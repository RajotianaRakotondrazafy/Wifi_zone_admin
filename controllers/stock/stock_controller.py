from datetime import datetime

from models.produit import CATEGORIES_PRODUITS, libelle_categorie
from models.produit import Produit
from models.vente_produit import VenteProduit
from repositories.produit_repository import ProduitRepository


class StockController:
    """Gestion de la boutique / stock du multiservice (produits et ventes)."""

    def __init__(self):
        self._produit_repo = ProduitRepository()

    # ── Produits ─────────────────────────────────────────────────────────

    def obtenir_produits(self, actif_seulement: bool = True) -> list[dict]:
        produits = self._produit_repo.lister_produits(actif_seulement=actif_seulement)
        return [
            {
                **p.to_dict(),
                "categorie_label": libelle_categorie(p.categorie),
            }
            for p in produits
        ]

    def creer_produit(self, nom: str, categorie: str, prix_unitaire: float | None) -> dict:
        nom = nom.strip()
        if not nom:
            return {"ok": False, "message": "Le nom du produit est obligatoire."}
        if categorie not in [c for c, _ in CATEGORIES_PRODUITS]:
            return {"ok": False, "message": "Catégorie invalide."}
        try:
            produit = Produit(nom=nom, categorie=categorie, prix_unitaire=prix_unitaire)
            self._produit_repo.creer_produit(produit)
            return {"ok": True, "message": f"Produit « {nom} » ajouté.", "produit": produit}
        except Exception as exc:
            return {"ok": False, "message": str(exc)}

    def modifier_produit(
        self, produit_id: int, nom: str, categorie: str, prix_unitaire: float | None
    ) -> dict:
        nom = nom.strip()
        produit = self._produit_repo.obtenir_par_id(produit_id)
        if produit is None:
            return {"ok": False, "message": "Produit introuvable."}
        if not nom:
            return {"ok": False, "message": "Le nom du produit est obligatoire."}
        try:
            produit.nom = nom
            produit.categorie = categorie
            produit.prix_unitaire = prix_unitaire
            self._produit_repo.modifier_produit(produit)
            return {"ok": True, "message": f"Produit « {nom} » mis à jour."}
        except Exception as exc:
            return {"ok": False, "message": str(exc)}

    def definir_actif(self, produit_id: int, actif: bool) -> dict:
        try:
            self._produit_repo.definir_actif(produit_id, actif)
            return {"ok": True}
        except Exception as exc:
            return {"ok": False, "message": str(exc)}

    # ── Ventes ───────────────────────────────────────────────────────────

    def enregistrer_vente(
        self,
        produit_id: int,
        quantite: int,
        prix_unitaire: float,
        methode: str,
        user_id: int,
    ) -> dict:
        if quantite <= 0:
            return {"ok": False, "message": "La quantité doit être supérieure à 0."}
        if prix_unitaire < 0:
            return {"ok": False, "message": "Le prix ne peut pas être négatif."}
        try:
            vente = VenteProduit(
                produit_id=produit_id,
                quantite=quantite,
                prix_unitaire=prix_unitaire,
                montant=round(quantite * prix_unitaire, 2),
                methode_paiement=methode,
                date_vente=datetime.now(),
                user_id=user_id,
            )
            self._produit_repo.creer_vente(vente)
            return {"ok": True, "vente_id": vente.id, "montant": vente.montant}
        except Exception as exc:
            return {"ok": False, "message": str(exc)}

    def obtenir_ventes_du_jour(self, date: str | None = None) -> list[dict]:
        date = date or datetime.now().date().isoformat()
        ventes = self._produit_repo.lister_ventes_du_jour(date)
        return [self._construire_vente(v) for v in ventes]

    @staticmethod
    def _construire_vente(v: dict) -> dict:
        date_vente = v["date_vente"]
        if isinstance(date_vente, str):
            date_vente = datetime.fromisoformat(date_vente)
        return {
            "vente_id":       v["vente_id"],
            "annule":         bool(v.get("annule", 0)),
            "heure":          date_vente.strftime("%H:%M"),
            "produit":        v["produit_nom"],
            "categorie":      v["categorie"],
            "categorie_label": libelle_categorie(v["categorie"]),
            "quantite":       v["quantite"],
            "prix_unitaire":  v["prix_unitaire"],
            "montant":        v["montant"],
            "methode":        v["methode_paiement"],
        }

    def total_du_jour(self, date: str | None = None) -> dict:
        date = date or datetime.now().date().isoformat()
        return self._produit_repo.agreger_du_jour(date)

    def ventes_par_categorie_du_jour(self, date: str | None = None) -> list[dict]:
        date = date or datetime.now().date().isoformat()
        lignes = self._produit_repo.ventes_par_categorie_du_jour(date)
        return [
            {
                **l,
                "categorie_label": libelle_categorie(l["categorie"]),
            }
            for l in lignes
        ]

    def annuler_vente(self, vente_id: int) -> dict:
        try:
            self._produit_repo.annuler_vente(vente_id)
            return {"ok": True, "message": "Vente produit annulée."}
        except Exception as exc:
            return {"ok": False, "message": str(exc)}
