import re
import sys
from pathlib import Path

FULL_TIMESTAMP = re.compile(r"^\[\d{4}-\d{2}-\d{2}T(\d{2}:\d{2}:\d{2})\.\d+Z\] ")
SHORT_TIMESTAMP = re.compile(r"^\[\d{2}:\d{2}:\d{2}\] ")
PIPELINE_NOISE = re.compile(r"^\[Pipeline\] (\{|\}|// .*)$")

KEEP_EDGES = 3
MAX_LINES = 400
HEAD_LINES = 50


def shorten_timestamp(line):
    return FULL_TIMESTAMP.sub(r"[\1] ", line)


def is_noise(line):
    return bool(PIPELINE_NOISE.match(line))


def shape(line):
    """The line without its timestamp and with every number replaced by #, used to spot repeats."""
    return re.sub(r"\d+", "#", SHORT_TIMESTAMP.sub("", line))


def collapse_repeats(lines):
    result = []
    i = 0
    while i < len(lines):
        j = i
        while j + 1 < len(lines) and shape(lines[j + 1]) == shape(lines[i]):
            j += 1
        run = lines[i : j + 1]
        if len(run) > 2 * KEEP_EDGES + 1:
            omitted = len(run) - 2 * KEEP_EDGES
            result.extend(run[:KEEP_EDGES])
            result.append(f"... ({omitted} similar lines omitted) ...")
            result.extend(run[-KEEP_EDGES:])
        else:
            result.extend(run)
        i = j + 1
    return result


def cap_length(lines):
    if len(lines) <= MAX_LINES:
        return lines
    tail = MAX_LINES - HEAD_LINES
    omitted = len(lines) - MAX_LINES
    return lines[:HEAD_LINES] + [f"... ({omitted} lines omitted from the middle) ..."] + lines[-tail:]


def trim_log(text):
    lines = [shorten_timestamp(line) for line in text.splitlines()]
    lines = [line for line in lines if not is_noise(line)]
    lines = collapse_repeats(lines)
    lines = cap_length(lines)
    return "\n".join(lines)


def main():
    if len(sys.argv) != 2:
        print("Usage: python trim_log.py <path-to-console.log>", file=sys.stderr)
        sys.exit(1)

    original = Path(sys.argv[1]).read_text()
    trimmed = trim_log(original)
    print(trimmed)

    before_lines, after_lines = len(original.splitlines()), len(trimmed.splitlines())
    reduction = 100 * (1 - len(trimmed) / len(original))
    print(
        f"\n---\nLines: {before_lines} -> {after_lines} | Characters: {len(original)} -> {len(trimmed)} ({reduction:.0f}% smaller)",
        file=sys.stderr,
    )


if __name__ == "__main__":
    main()