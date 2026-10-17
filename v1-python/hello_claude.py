from pathlib import Path

import anthropic
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent.parent / ".env")

client = anthropic.Anthropic()

response = client.messages.create(
    model="claude-sonnet-5-5",
    max_tokens=200,
    system="You are a senior DevOps engineer. Answer in one short sentence.",
    messages=[
        {
            "role": "user",
            "content": "What usually causes a Jenkins build to fail with 'script returned exit code 1'?",
        }
    ],
)

print(response.content[0].text)
print(f"\nTokens used: input={response.usage.input_tokens}, output={response.usage.output_tokens}")