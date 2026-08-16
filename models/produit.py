from dataclasses import dataclass
from datetime import datetime
from typing import Optional

CATEGORIES_PRODUITS: list[tuple[str, str]] = [
    ("film",     "Film"),
    ("serie",    "Série"),
    ("jeux",   "Jeux"),
    ("logiciel", "Logiciel"),
    ("accessoires_informatiques", "Accessoires informatiques"),
    ("autre", "Autre"),
]

_LABELS_CATEGORIES = dict(CATEGORIES_PRODUITS)


def libelle_categorie(code: str) -> str:
    return _LABELS_CATEGORIES.get(code, code)


@dataclass
class Produit:
    nom: str
    # Valeurs : "film", "serie", "jeux", "logiciel", "accessoires_informatiques", "autre"
    categorie: str
    # Prix par défaut ; None ou 0 → prix variable saisi à la vente
    prix_unitaire: Optional[float] = None
    actif: bool = True
    created_at: Optional[datetime] = None
    id: Optional[int] = None

    @property
    def prix_fixe(self) -> bool:
        return bool(self.prix_unitaire)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "nom": self.nom,
            "categorie": self.categorie,
            "prix_unitaire": self.prix_unitaire,
            "prix_fixe": self.prix_fixe,
            "actif": self.actif,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Produit":
        created = data.get("created_at")
        if isinstance(created, str) and created:
            created = datetime.fromisoformat(created)
        return cls(
            id=data.get("id"),
            nom=data["nom"],
            categorie=data["categorie"],
            prix_unitaire=data.get("prix_unitaire"),
            actif=bool(data.get("actif", True)),
            created_at=created,
        )
