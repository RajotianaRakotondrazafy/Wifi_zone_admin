from datetime import datetime

from models.depense import CATEGORIES_DEPENSES, Depense, libelle_categorie
from repositories.depense_repository import DepenseRepository

_METHODES = {
    "especes":      "Espèces",
    "mobile_money": "Mobile Money",
    "carte":        "Carte",
}


class DepensesController:
    """Gestion des dépenses du multiservice."""

    def __init__(self):
        self._depense_repo = DepenseRepository()

    def creer_depense(
        self,
        montant: float,
        motif: str,
        categorie: str,
        methode: str,
        user_id: int,
    ) -> dict:
        motif = motif.strip()
        if not motif:
            return {"ok": False, "message": "Le motif de la dépense est obligatoire."}
        if montant <= 0:
            return {"ok": False, "message": "Le montant doit être supérieur à 0."}
        if categorie not in [c for c, _ in CATEGORIES_DEPENSES]:
            return {"ok": False, "message": "Catégorie invalide."}
        if methode not in _METHODES:
            return {"ok": False, "message": "Méthode de paiement invalide."}
        try:
            depense = Depense(
                montant=round(montant, 2),
                motif=motif,
                categorie=categorie,
                methode_paiement=methode,
                date_depense=datetime.now(),
                user_id=user_id,
            )
            self._depense_repo.creer(depense)
            return {"ok": True, "message": "Dépense enregistrée.", "depense_id": depense.id}
        except Exception as exc:
            return {"ok": False, "message": str(exc)}

    def obtenir_depenses_du_jour(self, date: str | None = None) -> list[dict]:
        date = date or datetime.now().date().isoformat()
        return [self._construire_depense(d) for d in self._depense_repo.lister_du_jour(date)]

    @staticmethod
    def _construire_depense(d: dict) -> dict:
        date_depense = d["date_depense"]
        if isinstance(date_depense, str) and date_depense:
            date_depense = datetime.fromisoformat(date_depense)
        return {
            "depense_id":      d["id"],
            "annule":          bool(d.get("annule", 0)),
            "heure":           date_depense.strftime("%H:%M"),
            "motif":           d["motif"],
            "categorie":       d["categorie"],
            "categorie_label": libelle_categorie(d["categorie"]),
            "montant":         d["montant"],
            "methode":         d["methode_paiement"],
            "methode_label":   _METHODES.get(d["methode_paiement"], "—"),
        }

    def total_du_jour(self, date: str | None = None) -> dict:
        date = date or datetime.now().date().isoformat()
        return self._depense_repo.agreger_du_jour(date)

    def annuler_depense(self, depense_id: int) -> dict:
        try:
            self._depense_repo.annuler(depense_id)
            return {"ok": True, "message": "Dépense annulée."}
        except Exception as exc:
            return {"ok": False, "message": str(exc)}