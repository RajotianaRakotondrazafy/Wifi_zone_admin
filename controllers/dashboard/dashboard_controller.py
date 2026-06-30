from typing import Any


class DashboardController:
    """Orchestration des données pour le tableau de bord."""

    def obtenir_donnees_dashboard(self) -> dict[str, Any]:
        """Retourne les statistiques réseau et les sessions actives.

        TODO: Remplacer les données factices ci-dessous par des appels réels à
              mikrotik_service (RouterOS API) et session_repository (SQLite).
              mikrotik_service.obtenir_statistiques() → statistiques
              session_repository.lister_sessions_actives() → sessions_actives
        """
        statistiques = {
            "appareils_connectes": 7,
            "appareils_max": 20,
            "debit_descendant": 148,   # Mb/s
            "debit_montant": 22,        # Mb/s
            "latence": 42,              # ms
        }

        sessions_actives = [
            {
                "nom_appareil": "Jean Dupont",
                "mac_address": "A4:C3:F0:12:33:BB",
                "type_appareil": "iPhone 14",
                "debit_actuel": 12,
                "est_connecte": True,
                "est_identifie": True,
            },
            {
                "nom_appareil": "Marie A.",
                "mac_address": "B8:27:EB:44:A1:02",
                "type_appareil": "MacBook Pro",
                "debit_actuel": 47,
                "est_connecte": True,
                "est_identifie": True,
            },
            {
                "nom_appareil": "Inconnu",
                "mac_address": "DC:A6:32:F5:88:21",
                "type_appareil": "Appareil inconnu",
                "debit_actuel": 3,
                "est_connecte": True,
                "est_identifie": False,
            },
            {
                "nom_appareil": "PC Bureau",
                "mac_address": "F0:18:98:AA:22:CC",
                "type_appareil": "Windows 11",
                "debit_actuel": 0,
                "est_connecte": False,
                "est_identifie": True,
            },
        ]

        return {
            "statistiques": statistiques,
            "sessions_actives": sessions_actives,
        }
