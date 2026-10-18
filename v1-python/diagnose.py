import sys
from pathlib import Path

import anthropic
from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(PROJECT_ROOT / ".env")

MODEL = "claude-sonnet-5-5"
PRICE_INPUT_PER_MTOK = 2.00
PRICE_OUTPUT_PER_MTOK = 10.00

SYSTEM_PROMPT = """You are an expert CI/CD engineer who diagnoses failed Jenkins pipeline builds.

You will receive the full console log of one failed build. Your job:
1. Identify the stage that failed.
2. Find the first real error: the root cause, not the generic lines that follow it (such as "script returned exit code 1").
3. Explain the root cause in one or two sentences.
4. Quote the key log line(s) that prove it.
5. Suggest a concrete fix.

Rules:
- Fix the cause, not the symptom. Never suggest weakening or deleting a test, removing a timeout, or simply retrying as the fix.
- If the log alone is not enough to be certain, say what else you would check.
- Be concise."""


def main():
    if len(sys.argv) != 2:
        print("Usage: python diagnose.py <path-to-console.log>")
        sys.exit(1)

    log_path = Path(sys.argv[1])
    log_text = log_path.read_text()

    client = anthropic.Anthropic()
    response = client.messages.create(
        model=MODEL,
        max_tokens=4000,
        system=SYSTEM_PROMPT,
        messages=[
            {
                "role": "user",
                "content": f"Here is the console log of a failed Jenkins build:\n\n<console_log>\n{log_text}\n</console_log>",
            }
        ],
    )

    answer = "".join(block.text for block in response.content if block.type == "text")
    print(answer)

    block_types = [block.type for block in response.content]
    usage = response.usage
    cost = (usage.input_tokens * PRICE_INPUT_PER_MTOK + usage.output_tokens * PRICE_OUTPUT_PER_MTOK) / 1_000_000
    print(f"\n---\nBlocks: {block_types} | stop_reason: {response.stop_reason}")
    print(f"Tokens: input={usage.input_tokens}, output={usage.output_tokens} | cost ≈ ${cost:.4f}")

if __name__ == "__main__":
    main()