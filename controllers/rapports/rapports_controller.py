import csv
import os
from datetime import date, timedelta

from repositories.sale_repository import SaleRepository
from repositories.produit_repository import ProduitRepository
from repositories.depense_repository import DepenseRepository


def _lundi_semaine(d: date) -> date:
    return d - timedelta(days=d.weekday())


def _premier_du_mois(d: date) -> date:
    return d.replace(day=1)


def _dernier_du_mois(d: date) -> date:
    if d.month == 12:
        return d.replace(month=12, day=31)
    return d.replace(month=d.month + 1, day=1) - timedelta(days=1)


PERIODES = [
    "Ce mois",
    "Mois précédent",
    "Cette semaine",
    "7 derniers jours",
    "30 derniers jours",
]


class RapportsController:

    def __init__(self):
        self._sale_repo = SaleRepository()
        self._produit_repo = ProduitRepository()
        self._depense_repo = DepenseRepository()

    def plage_pour_periode(self, periode: str) -> tuple[str, str]:
        """Retourne (date_debut, date_fin) en ISO pour la période choisie."""
        aujourd_hui = date.today()
        if periode == "Ce mois":
            debut = _premier_du_mois(aujourd_hui)
            fin   = aujourd_hui
        elif periode == "Mois précédent":
            dernier_mois = aujourd_hui.replace(day=1) - timedelta(days=1)
            debut = _premier_du_mois(dernier_mois)
            fin   = _dernier_du_mois(dernier_mois)
        elif periode == "Cette semaine":
            debut = _lundi_semaine(aujourd_hui)
            fin   = aujourd_hui
        elif periode == "7 derniers jours":
            debut = aujourd_hui - timedelta(days=6)
            fin   = aujourd_hui
        else:  # "30 derniers jours"
            debut = aujourd_hui - timedelta(days=29)
            fin   = aujourd_hui
        return debut.isoformat(), fin.isoformat()

    def rapport_complet(self, date_debut: str, date_fin: str) -> dict:
        synthese      = self._sale_repo.agreger_par_periode(date_debut, date_fin)
        par_jour      = self._sale_repo.ventes_par_jour(date_debut, date_fin)
        top_profils   = self._sale_repo.top_profils_periode(date_debut, date_fin)
        produits      = self._produit_repo.agreger_par_periode(date_debut, date_fin)
        par_categorie = self._produit_repo.ventes_par_categorie_periode(date_debut, date_fin)

        ca_accessoires = sum(r["ca"] for r in par_categorie if r["categorie"] == "accessoires")
        ca_accessoires = int(ca_accessoires or 0)
        ca_tickets     = int(synthese["ca_total"] or 0)
        ca_produits    = int(produits["ca_total"] or 0)
        ca_total       = ca_tickets + ca_produits
        depenses_total = self._depense_repo.agreger_par_periode(date_debut, date_fin)
        return {
            "synthese":            synthese,
            "par_jour":            par_jour,
            "top_profils":         top_profils,
            "produits":            produits,
            "par_categorie":       par_categorie,
            "ca_tickets":          ca_tickets,
            "ca_accessoires":      ca_accessoires,
            "ca_autres_produits":  max(0, ca_produits - ca_accessoires),
            "ca_total":            ca_total,
            "depenses_total":      depenses_total,
            "benefice_net":        max(0, ca_total - depenses_total),
        }

    def exporter_csv(self, chemin: str, date_debut: str, date_fin: str,
                     par_jour: list[dict]) -> int:
        os.makedirs(os.path.dirname(chemin), exist_ok=True) if os.path.dirname(chemin) else None
        with open(chemin, "w", newline="", encoding="utf-8-sig") as f:
            writer = csv.writer(f, delimiter=";")
            writer.writerow(["Date", "Nb ventes", "CA (Ar)"])
            for ligne in par_jour:
                jour_iso = ligne["jour"]
                jour_fr  = f"{jour_iso[8:10]}/{jour_iso[5:7]}/{jour_iso[:4]}"
                writer.writerow([jour_fr, ligne["nb_ventes"], int(ligne["ca"])])
        return len(par_jour)
