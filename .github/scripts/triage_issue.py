#!/usr/bin/env python3
"""Classify a newly opened GitHub issue via OpenAI and print JSON to stdout.

Output shape: {"type": "bug|feature|question|docs|chore", "priority":
"P0|P1|P2|P3", "justification": "..."}. The workflow applies the `type`
label automatically (low-risk, reversible) and posts the priority as a
suggestion only — priority changes the triage queue, so it needs a human
to confirm before it's applied.
"""
import json
import os
import re
import sys
import urllib.error
import urllib.request

VALID_TYPES = {"bug", "feature", "question", "docs", "chore"}
VALID_PRIORITIES = {"P0", "P1", "P2", "P3"}

SYSTEM_PROMPT = """You triage incoming GitHub issues. Given a title and body, decide:
- "type": exactly one of bug, feature, question, docs, chore
- "priority": exactly one of P0 (critical/urgent), P1 (high), P2 (normal), P3 (low)
- "justification": one or two sentences explaining both choices

Respond with ONLY a JSON object with keys "type", "priority", "justification".
No markdown fences, no extra text."""

FALLBACK = {
    "type": "chore",
    "priority": "P2",
    "justification": "Could not classify automatically; defaulted to chore/P2 for manual triage.",
}


def main() -> int:
    title = os.environ.get("ISSUE_TITLE", "")
    body = os.environ.get("ISSUE_BODY", "") or "(no description provided)"
    api_key = os.environ.get("OPENAI_API_KEY")
    model = os.environ.get("OPENAI_MODEL", "gpt-4o-mini")

    if not api_key:
        print(json.dumps(FALLBACK))
        print("::warning::OPENAI_API_KEY not set; used fallback classification", file=sys.stderr)
        return 0

    payload = json.dumps(
        {
            "model": model,
            "temperature": 0,
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": f"Title: {title}\n\nBody:\n{body}"},
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
        with urllib.request.urlopen(req, timeout=60) as resp:
            resp_body = json.loads(resp.read().decode("utf-8"))
        content = resp_body["choices"][0]["message"]["content"].strip()
        content = re.sub(r"^```(json)?|```$", "", content, flags=re.MULTILINE).strip()
        result = json.loads(content)

        if result.get("type") not in VALID_TYPES:
            result["type"] = FALLBACK["type"]
        if result.get("priority") not in VALID_PRIORITIES:
            result["priority"] = FALLBACK["priority"]
        result.setdefault("justification", FALLBACK["justification"])

        print(json.dumps(result))
        return 0
    except (urllib.error.URLError, KeyError, IndexError, json.JSONDecodeError) as e:
        print(json.dumps(FALLBACK))
        print(f"::warning::Falling back to default classification: {e}", file=sys.stderr)
        return 0


if __name__ == "__main__":
    sys.exit(main())
