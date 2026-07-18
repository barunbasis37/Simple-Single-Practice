#!/usr/bin/env python3
"""Send a PR diff to OpenAI and print a Markdown review to stdout."""
import json
import os
import sys
import urllib.request
import urllib.error

MAX_DIFF_CHARS = 60000

SYSTEM_PROMPT = """You are an automated code reviewer commenting on a GitHub pull request.
You will be given the PR title, description, and diff. Respond in GitHub-flavored
Markdown with exactly these sections, in this order:

### Summary
2-4 sentences describing what you understand the PR does and why.

### Review Notes
Bullet points on notable issues, risks, bugs, or things done well. Be concise and
specific (reference file/line when useful). If nothing stands out, say so briefly.

### Recommendation
One line starting with exactly one of:
- "Merge" (recommended if approve to merge as-is)
- "Merge with changes" (recommended if minor changes needed but not blocking)
- "Do not merge" (recommended if there are blocking issues)
followed by a one-sentence justification.

Be factual and concise. If the diff was truncated, note that your review may be
incomplete."""


def read_file(path: str) -> str:
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            return f.read()
    except FileNotFoundError:
        return ""


def main() -> int:
    diff = read_file("pr.diff")
    truncated = len(diff) > MAX_DIFF_CHARS
    if truncated:
        diff = diff[:MAX_DIFF_CHARS]

    pr_title = os.environ.get("PR_TITLE", "")
    pr_body = os.environ.get("PR_BODY", "")
    api_key = os.environ.get("OPENAI_API_KEY")
    model = os.environ.get("OPENAI_MODEL", "gpt-4o-mini")

    if not api_key:
        print("::error::OPENAI_API_KEY secret is not set", file=sys.stderr)
        return 1

    user_content = f"""PR Title: {pr_title}

PR Description:
{pr_body or "(no description provided)"}

Diff{" (truncated)" if truncated else ""}:
```diff
{diff or "(no diff content)"}
```"""

    payload = json.dumps(
        {
            "model": model,
            "temperature": 0.2,
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_content},
            ],
        }
    ).encode("utf-8")

    req = urllib.request.Request(
        "https://api.openai.com/v1/chat/completions",
        data=payload,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            body = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        err_body = e.read().decode("utf-8", errors="replace")
        print(f"::error::OpenAI API request failed ({e.code}): {err_body}", file=sys.stderr)
        return 1
    except urllib.error.URLError as e:
        print(f"::error::OpenAI API request failed: {e}", file=sys.stderr)
        return 1

    try:
        review = body["choices"][0]["message"]["content"].strip()
    except (KeyError, IndexError):
        print(f"::error::Unexpected OpenAI response shape: {body}", file=sys.stderr)
        return 1

    print(review)
    return 0


if __name__ == "__main__":
    sys.exit(main())
