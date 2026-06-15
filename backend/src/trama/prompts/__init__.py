from pathlib import Path

_PROMPTS_DIR = Path(__file__).parent


def load_prompt(version: str) -> str:
    """Return the contents of the prompt file for the given version.

    Reads from disk on every call so editing a prompt file does not require
    a restart. Raises FileNotFoundError if the version does not exist.
    """
    path = _PROMPTS_DIR / f"{version}_extraction.txt"
    return path.read_text(encoding="utf-8")
