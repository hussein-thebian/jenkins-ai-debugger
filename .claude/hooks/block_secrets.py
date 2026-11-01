#!/usr/bin/env python3
"""PreToolUse hook: block any tool call that could expose secrets or eval answer keys."""
import json
import re
import sys

ENV_FILE = re.compile(r"(?<![\w.])\.env(?![\w.-])")
ANSWER_KEY = re.compile(r"\bexpected\b")
EVAL_PATH = re.compile(r"(?<![\w-])eval(?:/[^\s\"'`;|&)\\]*)?(?![\w-])")
ALLOWED_EVAL_PATH = re.compile(r"eval/cases/[\w-]+/console\.log")
TWO_DOT_DIFF = re.compile(r"git\s+diff\b[^;|&]*?[^\s.]\.\.(?!\.)\S")


def reason_to_block(text):
    if ENV_FILE.search(text):
        return "it references the .env secrets file"
    if ANSWER_KEY.search(text):
        return "it references the eval answer keys (expected.json)"
    for match in EVAL_PATH.finditer(text):
        if not ALLOWED_EVAL_PATH.fullmatch(match.group(0)):
            return f"it touches '{match.group(0)}'; only eval/cases/<case>/console.log files may be read"
    if TWO_DOT_DIFF.search(text):
        return "two-dot git diff compares branch tips and can expose unrelated files; use main...<branch> (three dots)"
    return None


def main():
    event = json.load(sys.stdin)
    text = json.dumps(event.get("tool_input", {}))
    reason = reason_to_block(text)
    if reason:
        print(f"Blocked by project hook: this {event.get('tool_name')} call is not allowed because {reason}.", file=sys.stderr)
        sys.exit(2)
    sys.exit(0)


if __name__ == "__main__":
    main()