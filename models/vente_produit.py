from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class VenteProduit:
    produit_id: int
    quantite: int
    # Prix unitaire réellement facturé (peut différer du prix par défaut)
    prix_unitaire: float
    montant: float
    methode_paiement: str
    date_vente: datetime
    user_id: int
    annule: bool = False
    date_annulation: Optional[datetime] = None
    id: Optional[int] = None

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "produit_id": self.produit_id,
            "quantite": self.quantite,
            "prix_unitaire": self.prix_unitaire,
            "montant": self.montant,
            "methode_paiement": self.methode_paiement,
            "date_vente": self.date_vente.isoformat(),
            "user_id": self.user_id,
            "annule": self.annule,
            "date_annulation": self.date_annulation.isoformat() if self.date_annulation else None,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "VenteProduit":
        date_vente = data["date_vente"]
        if isinstance(date_vente, str):
            date_vente = datetime.fromisoformat(date_vente)
        annulation = data.get("date_annulation")
        if isinstance(annulation, str) and annulation:
            annulation = datetime.fromisoformat(annulation)
        return cls(
            id=data.get("id"),
            produit_id=data["produit_id"],
            quantite=data["quantite"],
            prix_unitaire=data["prix_unitaire"],
            montant=data["montant"],
            methode_paiement=data["methode_paiement"],
            date_vente=date_vente,
            user_id=data["user_id"],
            annule=bool(data.get("annule", False)),
            date_annulation=annulation,
        )
