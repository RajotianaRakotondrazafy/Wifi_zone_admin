"""Chiffrement symétrique Fernet pour les secrets stockés en base de données.

La clé est lue depuis la variable d'environnement FERNET_KEY.
Si elle est absente (première exécution), une clé est générée automatiquement
et ajoutée au fichier .env situé à la racine du projet.
"""

import logging
import os

from cryptography.fernet import Fernet, InvalidToken

logger = logging.getLogger(__name__)

_BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_ENV_PATH = os.path.join(_BASE_DIR, ".env")


class CryptoService:
    _instance: "CryptoService | None" = None
    _fernet: Fernet | None = None

    def __new__(cls) -> "CryptoService":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialiser()
        return cls._instance

    def _initialiser(self) -> None:
        cle = os.getenv("FERNET_KEY", "").strip()
        if not cle:
            cle = self._generer_et_sauvegarder()
        try:
            self._fernet = Fernet(cle.encode())
        except Exception as exc:
            raise RuntimeError(
                f"FERNET_KEY invalide dans .env — supprimez-la pour en générer une nouvelle : {exc}"
            ) from exc

    def _generer_et_sauvegarder(self) -> str:
        cle = Fernet.generate_key().decode()
        try:
            with open(_ENV_PATH, "a", encoding="utf-8") as f:
                f.write(f"\nFERNET_KEY={cle}\n")
            os.environ["FERNET_KEY"] = cle
            logger.info("CryptoService : clé Fernet générée et ajoutée à .env")
        except OSError as exc:
            logger.warning("CryptoService : impossible d'écrire dans .env (%s)", exc)
        return cle

    # ── API publique ──────────────────────────────────────────────────────

    def chiffrer(self, valeur: str) -> str:
        """Retourne la valeur chiffrée en base64 (safe à stocker en DB)."""
        return self._fernet.encrypt(valeur.encode("utf-8")).decode("utf-8")

    def dechiffrer(self, valeur: str) -> str:
        """Déchiffre une valeur chiffrée. Lève ValueError si le token est invalide."""
        try:
            return self._fernet.decrypt(valeur.encode("utf-8")).decode("utf-8")
        except InvalidToken as exc:
            raise ValueError("Token Fernet invalide — clé incorrecte ou donnée corrompue.") from exc

    def est_chiffre(self, valeur: str) -> bool:
        """Vérifie rapidement si une valeur ressemble à un token Fernet."""
        try:
            self._fernet.decrypt(valeur.encode("utf-8"))
            return True
        except (InvalidToken, Exception):
            return False
