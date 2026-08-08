import os
import re
from pathlib import Path

from config.settings import _chemin_ressource

CHEMIN_STYLES = Path(_chemin_ressource(os.path.join("assets", "styles")))
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
