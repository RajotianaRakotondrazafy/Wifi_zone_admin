import os
import re
from pathlib import Path


CHEMIN_STYLES = Path(__file__).resolve().parent.parent / "assets" / "styles"
CHEMIN_THEME = CHEMIN_STYLES / "dark_theme.qss"

_IMPORT = re.compile(r'@import\s+["\']([^"\']+)["\']\s*;')


def charger_theme() -> str:
    """Retourne le QSS complet (dark_theme.qss + fichiers importés)."""
    qss = CHEMIN_THEME.read_text(encoding="utf-8")

    def _resoudre(match: re.Match) -> str:
        chemin = CHEMIN_STYLES / match.group(1)
        if not chemin.exists():
            return ""
        return chemin.read_text(encoding="utf-8")

    return _IMPORT.sub(_resoudre, qss)
