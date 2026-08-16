"""Chiffrement symétrique Fernet pour les secrets stockés en base de données.

La clé est lue depuis la variable d'environnement FERNET_KEY ou le fichier
.env. Si elle est absente (première exécution), une clé est générée
automatiquement et ajoutée au fichier .env.

Important : le chemin du .env doit rester identique à celui de
config/settings.py (à côté de l'exe en version compilée, à la racine en dev).
Sinon, en exécutable, une nouvelle clé serait générée à chaque démarrage et
les mots de passe déjà stockés deviendraient indéchiffrables.
"""

import logging
import os
import sys

from cryptography.fernet import Fernet, InvalidToken

logger = logging.getLogger(__name__)


def _chemin_env() -> str:
    """Chemin du fichier .env — cohérent avec config/settings.py."""
    if getattr(sys, "frozen", False):
        base = os.path.dirname(sys.executable)
    else:
        base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base, ".env")


_ENV_PATH = _chemin_env()


def _lire_cle(chemin: str) -> str:
    """Lit la dernière valeur FERNET_KEY d'un fichier .env."""
    try:
        with open(chemin, encoding="utf-8") as f:
            cle = ""
            for ligne in f:
                ligne = ligne.strip()
                if not ligne or ligne.startswith("#") or "=" not in ligne:
                    continue
                nom, _, valeur = ligne.partition("=")
                if nom.strip() == "FERNET_KEY":
                    cle = valeur.strip()
            return cle
    except OSError:
        return ""


def _sauvegarder_cle(cle: str) -> None:
    """Écrit la clé dans le .env s'il n'y en a pas déjà une."""
    if _lire_cle(_ENV_PATH):
        return
    try:
        with open(_ENV_PATH, "a", encoding="utf-8") as f:
            f.write(f"\nFERNET_KEY={cle}\n")
        logger.info("CryptoService : clé Fernet ajoutée à %s", _ENV_PATH)
    except OSError as exc:
        logger.warning("CryptoService : impossible d'écrire dans .env (%s)", exc)


class CryptoService:
    _instance: "CryptoService | None" = None
    _fernet: Fernet | None = None

    def __new__(cls) -> "CryptoService":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialiser()
        return cls._instance

    def _initialiser(self) -> None:
        cle = os.getenv("FERNET_KEY", "").strip() or _lire_cle(_ENV_PATH)
        if not cle and getattr(sys, "frozen", False):
            # Migration : anciennes versions généraient la clé dans
            # sys._MEIPASS/.env (répertoire temporaire jamais relu). On la
            # réutilise pour ne pas perdre les mots de passe déjà chiffrés,
            # puis on la copie dans le .env à côté de l'exe.
            legacy = os.path.join(getattr(sys, "_MEIPASS", ""), ".env")
            cle = _lire_cle(legacy)
            if cle:
                _sauvegarder_cle(cle)
        if not cle:
            cle = self._generer_et_sauvegarder()
        else:
            os.environ["FERNET_KEY"] = cle
        try:
            self._fernet = Fernet(cle.encode())
        except Exception as exc:
            raise RuntimeError(
                f"FERNET_KEY invalide dans .env — supprimez-la pour en générer une nouvelle : {exc}"
            ) from exc

    def _generer_et_sauvegarder(self) -> str:
        cle = Fernet.generate_key().decode()
        _sauvegarder_cle(cle)
        os.environ["FERNET_KEY"] = cle
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
