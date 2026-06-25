"""Modèle représentant une entrée dans le journal d'activité de l'application."""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class ActivityLog:
    """Trace d'audit d'une action réalisée par un utilisateur dans le système."""

    # Clé étrangère vers l'utilisateur ayant déclenché l'action
    user_id: int
    # Description courte de l'action (ex : "creation_ticket", "login", "suppression_profil")
    action: str
    date: datetime
    # Données complémentaires en JSON ou texte libre (ex : id du ticket créé)
    details: Optional[str] = None
    id: Optional[int] = None

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "user_id": self.user_id,
            "action": self.action,
            "date": self.date.isoformat(),
            "details": self.details,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "ActivityLog":
        return cls(
            id=data.get("id"),
            user_id=data["user_id"],
            action=data["action"],
            date=datetime.fromisoformat(data["date"]),
            details=data.get("details"),
        )
