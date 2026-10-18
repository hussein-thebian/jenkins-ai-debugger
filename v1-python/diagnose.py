import argparse
import sys
from pathlib import Path
from typing import Literal

import anthropic
from dotenv import load_dotenv
from pydantic import BaseModel, Field

from trim_log import trim_log

PROJECT_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(PROJECT_ROOT / ".env")

MODEL = "claude-sonnet-5-5"
PRICE_INPUT_PER_MTOK = 2.00
PRICE_OUTPUT_PER_MTOK = 10.00

SYSTEM_PROMPT = """You are an expert CI/CD engineer who diagnoses failed Jenkins pipeline builds.

You will receive the full console log of one failed build. Your job:
1. Identify the stage that failed and the final build result.
2. Find the first real error: the root cause, not the generic lines that follow it (such as "script returned exit code 1").
3. Explain the root cause in one or two sentences.
4. Quote the exact log lines that prove it.
5. Suggest a concrete fix.

Rules:
- Fix the cause, not the symptom. Never suggest weakening or deleting a test, removing a timeout, or simply retrying as the fix.
- Separate what the log proves from what you assume. Anything you cannot see in the log (source code, file contents, the intent behind a change) goes in "assumptions".
- Use confidence "high" only when the log alone proves both the root cause and the fix. Use "medium" or "low" when the fix depends on code or history you cannot see."""


class Diagnosis(BaseModel):
    failed_stage: str = Field(description="Name of the Jenkins stage that failed, exactly as shown in the log")
    build_result: Literal["FAILURE", "ABORTED", "UNSTABLE"]
    category: Literal[
        "test_failure",
        "credential_error",
        "terraform_error",
        "timeout",
        "dependency_error",
        "syntax_error",
        "infrastructure_error",
        "other",
    ]
    root_cause: str = Field(description="One or two sentences explaining why the build failed")
    key_evidence: list[str] = Field(description="Exact log lines that prove the root cause")
    suggested_fix: str = Field(description="The single best fix")
    confidence: Literal["high", "medium", "low"]
    assumptions: list[str] = Field(description="Things assumed because the log does not show them; empty if none")
    next_checks: list[str] = Field(description="What a human should verify next")


def diagnose(log_text: str):
    client = anthropic.Anthropic()
    return client.messages.parse(
        model=MODEL,
        max_tokens=4000,
        system=SYSTEM_PROMPT,
        messages=[
            {
                "role": "user",
                "content": f"Here is the console log of a failed Jenkins build:\n\n<console_log>\n{log_text}\n</console_log>",
            }
        ],
        output_format=Diagnosis,
    )


def main():
    parser = argparse.ArgumentParser(description="Diagnose a failed Jenkins build log with Claude.")
    parser.add_argument("log_path", help="path to a Jenkins console log")
    parser.add_argument("--raw", action="store_true", help="send the full log without trimming")
    args = parser.parse_args()

    log_text = Path(args.log_path).read_text()
    original_lines = len(log_text.splitlines())
    if not args.raw:
        log_text = trim_log(log_text)
    sent_lines = len(log_text.splitlines())

    response = diagnose(log_text)

    if response.parsed_output is None:
        print(f"No valid diagnosis returned (stop_reason: {response.stop_reason})", file=sys.stderr)
        sys.exit(1)

    print(response.parsed_output.model_dump_json(indent=2))

    usage = response.usage
    cost = (usage.input_tokens * PRICE_INPUT_PER_MTOK + usage.output_tokens * PRICE_OUTPUT_PER_MTOK) / 1_000_000
    block_types = [block.type for block in response.content]
    mode = "raw" if args.raw else "trimmed"
    print(
        f"\n---\nLog lines: {original_lines} -> {sent_lines} ({mode})\n"
        f"Blocks: {block_types} | stop_reason: {response.stop_reason}\n"
        f"Tokens: input={usage.input_tokens}, output={usage.output_tokens} | cost ≈ ${cost:.4f}",
        file=sys.stderr,
    )


if __name__ == "__main__":
    main()