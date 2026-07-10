from datetime import datetime, timedelta


# TODO: remplacer par hotspot_profile_repository.lister_tous()
_PROFILS_FACTICES = [
    {"id": 1, "nom": "1h — 2 Mbps",   "debit_max": 2048,  "duree_session_max": 60,   "validite": 24,  "prix": 500.0},
    {"id": 2, "nom": "3h — 5 Mbps",   "debit_max": 5120,  "duree_session_max": 180,  "validite": 48,  "prix": 1000.0},
    {"id": 3, "nom": "Journalier",     "debit_max": 10240, "duree_session_max": 1440, "validite": 24,  "prix": 2000.0},
    {"id": 4, "nom": "Hebdomadaire",   "debit_max": 10240, "duree_session_max": 10080,"validite": 168, "prix": 10000.0},
]


class VentesController:
    """Orchestration de la page Ventes : profils, historique, enregistrement."""

    def obtenir_profils(self) -> list[dict]:
        """Retourne les profils hotspot disponibles à la vente.

        TODO: hotspot_profile_repository.lister_par_router(router_id)
        """
        return _PROFILS_FACTICES

    def obtenir_ventes_du_jour(self) -> list[dict]:
        """Retourne les ventes du jour enrichies avec les données de timing.

        TODO: sale_repository.get_all_sales_by_date(datetime.today().date().isoformat())
              + jointure ticket + profil → nom_profil, code, profil_duree_min
        """
        now = datetime.now()

        # Données factices avec heures relatives à maintenant pour que les timers fonctionnent
        ventes_brutes = [
            {
                "heure_dt":       now - timedelta(hours=3, minutes=28),
                "profil":         "1h — 2 Mbps",
                "profil_duree_min": 60,
                "code":           "ABC-1234",
                "methode":        "especes",
                "montant":        500.0,
            },
            {
                "heure_dt":       now - timedelta(minutes=47),
                "profil":         "3h — 5 Mbps",
                "profil_duree_min": 180,
                "code":           "XKY-5678",
                "methode":        "mobile_money",
                "montant":        1000.0,
            },
            {
                "heure_dt":       now - timedelta(hours=1, minutes=15),
                "profil":         "Journalier",
                "profil_duree_min": 1440,
                "code":           "ZQM-9012",
                "methode":        "especes",
                "montant":        2000.0,
            },
            {
                "heure_dt":       now - timedelta(hours=2, minutes=10),
                "profil":         "1h — 2 Mbps",
                "profil_duree_min": 60,
                "code":           "PBT-3456",
                "methode":        "carte",
                "montant":        500.0,
            },
            {
                "heure_dt":       now - timedelta(minutes=12),
                "profil":         "3h — 5 Mbps",
                "profil_duree_min": 180,
                "code":           "LWR-7890",
                "methode":        "especes",
                "montant":        1000.0,
            },
        ]

        # Calcul automatique de l'expiration et du statut
        for v in ventes_brutes:
            v["heure"]         = v["heure_dt"].strftime("%H:%M")
            v["expiration_dt"] = v["heure_dt"] + timedelta(minutes=v["profil_duree_min"])
            v["actif"]         = v["expiration_dt"] > now

        # Plus récentes en tête
        return sorted(ventes_brutes, key=lambda v: v["heure_dt"], reverse=True)

    def enregistrer_vente(self, ticket: dict, user_id: int) -> bool:
        """Persiste le ticket et la vente en base.

        TODO:
          1. ticket_repo.create_ticket(Ticket(code=ticket['code'], password=ticket['password'],
                                              profile_id=ticket['profile_id']))
          2. sale_repo.create_sale(Sale(ticket_id=..., user_id=user_id,
                                        montant=ticket['prix'],
                                        date_vente=datetime.now(),
                                        methode_paiement=ticket['methode']))
        """
        return True

    def total_du_jour(self) -> dict:
        """Calcule les agrégats du jour.

        TODO: sale_repository.agreger_par_date(datetime.today().date().isoformat())
        """
        ventes = self.obtenir_ventes_du_jour()
        return {
            "nb_ventes": len(ventes),
            "ca_total":  sum(v["montant"] for v in ventes),
            "nb_actifs": sum(1 for v in ventes if v["actif"]),
        }
