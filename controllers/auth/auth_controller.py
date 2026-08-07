import time
from collections import defaultdict
from typing import Optional

import bcrypt

from models.user import User
from repositories.user_repository import UserRepository

_MAX_TENTATIVES = 5
_BLOCAGE_SEC    = 30


class AuthController:
    def __init__(self):
        self.user_repository = UserRepository()
        self._tentatives: dict[str, int]   = defaultdict(int)
        self._bloque_jusqu: dict[str, float] = {}

    def authentifier(self, login: str, mot_de_passe: str) -> Optional[User]:
        """Vérifie les identifiants et retourne l'utilisateur ou None.

        Lève RuntimeError si le compte est temporairement bloqué après trop
        de tentatives échouées.
        """
        if not login or not mot_de_passe:
            return None

        login = login.strip()
        now   = time.monotonic()

        # ── Vérification du blocage ───────────────────────────────────────
        if login in self._bloque_jusqu:
            restant = self._bloque_jusqu[login] - now
            if restant > 0:
                raise RuntimeError(
                    f"Trop de tentatives. Réessayez dans {int(restant) + 1} seconde(s)."
                )
            # Blocage expiré
            del self._bloque_jusqu[login]
            self._tentatives[login] = 0

        # ── Vérification des identifiants ────────────────────────────────
        try:
            user = self.user_repository.get_by_login(login)
        except RuntimeError:
            return None

        if user is None or not user.actif:
            return None

        valide = bcrypt.checkpw(
            mot_de_passe.encode("utf-8"),
            user.mot_de_passe_hash.encode("utf-8"),
        )

        if not valide:
            self._tentatives[login] += 1
            if self._tentatives[login] >= _MAX_TENTATIVES:
                self._bloque_jusqu[login] = now + _BLOCAGE_SEC
                self._tentatives[login]   = 0
                raise RuntimeError(
                    f"Trop de tentatives échouées. "
                    f"Compte bloqué pendant {_BLOCAGE_SEC} secondes."
                )
            restantes = _MAX_TENTATIVES - self._tentatives[login]
            raise RuntimeError(
                f"Identifiant ou mot de passe incorrect. "
                f"{restantes} tentative(s) restante(s)."
            )

        # Succès — réinitialiser le compteur
        self._tentatives[login] = 0
        return user

    def restant_blocage(self, login: str) -> int:
        """Retourne le nombre de secondes restantes du blocage (0 si pas bloqué)."""
        if login not in self._bloque_jusqu:
            return 0
        restant = self._bloque_jusqu[login] - time.monotonic()
        return max(0, int(restant) + 1)
