from dotenv import load_dotenv
import os

load_dotenv()

_BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# ── Base de données ───────────────────────────────────────────────────────────
DATABASE_PATH = os.getenv(
    "DATABASE_PATH",
    os.path.join(_BASE_DIR, "database", "app.db"),
)

# ── Tarification ─────────────────────────────────────────────────────────────
# Valeurs par défaut utilisées si la table `parametres` ne contient pas
# encore les clés correspondantes (premier démarrage, ou .env personnalisé).
TARIFICATION_PRIX_PAR_HEURE    = int(os.getenv("TARIFICATION_PRIX_PAR_HEURE",    "1000"))
TARIFICATION_DEBIT_DEFAUT_MBPS = int(os.getenv("TARIFICATION_DEBIT_DEFAUT_MBPS", "2"))
TARIFICATION_LIBRE_MIN_AR      = int(os.getenv("TARIFICATION_LIBRE_MIN_AR",      "500"))
TARIFICATION_LIBRE_MIN_MIN     = int(os.getenv("TARIFICATION_LIBRE_MIN_MIN",     "30"))
