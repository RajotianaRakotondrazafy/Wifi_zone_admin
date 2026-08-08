import sys
from dotenv import load_dotenv
import os

# ── Chemins de base ──────────────────────────────────────────────────────────
# Détecte si l'app tourne en mode compilé (PyInstaller) ou en développement.
if getattr(sys, "frozen", False):
    # Exécutable PyInstaller (--onedir) : l'exe et les données sont dans le
    # même dossier ; les ressources bundlées sont dans sys._MEIPASS.
    _DATA_DIR     = os.path.dirname(sys.executable)
    _RESOURCE_DIR = sys._MEIPASS  # type: ignore[attr-defined]
else:
    _DATA_DIR     = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    _RESOURCE_DIR = _DATA_DIR

load_dotenv(os.path.join(_DATA_DIR, ".env"))


def _chemin_donnees(relatif: str) -> str:
    """Chemin vers un fichier mutable (DB, logs) — à côté de l'exe en prod."""
    return os.path.join(_DATA_DIR, relatif)


def _chemin_ressource(relatif: str) -> str:
    """Chemin vers une ressource bundlée en lecture seule (assets, migrations)."""
    return os.path.join(_RESOURCE_DIR, relatif)


# ── Base de données ───────────────────────────────────────────────────────────
DATABASE_PATH = os.getenv("DATABASE_PATH") or _chemin_donnees(
    os.path.join("database", "app.db")
)

# ── Tarification ─────────────────────────────────────────────────────────────
# Valeurs par défaut utilisées si la table `parametres` ne contient pas
# encore les clés correspondantes (premier démarrage, ou .env personnalisé).
TARIFICATION_PRIX_PAR_HEURE    = int(os.getenv("TARIFICATION_PRIX_PAR_HEURE",    "1000"))
TARIFICATION_DEBIT_DEFAUT_MBPS = int(os.getenv("TARIFICATION_DEBIT_DEFAUT_MBPS", "2"))
TARIFICATION_LIBRE_MIN_AR      = int(os.getenv("TARIFICATION_LIBRE_MIN_AR",      "500"))
TARIFICATION_LIBRE_MIN_MIN     = int(os.getenv("TARIFICATION_LIBRE_MIN_MIN",     "30"))
