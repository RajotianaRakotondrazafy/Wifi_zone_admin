from dataclasses import dataclass
from enum import Enum
from typing import Optional


class RoleUtilisateur(str, Enum):
    """Rôles disponibles dans l'application backoffice."""
    ADMIN = "admin"       # accès complet : configuration, rapports, gestion utilisateurs
    CAISSIER = "caissier" # accès limité : vente de ticket et consultation des ventes


@dataclass
class User:
    """Compte utilisateur de l'interface d'administration WiFi zone."""

    nom: str
    login: str
    # Hash bcrypt ou similaire — jamais le mot de passe en clair
    mot_de_passe_hash: str
    role: RoleUtilisateur = RoleUtilisateur.CAISSIER
    id: Optional[int] = None

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "nom": self.nom,
            "login": self.login,
            "mot_de_passe_hash": self.mot_de_passe_hash,
            "role": self.role.value if isinstance(self.role, RoleUtilisateur) else self.role,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "User":
        return cls(
            id=data.get("id"),
            nom=data["nom"],
            login=data["login"],
            mot_de_passe_hash=data["mot_de_passe_hash"],
            role=RoleUtilisateur(data.get("role", RoleUtilisateur.CAISSIER.value)),
        )
