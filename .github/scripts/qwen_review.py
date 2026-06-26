import json
import os
import sys
import time
import subprocess
import urllib.request
import urllib.error
import re
import random

try:
    from openai import OpenAI
except ImportError:
    print("ERROR: openai not installed")
    sys.exit(1)

# ── Env vars ──────────────────────────────────────────────────────────────────
api_key     = os.environ.get("QWEN_API_KEY", "").strip()
pr_number   = os.environ.get("PR_NUMBER", "").strip()
pr_title    = os.environ.get("PR_TITLE", "Pull Request").strip()
pr_author   = os.environ.get("PR_AUTHOR", "unknown").strip()
base_branch = os.environ.get("BASE_BRANCH", "main").strip()
head_branch = os.environ.get("HEAD_BRANCH", "").strip()
repo        = os.environ.get("GITHUB_REPOSITORY", "").strip()
token       = os.environ.get("GH_TOKEN", "").strip()


# ══════════════════════════════════════════════════════════════════════════════
# RATE LIMITER — Exponential backoff + jitter + per-model cooldown tracking
# ══════════════════════════════════════════════════════════════════════════════
class RateLimiter:
    """
    Handles OpenRouter free-tier rate limiting with:
    - Exponential backoff (2^attempt * base_wait)
    - Random jitter (prevents thundering herd)
    - Per-model cooldown tracking
    - Global retry budget across all models
    """

    def __init__(self, base_wait=15, max_wait=120, jitter=5):
        self.base_wait   = base_wait   # seconds before first retry
        self.max_wait    = max_wait    # cap on wait time
        self.jitter      = jitter      # random ±jitter seconds added
        self.model_fails = {}          # tracks consecutive failures per model
        self.global_429s = 0           # total 429s seen this session

    def wait_for(self, model: str, attempt: int):
        """Calculate and sleep for the correct backoff duration."""
        # Exponential: 15s, 30s, 60s, 120s (capped)
        backoff = min(self.base_wait * (2 ** attempt), self.max_wait)
        # Add random jitter to avoid all retries hitting at the same time
        jitter  = random.uniform(-self.jitter, self.jitter)
        wait    = max(5, backoff + jitter)

        print(f"    ⏳ Rate limited [{model}] — waiting {wait:.0f}s "
              f"(backoff attempt {attempt+1}, global 429s: {self.global_429s})")
        time.sleep(wait)

    def record_429(self, model: str):
        self.global_429s += 1
        self.model_fails[model] = self.model_fails.get(model, 0) + 1

    def record_success(self, model: str):
        self.model_fails[model] = 0

    def is_model_exhausted(self, model: str, max_fails=4) -> bool:
        """Skip a model that has failed too many times."""
        return self.model_fails.get(model, 0) >= max_fails

    def should_abort(self, max_global_429s=15) -> bool:
        """Give up entirely if we've hit rate limits too many times."""
        return self.global_429s >= max_global_429s


def call_with_rate_limit(client, model: str, messages: list,
                          limiter: RateLimiter,
                          max_attempts=4,
                          temperature=0.2,
                          max_tokens=2000):
    """
    Call OpenRouter with full rate-limit handling.
    Returns (response_text, success_bool)
    """
    if limiter.is_model_exhausted(model):
        print(f"  ⏭  Skipping {model} — too many prior failures")
        return None, False

    for attempt in range(max_attempts):
        try:
            print(f"  → [{model}] attempt {attempt+1}/{max_attempts}...")
            resp = client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
            )
            text = resp.choices[0].message.content.strip()
            # Strip <think> reasoning tags some Qwen models include
            text = re.sub(r'<think>.*?</think>', '', text, flags=re.DOTALL).strip()
            limiter.record_success(model)
            print(f"  ✓  [{model}] success on attempt {attempt+1}")
            return text, True

        except Exception as e:
            err = str(e)
            is_rate_limit = "429" in err or "rate" in err.lower() or "too many" in err.lower()
            is_unavailable = "503" in err or "502" in err or "unavailable" in err.lower()

            if is_rate_limit:
                limiter.record_429(model)
                if limiter.should_abort():
                    print(f"  ✗  Global rate limit budget exhausted — aborting all retries")
                    return None, False
                if attempt < max_attempts - 1:
                    limiter.wait_for(model, attempt)
                else:
                    print(f"  ✗  [{model}] rate limited, max attempts reached")

            elif is_unavailable:
                wait = 10 + random.uniform(0, 5)
                print(f"  ✗  [{model}] service unavailable — waiting {wait:.0f}s...")
                time.sleep(wait)

            else:
                print(f"  ✗  [{model}] error: {err[:150]}")
                return None, False  # Non-rate-limit error — skip this model

    return None, False


