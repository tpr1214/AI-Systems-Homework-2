import json
from pathlib import Path
from typing import Dict, List


HISTORY_PATH = Path(__file__).with_name("history.json")


def load_history() -> List[Dict[str, str]]:
    if not HISTORY_PATH.exists():
        return []
    try:
        data = json.loads(HISTORY_PATH.read_text(encoding="utf-8"))
        if isinstance(data, list):
            history = [
                m
                for m in data
                if isinstance(m, dict)
                and m.get("role") in {"user", "assistant", "system", "tool"}
                and isinstance(m.get("content"), str)
            ]
            if history:
                print("Welcome back.")
            return history
    except Exception as e:
        print(f"[Memory] Could not load history: {e}")
    return []


def save_history(messages: List[Dict[str, str]]) -> None:
    HISTORY_PATH.write_text(json.dumps(messages, ensure_ascii=False, indent=2), encoding="utf-8")


def reset_history() -> List[Dict[str, str]]:
    try:
        HISTORY_PATH.unlink(missing_ok=True)
    except TypeError:
        if HISTORY_PATH.exists():
            HISTORY_PATH.unlink()
    print("New conversation started.")
    return []
