import json
import os

from models.user import User

_SESSION_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    ".session.json",
)


def sauvegarder_session(user: User) -> None:
    try:
        with open(_SESSION_PATH, "w", encoding="utf-8") as f:
            json.dump(user.to_dict(), f, ensure_ascii=False, indent=2)
    except OSError:
        pass


def charger_session() -> User | None:
    if not os.path.exists(_SESSION_PATH):
        return None
    try:
        with open(_SESSION_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        return User.from_dict(data)
    except (OSError, ValueError, KeyError):
        return None


def effacer_session() -> None:
    try:
        if os.path.exists(_SESSION_PATH):
            os.remove(_SESSION_PATH)
    except OSError:
        pass
