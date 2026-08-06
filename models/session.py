from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class Session:
    # Clé étrangère vers le ticket utilisé pour cette session
    ticket_id: int
    # Adresse MAC de l'appareil client (identifiant réseau unique)
    mac_address: str
    # Adresse IP attribuée par le DHCP du hotspot MikroTik
    ip_assignee: str
    date_debut: datetime
    date_fin: Optional[datetime] = None
    # Volume de données montant en octets (client → internet)
    octets_envoyes: int = 0
    # Volume de données descendant en octets (internet → client)
    octets_recus: int = 0
    # Durée effective de la session en secondes
    duree_reelle: Optional[int] = None
    # Nom d'hôte DHCP (nom d'appareil) si connu
    nom_hote: Optional[str] = None
    id: Optional[int] = None

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "ticket_id": self.ticket_id,
            "mac_address": self.mac_address,
            "ip_assignee": self.ip_assignee,
            "date_debut": self.date_debut.isoformat(),
            "date_fin": self.date_fin.isoformat() if self.date_fin else None,
            "octets_envoyes": self.octets_envoyes,
            "octets_recus": self.octets_recus,
            "duree_reelle": self.duree_reelle,
            "nom_hote": self.nom_hote,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Session":
        return cls(
            id=data.get("id"),
            ticket_id=data["ticket_id"],
            mac_address=data["mac_address"],
            ip_assignee=data["ip_assignee"],
            date_debut=datetime.fromisoformat(data["date_debut"]),
            date_fin=datetime.fromisoformat(data["date_fin"]) if data.get("date_fin") else None,
            octets_envoyes=data.get("octets_envoyes", 0),
            octets_recus=data.get("octets_recus", 0),
            duree_reelle=data.get("duree_reelle"),
            nom_hote=data.get("nom_hote"),
        )