# ══════════════════════════════════════════════════════════════════════════════
# GITHUB COMMENT POSTER
# ══════════════════════════════════════════════════════════════════════════════
def post_comment(body):
    if not token or not repo or not pr_number:
        print(body)
        return
    url  = f"https://api.github.com/repos/{repo}/issues/{pr_number}/comments"
    data = json.dumps({"body": body}).encode("utf-8")
    req  = urllib.request.Request(
        url, data=data,
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
            "Content-Type": "application/json",
            "X-GitHub-Api-Version": "2022-11-28",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req) as r:
            result = json.loads(r.read())
            print(f"  ✅ Comment posted: {result.get('html_url')}")
    except urllib.error.HTTPError as e:
        print(f"  HTTP Error {e.code}: {e.read().decode()}")


# ══════════════════════════════════════════════════════════════════════════════
# GUARD: API KEY
# ══════════════════════════════════════════════════════════════════════════════
if not api_key:
    post_comment(
        "## ⚠️ Git Analyser Setup Required\n\n"
        "`QWEN_API_KEY` secret is not set.\n\n"
        "1. Get a free key at https://openrouter.ai\n"
        "2. Repo **Settings → Secrets → Actions → New repository secret**\n"
        "3. Name: `QWEN_API_KEY`, Value: your key\n"
        "4. Re-run this workflow"
    )
    sys.exit(0)


# ══════════════════════════════════════════════════════════════════════════════
# GIT DIFF ANALYSIS
# ══════════════════════════════════════════════════════════════════════════════
def git(args, max_chars=8000):
    try:
        out = subprocess.check_output(
            ["git"] + args, text=True, timeout=30, stderr=subprocess.DEVNULL
        )
        return out[:max_chars]
    except Exception as e:
        return f"(not available: {e})"

diff_stat = git(["diff", f"origin/{base_branch}...HEAD", "--stat", "--no-color"], 3000)
diff_full = git(["diff", f"origin/{base_branch}...HEAD", "--no-color",
                  "--unified=5", "--diff-filter=ACMR"], 8000)

# Compute risk score from the diff
added_lines   = diff_full.count("\n+")
removed_lines = diff_full.count("\n-")
total_changes = added_lines + removed_lines

# Detect changed functions/classes
func_pattern  = re.compile(r'^\+[^+].*\bdef \w+|^\+[^+].*\bclass \w+', re.MULTILINE)
changed_funcs = [f.strip().lstrip('+').strip() for f in func_pattern.findall(diff_full)]
func_count    = len(changed_funcs)

raw_risk   = min(1.0, (total_changes / 200) * 0.6 + (func_count / 10) * 0.4)
risk_score = round(raw_risk, 2)
risk_label = "HIGH"   if risk_score >= 0.7 else "MEDIUM" if risk_score >= 0.4 else "LOW"
risk_emoji = "🔴"     if risk_score >= 0.7 else "🟡"     if risk_score >= 0.4 else "🟢"
risk_bar   = "█" * int(risk_score * 10) + "░" * (10 - int(risk_score * 10))

files_changed = [
    line.split("|")[0].strip()
    for line in diff_stat.splitlines()
    if "|" in line
]

# Load CRG extras if available
crg_test_gaps, crg_flows = [], []
try:
    with open("/tmp/crg-report.json") as f:
        crg = json.load(f)
    crg_test_gaps = crg.get("test_gaps") or []
    crg_flows     = crg.get("affected_flows") or []
except Exception:
    pass

def fn_name(fn):
    if isinstance(fn, str): return fn
    return fn.get("qualified_name") or fn.get("name") or str(fn)

gap_lines  = "\n".join(f"  - {fn_name(g)}" for g in crg_test_gaps[:10]) or "  (run tests to detect)"
flow_lines = "\n".join(f"  - {fn_name(f)}" for f in crg_flows[:10])     or "  (see diff for impact)"
func_lines = "\n".join(f"  - {f}" for f in changed_funcs[:15])           or "  (no new defs detected)"
files_list = "\n".join(f"  - {f}" for f in files_changed)                or "  (see diff)"

