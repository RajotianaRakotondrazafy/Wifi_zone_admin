from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class Blocage:
    """Appareil bloqué sur le hotspot."""

    mac_address: str
    nom: str = "Appareil inconnu"
    ip_assignee: str = ""
    raison: str = "Bloqué manuellement"
    date_blocage: Optional[datetime] = None
    id: Optional[int] = None

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "mac_address": self.mac_address,
            "nom": self.nom,
            "ip_assignee": self.ip_assignee,
            "raison": self.raison,
            "date_blocage": self.date_blocage.isoformat() if self.date_blocage else None,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Blocage":
        return cls(
            id=data.get("id"),
            mac_address=data["mac_address"],
            nom=data.get("nom", "Appareil inconnu"),
            ip_assignee=data.get("ip_assignee", ""),
            raison=data.get("raison", "Bloqué manuellement"),
            date_blocage=datetime.fromisoformat(data["date_blocage"])
            if data.get("date_blocage") else None,
        )
