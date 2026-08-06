"""Modèle représentant un profil hotspot MikroTik (ex : 1h-5MB, journalier, etc.)."""

from dataclasses import dataclass
from typing import Optional


@dataclass
class HotspotProfile:
    """Profil d'accès hotspot définissant les limites de débit, durée et prix."""

    # Clé étrangère vers le routeur qui héberge ce profil
    router_id: int
    nom: str
    # Débit maximum en kbps (ex : 2048 pour 2 Mbps)
    debit_max: int
    # Durée maximale d'une session en minutes
    duree_session_max: int
    # Validité du ticket en heures après première connexion
    validite: int
    # Prix de vente en unité monétaire locale
    prix: float
    # Nombre maximum d'appareils simultanés (shared-users MikroTik) — 1 = usage exclusif
    utilisateurs_max: int = 1
    # Statut : 'actif' (proposé à la vente) | 'inactif' (masqué)
    statut: str = "actif"
    id: Optional[int] = None

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "router_id": self.router_id,
            "nom": self.nom,
            "debit_max": self.debit_max,
            "duree_session_max": self.duree_session_max,
            "validite": self.validite,
            "prix": self.prix,
            "utilisateurs_max": self.utilisateurs_max,
            "statut": self.statut,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "HotspotProfile":
        return cls(
            id=data.get("id"),
            router_id=data["router_id"],
            nom=data["nom"],
            debit_max=data["debit_max"],
            duree_session_max=data["duree_session_max"],
            validite=data["validite"],
            prix=data["prix"],
            utilisateurs_max=data.get("utilisateurs_max", 1),
            statut=data.get("statut", "actif"),
        )
