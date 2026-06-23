import json
import os
import sys
import time
import subprocess
import urllib.request
import urllib.error
from openai import OpenAI

# Load CRG report
try:
    with open("/tmp/crg-report.json") as f:
        report = json.load(f)
    print(f"CRG report loaded: risk_score={report.get('risk_score', 'N/A')}")
except Exception as e:
    print(f"Warning: {e}")
    report = {}

# Env vars
api_key     = os.environ.get("QWEN_API_KEY", "").strip()
pr_number   = os.environ.get("PR_NUMBER", "").strip()
pr_title    = os.environ.get("PR_TITLE", "Pull Request").strip()
pr_author   = os.environ.get("PR_AUTHOR", "unknown").strip()
base_branch = os.environ.get("BASE_BRANCH", "main").strip()
head_branch = os.environ.get("HEAD_BRANCH", "").strip()
repo        = os.environ.get("GITHUB_REPOSITORY", "").strip()
token       = os.environ.get("GH_TOKEN", "").strip()

def post_comment(body):
    if not token or not repo or not pr_number:
        print(body)
        return
    url = f"https://api.github.com/repos/{repo}/issues/{pr_number}/comments"
    data = json.dumps({"body": body}).encode("utf-8")
    req = urllib.request.Request(
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
            print(f"Comment posted: {result.get('html_url')}")
    except urllib.error.HTTPError as e:
        print(f"HTTP Error {e.code}: {e.read().decode()}")

if not api_key:
    post_comment(
        "## Git Analyser Setup Required\n\n"
        "`QWEN_API_KEY` secret is not set.\n\n"
        "1. Get a free key at https://openrouter.ai\n"
        "2. Go to repo **Settings → Secrets and variables → Actions → New repository secret**\n"
        "3. Name: `QWEN_API_KEY`, Value: your key\n"
        "4. Re-run this workflow"
    )
    sys.exit(0)

# Extract CRG data
risk_score     = float(report.get("risk_score") or 0)
changed_funcs  = report.get("changed_functions") or []
affected_flows = report.get("affected_flows") or []
test_gaps      = report.get("test_gaps") or []
priorities     = report.get("review_priorities") or changed_funcs

risk_label = "HIGH" if risk_score >= 0.7 else "MEDIUM" if risk_score >= 0.4 else "LOW"
risk_emoji = "🔴" if risk_score >= 0.7 else "🟡" if risk_score >= 0.4 else "🟢"

def fn_name(fn):
    if isinstance(fn, str): return fn
    return fn.get("qualified_name") or fn.get("name") or str(fn)

def fn_risk(fn):
    if isinstance(fn, dict):
        return float(fn.get("risk_score") or fn.get("risk") or 0)
    return 0.0

top_changed = (priorities or changed_funcs)[:15]
top_gaps    = test_gaps[:15]

changed_lines = "\n".join(f"  - {fn_name(fn)} (risk={fn_risk(fn):.2f})" for fn in top_changed) or "  none"
gap_lines     = "\n".join(f"  - {fn_name(g)}" for g in top_gaps) or "  none"
flow_lines    = "\n".join(f"  - {fn_name(f)}" for f in affected_flows[:10]) or "  none"

# Get git diff
def git(args, max_chars=5000):
    try:
        out = subprocess.check_output(["git"] + args, text=True, timeout=30, stderr=subprocess.DEVNULL)
        return out[:max_chars]
    except Exception:
        return "(not available)"

diff_stat   = git(["diff", f"origin/{base_branch}...HEAD", "--stat", "--no-color"], 3000)
diff_detail = git(["diff", f"origin/{base_branch}...HEAD", "--no-color", "--unified=3", "--diff-filter=ACMR"], 6000)

# Build prompt
prompt = f"""You are a senior software architect performing a thorough code review.

## Pull Request
- PR: #{pr_number} — {pr_title}
- Author: {pr_author}
- Branch: {head_branch} -> {base_branch}

## code-review-graph Risk Analysis
- Overall Risk Score: {risk_score:.2f} / 1.00 ({risk_emoji} {risk_label})
- Changed functions/classes ({len(changed_funcs)} total):
{changed_lines}
- Affected downstream flows:
{flow_lines}
- Test gaps (no coverage):
{gap_lines}

## Git Diff Summary
{diff_stat}

## Detailed Changes
{diff_detail}

Write a complete PR review with EXACTLY these sections:

## 🔍 What Changed
## ⚠️ Potential Risks
## 💥 Blast Radius
## 🧪 Recommended Test Cases
## 🏁 Verdict
APPROVE / REQUEST CHANGES / NEEDS REVIEW — one sentence why.

Be specific, reference actual function names. Max 700 words."""

# Call Qwen via OpenRouter
client = OpenAI(api_key=api_key, base_url="https://openrouter.ai/api/v1")

MODELS = [
    "qwen/qwen3-coder:free",
    "qwen/qwen3-235b-a22b:free",
    "qwen/qwen3-30b-a3b:free",
    "meta-llama/llama-3.3-70b-instruct:free",
]

analysis = None
for model in MODELS:
    for attempt in range(3):
        try:
            print(f"Trying {model} attempt {attempt+1}...")
            resp = client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": "You are a senior software architect. Write precise, actionable code reviews."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.2,
                max_tokens=2000,
            )
            analysis = resp.choices[0].message.content.strip()
            print(f"Success with {model}")
            break
        except Exception as e:
            err = str(e)
            print(f"Error {model}: {err[:120]}")
            if "429" in err or "rate" in err.lower():
                print("Rate limited, waiting 35s...")
                time.sleep(35)
            else:
                break
    if analysis:
        break

if not analysis:
    analysis = "⚠️ Qwen AI analysis could not be completed — all free models are rate limited. Please retry in a few minutes."

# Build comment
risk_bar = "█" * int(risk_score * 10) + "░" * (10 - int(risk_score * 10))

comment = f"""<!-- git-analyser-qwen-review -->
## 🤖 Git Analyser — Qwen AI Code Review

| | |
|---|---|
| **Risk Score** | `{risk_score:.2f}` {risk_emoji} {risk_label} `[{risk_bar}]` |
| **Changed** | {len(changed_funcs)} function(s)/class(es) |
| **Test Gaps** | {len(test_gaps)} uncovered |
| **Branch** | `{head_branch}` → `{base_branch}` |

---

{analysis}

---
<sub>🔬 Graph analysis by [code-review-graph](https://github.com/tirth8205/code-review-graph) · AI reasoning by Qwen via OpenRouter</sub>
"""

post_comment(comment)