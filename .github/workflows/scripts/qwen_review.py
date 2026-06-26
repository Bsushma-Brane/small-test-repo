#!/usr/bin/env python3
"""
qwen_review.py
Called by .github/workflows/code-review.yml

Reads code-review-graph's JSON output, sends it + the actual diff to Qwen AI
via OpenRouter, then posts the analysis as a GitHub PR comment.
"""

import json
import os
import sys
import time
import subprocess
import urllib.request
import urllib.error

try:
    from openai import OpenAI
except ImportError:
    print("ERROR: openai package not installed. Run: pip install openai")
    sys.exit(1)

# ── Load CRG JSON report ───────────────────────────────────────────────────────
try:
    with open("/tmp/crg-report.json") as f:
        report = json.load(f)
    print(f"Loaded CRG report: risk_score={report.get('risk_score', 'N/A')}")
except Exception as e:
    print(f"Warning: Could not load /tmp/crg-report.json: {e}")
    report = {}

# ── Environment variables (injected by workflow) ───────────────────────────────
api_key     = os.environ.get("QWEN_API_KEY", "").strip()
pr_number   = os.environ.get("PR_NUMBER", "").strip()
pr_title    = os.environ.get("PR_TITLE", "Pull Request").strip()
pr_author   = os.environ.get("PR_AUTHOR", "unknown").strip()
base_branch = os.environ.get("BASE_BRANCH", "main").strip()
head_branch = os.environ.get("HEAD_BRANCH", "").strip()
repo        = os.environ.get("GITHUB_REPOSITORY", "").strip()
token       = os.environ.get("GH_TOKEN", "").strip()

# ── Guard: QWEN_API_KEY must be set ───────────────────────────────────────────
if not api_key:
    msg = (
        "## ⚠️ Git Analyser — Setup Required\n\n"
        "`QWEN_API_KEY` secret is not configured.\n\n"
        "**To fix:**\n"
        "1. Go to https://openrouter.ai and create a free account\n"
        "2. Copy your API key\n"
        "3. In your repo: **Settings → Secrets and variables → Actions → New repository secret**\n"
        "   - Name: `QWEN_API_KEY`\n"
        "   - Value: your OpenRouter key (starts with `sk-or-...`)\n"
        "4. Re-run this workflow\n"
    )
    _post_comment(token, repo, pr_number, msg)
    sys.exit(0)

# ── Extract data from CRG report ──────────────────────────────────────────────
risk_score     = float(report.get("risk_score") or 0)
changed_funcs  = report.get("changed_functions") or []
affected_flows = report.get("affected_flows") or []
test_gaps      = report.get("test_gaps") or []
priorities     = report.get("review_priorities") or changed_funcs

risk_label = (
    "🔴 HIGH"   if risk_score >= 0.7 else
    "🟡 MEDIUM" if risk_score >= 0.4 else
    "🟢 LOW"
)

def fn_name(fn):
    if isinstance(fn, str):
        return fn
    return fn.get("qualified_name") or fn.get("name") or str(fn)

def fn_risk(fn):
    if isinstance(fn, dict):
        return float(fn.get("risk_score") or fn.get("risk") or 0)
    return 0.0

top_changed = (priorities or changed_funcs)[:15]
top_gaps    = test_gaps[:15]

changed_lines = "\n".join(
    f"  • {fn_name(fn)}  (risk={fn_risk(fn):.2f})"
    for fn in top_changed
) or "  No specific functions detected"

gap_lines = "\n".join(
    f"  • {fn_name(g)}"
    for g in top_gaps
) or "  No test gaps detected"

flow_lines = "\n".join(
    f"  • {fn_name(f)}"
    for f in affected_flows[:10]
) or "  None"

# ── Get git diff ──────────────────────────────────────────────────────────────
def run_git(args, max_chars=5000):
    try:
        out = subprocess.check_output(
            ["git"] + args, text=True, timeout=30, stderr=subprocess.DEVNULL
        )
        return out[:max_chars]
    except Exception:
        return "(not available)"

diff_stat   = run_git(["diff", f"origin/{base_branch}...HEAD", "--stat", "--no-color"], 3000)
diff_detail = run_git(["diff", f"origin/{base_branch}...HEAD", "--no-color",
                        "--unified=3", "--diff-filter=ACMR"], 6000)

