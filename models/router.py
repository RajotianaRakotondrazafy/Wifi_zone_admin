"""Modèle représentant un routeur MikroTik géré par l'application."""

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class Router:
    """Routeur MikroTik connecté à la zone WiFi."""

    nom: str
    adresse_ip: str
    port_api: int
    username: str
    # Mot de passe stocké chiffré en base de données
    password_chiffre: str
    statut: str = "inactif"  # "actif" | "inactif" | "erreur"
    id: Optional[int] = None

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "nom": self.nom,
            "adresse_ip": self.adresse_ip,
            "port_api": self.port_api,
            "username": self.username,
            "password_chiffre": self.password_chiffre,
            "statut": self.statut,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Router":
        return cls(
            id=data.get("id"),
            nom=data["nom"],
            adresse_ip=data["adresse_ip"],
            port_api=data["port_api"],
            username=data["username"],
            password_chiffre=data["password_chiffre"],
            statut=data.get("statut", "inactif"),
        )
