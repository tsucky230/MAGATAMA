"""Measure token cost of grasping this project WITH vs WITHOUT the comP index.

Approach B (no comP):   an LLM must read the full source text of every file.
Approach A (with comP): the LLM reads comP's structured summary (symbols /
                        signatures), not the bodies.

Token counts use tiktoken's cl100k_base if available (a widely-used proxy);
otherwise a chars/4 heuristic. The method used is printed so the numbers are
reproducible and clearly labeled as estimates.
"""

from __future__ import annotations

from pathlib import Path

try:
    import tiktoken

    _enc = tiktoken.get_encoding("cl100k_base")

    def count_tokens(text: str) -> int:
        return len(_enc.encode(text))

    METHOD = "tiktoken/cl100k_base"
except Exception:  # pragma: no cover - fallback when tiktoken is absent

    def count_tokens(text: str) -> int:
        return (len(text) + 3) // 4

    METHOD = "heuristic chars/4"


ROOT = "e:/dev/MAGATAMA"
SRC_DIRS = [
    f"{ROOT}/packages/magatama-core/src",
    f"{ROOT}/packages/magatama-mcp/src",
]
# The comP project-overview output that comP/MAGATAMA would feed to the LLM.
COMP_OVERVIEW = (
    "C:/Users/tsuck/.claude/projects/e--dev-MAGATAMA/"
    "8ed780b0-d2f4-4ce7-b3a4-b79fc18d5a0f/tool-results/"
    "mcp-comp-get_project_overview-1781468193718.txt"
)


def read(path: str | Path) -> str:
    return Path(path).read_text(encoding="utf-8", errors="replace")


def measure_source() -> tuple[int, int, int]:
    files = 0
    chars = 0
    tokens = 0
    for d in SRC_DIRS:
        for path in Path(d).rglob("*.py"):
            if "__pycache__" in path.parts:
                continue
            text = read(path)
            files += 1
            chars += len(text)
            tokens += count_tokens(text)
    return files, chars, tokens


def main() -> None:
    print(f"# Token measurement (method: {METHOD})\n")

    # Approach B: read all source bodies.
    b_files, b_chars, b_tokens = measure_source()
    print("## B. WITHOUT comP (read full source)")
    print(f"   files : {b_files}")
    print(f"   chars : {b_chars:,}")
    print(f"   tokens: {b_tokens:,}\n")

    # Approach A: read the comP structured overview instead.
    overview = read(COMP_OVERVIEW) if Path(COMP_OVERVIEW).exists() else ""
    a_full_tokens = count_tokens(overview)
    # The summary actually used to write the overview = the stats + language
    # distribution + top files (everything before the per-file breakdown).
    marker = "## Files Breakdown"
    summary = overview.split(marker)[0] if marker in overview else overview
    a_summary_tokens = count_tokens(summary)
    print("## A. WITH comP (read structured summary)")
    print(f"   full index dump  chars : {len(overview):,}")
    print(f"   full index dump  tokens: {a_full_tokens:,}")
    print(f"   overview summary tokens: {a_summary_tokens:,}\n")

    print("## Savings vs B (full source)")
    if b_tokens:
        for label, t in (
            ("full comP dump", a_full_tokens),
            ("comP summary", a_summary_tokens),
        ):
            pct = 100 * (1 - t / b_tokens)
            ratio = b_tokens / t if t else float("inf")
            print(f"   {label:>16}: {t:,} tokens  ->  -{pct:.1f}%  ({ratio:.1f}x less)")


if __name__ == "__main__":
    main()
