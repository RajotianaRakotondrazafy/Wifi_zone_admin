from dotenv import load_dotenv
import os

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

_BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

DATABASE_PATH = os.getenv(
    "DATABASE_PATH",
    os.path.join(_BASE_DIR, "database", "app.db"),
)

MIKROTIK_HOST = os.getenv("MIKROTIK_HOST")
MIKROTIK_PORT = int(os.getenv("MIKROTIK_PORT"))

MIKROTIK_USER = os.getenv("MIKROTIK_USER")
MIKROTIK_PASSWORD = os.getenv("MIKROTIK_PASSWORD")