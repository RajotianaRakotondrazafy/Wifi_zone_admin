"""Modèle représentant une transaction de vente d'un ticket WiFi."""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class Sale:
    """Enregistrement d'une vente de ticket réalisée par un caissier."""

    # Clé étrangère vers le ticket vendu
    ticket_id: int
    # Clé étrangère vers le caissier ayant effectué la vente
    user_id: int
    # Montant encaissé en unité monétaire locale
    montant: float
    date_vente: datetime
    # Exemple de valeurs : "especes", "mobile_money", "carte"
    methode_paiement: str
    id: Optional[int] = None

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "ticket_id": self.ticket_id,
            "user_id": self.user_id,
            "montant": self.montant,
            "date_vente": self.date_vente.isoformat(),
            "methode_paiement": self.methode_paiement,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Sale":
        return cls(
            id=data.get("id"),
            ticket_id=data["ticket_id"],
            user_id=data["user_id"],
            montant=data["montant"],
            date_vente=datetime.fromisoformat(data["date_vente"]),
            methode_paiement=data["methode_paiement"],
        )
