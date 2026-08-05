import bcrypt

from models.user import User, RoleUtilisateur
from repositories.user_repository import UserRepository


class UtilisateursController:
    def __init__(self):
        self._user_repo = UserRepository()

    def obtenir_utilisateurs(self) -> list[dict]:
        return [
            {
                "id":    u.id,
                "nom":   u.nom,
                "login": u.login,
                "role":  u.role.value,
                "actif": u.actif,
            }
            for u in self._user_repo.lister_tous()
        ]

    def creer_utilisateur(self, data: dict) -> None:
        nom = data.get("nom", "").strip()
        login = data.get("login", "").strip()
        mot_de_passe = data.get("mot_de_passe", "")

        if not nom or not login or not mot_de_passe:
            raise RuntimeError("Nom, identifiant et mot de passe sont obligatoires.")

        utilisateur = User(
            nom=nom,
            login=login,
            mot_de_passe_hash=self._hasher(mot_de_passe),
            role=RoleUtilisateur(data.get("role", RoleUtilisateur.CAISSIER.value)),
            actif=data.get("actif", True),
        )
        self._user_repo.create_user(utilisateur)

    def modifier_utilisateur(self, data: dict) -> None:
        utilisateur = self._obtenir_par_id(data.get("id"))
        utilisateur.nom = data.get("nom", utilisateur.nom).strip()
        utilisateur.login = data.get("login", utilisateur.login).strip()
        utilisateur.role = RoleUtilisateur(data.get("role", utilisateur.role.value))
        utilisateur.actif = data.get("actif", utilisateur.actif)

        # Mot de passe laissé vide → on conserve le hash existant
        mot_de_passe = data.get("mot_de_passe", "")
        if mot_de_passe:
            utilisateur.mot_de_passe_hash = self._hasher(mot_de_passe)

        self._user_repo.update(utilisateur)

    def supprimer_utilisateur(self, user_id: int) -> None:
        self._user_repo.supprimer(user_id)

    def basculer_actif(self, user_id: int) -> bool:
        """Inverse l'état actif/inactif. Retourne le nouvel état."""
        return self._user_repo.basculer_actif(user_id)

    # ── Helpers ──────────────────────────────────────────────────────────

    def _obtenir_par_id(self, user_id) -> User:
        if user_id is None:
            raise RuntimeError("Identifiant utilisateur manquant.")
        for utilisateur in self._user_repo.lister_tous():
            if utilisateur.id == int(user_id):
                return utilisateur
        raise RuntimeError("Utilisateur introuvable.")

    @staticmethod
    def _hasher(mot_de_passe: str) -> str:
        return bcrypt.hashpw(mot_de_passe.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
