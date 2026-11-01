#!/usr/bin/env python3
"""Stop hook: save the diagnosis JSON from Claude's final answer to reports/."""
import json
import os
import re
import sys
import hashlib
from datetime import datetime
from pathlib import Path

JSON_BLOCK = re.compile(r"```json\s*(\{.*?\})\s*```", re.DOTALL)
REQUIRED_FIELDS = {"failed_stage", "build_result", "category", "root_cause", "suggested_fix", "confidence"}


def final_answer_text(transcript_path):
    last_text = ""
    for line in Path(transcript_path).read_text().splitlines():
        try:
            entry = json.loads(line)
        except json.JSONDecodeError:
            continue
        if entry.get("isSidechain"):
            continue
        message = entry.get("message") or {}
        if message.get("role") != "assistant":
            continue
        content = message.get("content")
        if isinstance(content, str):
            parts = [content]
        elif isinstance(content, list):
            parts = [p.get("text", "") for p in content if isinstance(p, dict) and p.get("type") == "text"]
        else:
            parts = []
        text = "".join(parts).strip()
        if text:
            last_text = text
    return last_text


def message_text(value):
    """Turn last_assistant_message (a string or a message object) into plain text."""
    if isinstance(value, str):
        return value
    if isinstance(value, dict):
        content = value.get("content", value.get("message", {}).get("content"))
        if isinstance(content, str):
            return content
        if isinstance(content, list):
            return "".join(p.get("text", "") for p in content if isinstance(p, dict) and p.get("type") == "text")
    return ""


def main():
    event = json.load(sys.stdin)
    transcript = event.get("transcript_path")
    text = message_text(event.get("last_assistant_message"))
    if not JSON_BLOCK.search(text) and transcript:
        text = final_answer_text(transcript)

    blocks = JSON_BLOCK.findall(text)
    if not blocks:
        return
    report = json.loads(blocks[-1])
    if not REQUIRED_FIELDS.issubset(report):
        return

    project = Path(os.environ.get("CLAUDE_PROJECT_DIR", event.get("cwd", ".")))
    reports_dir = project / "reports"
    reports_dir.mkdir(exist_ok=True)
    session = str(event.get("session_id", "unknown"))[:8]
    fingerprint = hashlib.sha256(json.dumps(report, sort_keys=True).encode()).hexdigest()[:8]
    if list(reports_dir.glob(f"*-{session}-{fingerprint}.json")):
        return

    out_file = reports_dir / f"{datetime.now():%Y%m%d-%H%M%S}-{session}-{fingerprint}.json"
    out_file.write_text(json.dumps(
        {"saved_at": datetime.now().isoformat(timespec="seconds"), "session_id": event.get("session_id"),
         "trigger": event.get("hook_event_name"), "diagnosis": report},
        indent=2,
    ))


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        print(f"save_report hook skipped: {error}", file=sys.stderr)
    sys.exit(0)