print(f"\n📊 Risk: {risk_score} ({risk_label}) | +{added_lines}/-{removed_lines} lines | {func_count} functions")


# ══════════════════════════════════════════════════════════════════════════════
# QWEN PROMPT
# ══════════════════════════════════════════════════════════════════════════════
prompt = f"""You are a senior software architect performing a thorough code review.

## Pull Request
- PR: #{pr_number} — {pr_title}
- Author: {pr_author}
- Branch: `{head_branch}` → `{base_branch}`

## Risk Analysis
- Risk Score: {risk_score:.2f} / 1.00  ({risk_emoji} {risk_label})
- Lines changed: +{added_lines} added / -{removed_lines} removed
- Changed functions/classes ({func_count}):
{func_lines}

## Files Changed
{files_list}

## Downstream Impact
{flow_lines}

## Test Gaps
{gap_lines}

## Diff Summary
```
{diff_stat}
```

## Full Changes
```diff
{diff_full}
```

Write a complete PR review using EXACTLY these sections:

## 🔍 What Changed
## ⚠️ Potential Risks
## 💥 Blast Radius
## 🧪 Recommended Test Cases
## 🏁 Verdict
APPROVE / REQUEST CHANGES / NEEDS REVIEW — one sentence why.

Reference actual function/class names. Max 800 words."""

messages = [
    {"role": "system", "content": "You are a senior software architect. Write precise, actionable code reviews."},
    {"role": "user",   "content": prompt},
]


# ══════════════════════════════════════════════════════════════════════════════
# CALL QWEN WITH RATE LIMITER
# ══════════════════════════════════════════════════════════════════════════════
client  = OpenAI(api_key=api_key, base_url="https://openrouter.ai/api/v1")
limiter = RateLimiter(base_wait=15, max_wait=120, jitter=5)

# Model list — Qwen models first, fallbacks after
MODELS = [
    "qwen/qwen3-coder:free",
    "qwen/qwen3-235b-a22b:free",
    "qwen/qwen3-30b-a3b:free",
    "qwen/qwen2.5-coder-32b-instruct:free",
    "qwen/qwen2.5-72b-instruct:free",
    "meta-llama/llama-3.3-70b-instruct:free",
    "mistralai/mistral-7b-instruct:free",
    "google/gemma-3-27b-it:free",
]

print(f"\n🤖 Calling Qwen AI via OpenRouter ({len(MODELS)} models available)...\n")

analysis = None
model_used = None

for model in MODELS:
    if limiter.should_abort():
        print("⛔ Rate limit budget exhausted — stopping model attempts")
        break

    text, ok = call_with_rate_limit(
        client, model, messages, limiter,
        max_attempts=4,
        temperature=0.2,
        max_tokens=2000,
    )
    if ok and text:
        analysis  = text
        model_used = model
        break
    else:
        # Small pause between switching models (avoid burst)
        time.sleep(3)

if not analysis:
    analysis = (
        "⚠️ **Qwen AI analysis could not be completed.**\n\n"
        f"All {len(MODELS)} models were rate limited after multiple retries "
        f"({limiter.global_429s} total rate-limit responses received).\n\n"
        "**What to do:**\n"
        "- Push any small change to re-trigger in 5–10 minutes\n"
        "- Or add credits to your OpenRouter account for guaranteed access at https://openrouter.ai"
    )
    model_used = "none"


# ══════════════════════════════════════════════════════════════════════════════
# POST COMMENT
# ══════════════════════════════════════════════════════════════════════════════
comment = f"""<!-- git-analyser-qwen-review -->
## 🤖 Git Analyser — Qwen AI Code Review

| | |
|---|---|
| **Risk Score** | `{risk_score:.2f}` {risk_emoji} {risk_label} `[{risk_bar}]` |
| **Lines Changed** | +{added_lines} added / -{removed_lines} removed |
| **Functions Changed** | {func_count} |
| **Files** | {len(files_changed)} file(s) |
| **Branch** | `{head_branch}` → `{base_branch}` |
| **Model Used** | `{model_used}` |

---

{analysis}

---
<sub>🔬 Diff-based risk analysis + Qwen AI via OpenRouter · [code-review-graph](https://github.com/tirth8205/code-review-graph)</sub>
"""

post_comment(comment)