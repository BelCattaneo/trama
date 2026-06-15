from pathlib import Path

_PROMPTS_DIR = Path(__file__).parent


def load_prompt(version: str) -> str:
    path = _PROMPTS_DIR / f"{version}_extraction.txt"
    return path.read_text(encoding="utf-8")