# ── Build prompt ───────────────────────────────────────────────────────────────
prompt = f"""You are a senior software architect performing a thorough code review.

## Pull Request
- **PR**: #{pr_number} — {pr_title}
- **Author**: {pr_author}
- **Branch**: `{head_branch}` → `{base_branch}`

## code-review-graph Risk Analysis
- **Overall Risk Score**: {risk_score:.2f} / 1.00  ({risk_label})
- **Changed functions/classes** ({len(changed_funcs)} total):
{changed_lines}

- **Affected downstream flows**:
{flow_lines}

- **Test gaps** (no coverage):
{gap_lines}

## Git Diff Summary
```
{diff_stat}
```

## Detailed Changes
```diff
{diff_detail}
```

---

Write a complete PR review using EXACTLY these section headers (keep the emojis):

## 🔍 What Changed
Describe what was modified, added, or removed. Reference specific function/class names.

## ⚠️ Potential Risks
List specific risks from the changed functions and their risk scores. Mention any side effects.

## 💥 Blast Radius
Which parts of the codebase are impacted downstream? Who calls these changed functions?

## 🧪 Recommended Test Cases
Write 3–5 concrete test cases (function name + what to assert) targeting the test gaps above.

## 🏁 Verdict
**APPROVE** / **REQUEST CHANGES** / **NEEDS REVIEW** — one sentence explaining why.

Be specific, reference actual function names. Stay under 700 words total."""

# ── Call Qwen via OpenRouter ───────────────────────────────────────────────────
client = OpenAI(
    api_key=api_key,
    base_url="https://openrouter.ai/api/v1",
)

MODELS = [
    "qwen/qwen3-coder:free",
    "qwen/qwen3-235b-a22b:free",
    "qwen/qwen3-30b-a3b:free",
    "meta-llama/llama-3.3-70b-instruct:free",  # fallback if all Qwen are rate-limited
]

analysis = None
for model in MODELS:
    for attempt in range(3):
        try:
            print(f"  Trying model: {model} (attempt {attempt+1}/3)...")
            resp = client.chat.completions.create(
                model=model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are a senior software architect. Write precise, actionable code reviews."
                    },
                    {"role": "user", "content": prompt}
                ],
                temperature=0.2,
                max_tokens=2000,
            )
            analysis = resp.choices[0].message.content.strip()
            print(f"  ✓ Success with {model}")
            break
        except Exception as e:
            err = str(e)
            print(f"  ✗ {model}: {err[:120]}")
            if "429" in err or "rate" in err.lower():
                wait = 35
                print(f"    Rate limited — waiting {wait}s...")
                time.sleep(wait)
            else:
                break  # different error — try next model immediately
    if analysis:
        break

if not analysis:
    analysis = (
        "⚠️ **Qwen AI analysis could not be completed** — all free-tier models are currently rate-limited.\n\n"
        "**What you can do:**\n"
        "- Wait ~1 minute and re-run the workflow\n"
        "- Or add credits to your OpenRouter account for priority access\n"
    )

# ── Build the final PR comment ────────────────────────────────────────────────
risk_bar = "█" * int(risk_score * 10) + "░" * (10 - int(risk_score * 10))

comment = f"""<!-- git-analyser-qwen-review -->
## 🤖 Git Analyser — Qwen AI Code Review

| | |
|---|---|
| **Risk Score** | `{risk_score:.2f}` {risk_label} `[{risk_bar}]` |
| **Changed** | {len(changed_funcs)} function(s)/class(es) |
| **Test Gaps** | {len(test_gaps)} uncovered |
| **Branch** | `{head_branch}` → `{base_branch}` |

---

{analysis}

---
<sub>🔬 Graph analysis by [code-review-graph](https://github.com/tirth8205/code-review-graph) · AI reasoning by Qwen via OpenRouter</sub>
"""

# ── Post to GitHub ────────────────────────────────────────────────────────────
def _post_comment(gh_token, gh_repo, pr_num, body):
    if not gh_token or not gh_repo or not pr_num:
        print("Cannot post comment — missing token/repo/pr_number")
        print(body)
        return

    url = f"https://api.github.com/repos/{gh_repo}/issues/{pr_num}/comments"
    data = json.dumps({"body": body}).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data,
        headers={
            "Authorization": f"Bearer {gh_token}",
            "Accept": "application/vnd.github+json",
            "Content-Type": "application/json",
            "X-GitHub-Api-Version": "2022-11-28",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req) as r:
            result = json.loads(r.read())
            print(f"\n✅ Comment posted: {result.get('html_url')}")
    except urllib.error.HTTPError as e:
        body_err = e.read().decode()
        print(f"ERROR posting comment: HTTP {e.code} — {body_err}")

_post_comment(token, repo, pr_number, comment)
