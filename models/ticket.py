from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Optional


class StatutTicket(str, Enum):
    NON_UTILISE = "non_utilise"
    ACTIF = "actif"
    EXPIRE = "expire"
    EPUISE = "epuise"  # quota de données atteint


@dataclass
class Ticket:
    # Code affiché sur le ticket imprimé, saisi par le client
    code: str
    # Mot de passe MikroTik hotspot associé au code
    password: str
    # Clé étrangère vers le profil qui définit la vitesse
    profile_id: int
    # Durée max de session en minutes (stockée sur le ticket)
    duree_session_max: int
    # Validité en heures après première connexion (stockée sur le ticket)
    validite: int
    statut: StatutTicket = StatutTicket.NON_UTILISE
    date_generation: Optional[datetime] = None
    # Nom d'affichage (ex. "Perso 10 Mbps" pour un ticket personnalisé) — sinon le nom du profil
    nom_affichage: Optional[str] = None
    # Renseignée lors de la première authentification du client
    date_premiere_connexion: Optional[datetime] = None
    # Calculée : date_premiere_connexion + validite
    date_expiration: Optional[datetime] = None
    id: Optional[int] = None

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "code": self.code,
            "password": self.password,
            "profile_id": self.profile_id,
            "duree_session_max": self.duree_session_max,
            "validite": self.validite,
            "statut": self.statut.value if isinstance(self.statut, StatutTicket) else self.statut,
            "date_generation": self.date_generation.isoformat() if self.date_generation else None,
            "nom_affichage": self.nom_affichage,
            "date_premiere_connexion": self.date_premiere_connexion.isoformat() if self.date_premiere_connexion else None,
            "date_expiration": self.date_expiration.isoformat() if self.date_expiration else None,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Ticket":
        def _parse_dt(val: Optional[str]) -> Optional[datetime]:
            return datetime.fromisoformat(val) if val else None

        return cls(
            id=data.get("id"),
            code=data["code"],
            password=data["password"],
            profile_id=data["profile_id"],
            duree_session_max=data["duree_session_max"],
            validite=data["validite"],
            statut=StatutTicket(data.get("statut", StatutTicket.NON_UTILISE.value)),
            date_generation=_parse_dt(data.get("date_generation")),
            nom_affichage=data.get("nom_affichage"),
            date_premiere_connexion=_parse_dt(data.get("date_premiere_connexion")),
            date_expiration=_parse_dt(data.get("date_expiration")),
        )
