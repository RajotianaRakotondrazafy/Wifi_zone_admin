from typing import Optional

import bcrypt

from models.user import User
from repositories.user_repository import UserRepository


class AuthController:
    def __init__(self):
        self.user_repository = UserRepository()

    def authentifier(self, login: str, mot_de_passe: str) -> Optional[User]:
        if not login or not mot_de_passe:
            return None

        try:
            user = self.user_repository.get_by_login(login.strip())
        except RuntimeError:
            return None

        if user is None or not user.actif:
            return None

        mot_de_passe_valide = bcrypt.checkpw(
            mot_de_passe.encode("utf-8"),
            user.mot_de_passe_hash.encode("utf-8"),
        )

        return user if mot_de_passe_valide else None
