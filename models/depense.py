from dataclasses import dataclass
from datetime import datetime
from typing import Optional

CATEGORIES_DEPENSES: list[tuple[str, str]] = [
    ("internet",    "Internet / Connexion"),
    ("electricite", "Électricité"),
    ("fourniture",  "Fournitures"),
    ("materiel",    "Matériel / Maintenance"),
    ("salaire",     "Salaires"),
    ("autre",       "Autre"),
]

_LABELS_CATEGORIES = dict(CATEGORIES_DEPENSES)


def libelle_categorie(code: str) -> str:
    return _LABELS_CATEGORIES.get(code, code)


@dataclass
class Depense:
    montant: float
    motif: str
    # Valeurs : "internet", "electricite", "fourniture", "materiel", "salaire", "autre"
    categorie: str = "autre"
    methode_paiement: str = "especes"
    date_depense: Optional[datetime] = None
    user_id: Optional[int] = None
    annule: bool = False
    date_annulation: Optional[datetime] = None
    id: Optional[int] = None

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "montant": self.montant,
            "motif": self.motif,
            "categorie": self.categorie,
            "methode_paiement": self.methode_paiement,
            "date_depense": self.date_depense.isoformat() if self.date_depense else None,
            "user_id": self.user_id,
            "annule": self.annule,
            "date_annulation": self.date_annulation.isoformat() if self.date_annulation else None,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Depense":
        date_depense = data.get("date_depense")
        if isinstance(date_depense, str) and date_depense:
            date_depense = datetime.fromisoformat(date_depense)
        date_annulation = data.get("date_annulation")
        if isinstance(date_annulation, str) and date_annulation:
            date_annulation = datetime.fromisoformat(date_annulation)
        return cls(
            id=data.get("id"),
            montant=data["montant"],
            motif=data["motif"],
            categorie=data.get("categorie", "autre"),
            methode_paiement=data.get("methode_paiement", "especes"),
            date_depense=date_depense,
            user_id=data.get("user_id"),
            annule=bool(data.get("annule", 0)),
            date_annulation=date_annulation,
        )