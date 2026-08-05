from models.router import Router
from models.hotspot_profile import HotspotProfile
from repositories.router_repository import RouterRepository
from repositories.hotspot_profile_repository import HotspotProfileRepository


class ZonesController:
    """Orchestration des zones WiFi (routeurs MikroTik) et de leurs profils."""

    def __init__(self):
        self._router_repo = RouterRepository()
        self._profile_repo = HotspotProfileRepository()

    def obtenir_zones(self) -> list[dict]:
        """Retourne les zones WiFi depuis la base de données.

        TODO: Remplacer appareils/max_appareils par des appels réels à
              mikrotik_service.obtenir_statistiques(routeur) → appareils_connectes
        """
        zones = []
        for routeur in self._router_repo.lister_tous():
            profils = self._profile_repo.lister_par_router(routeur.id)
            zones.append({
                "id":             routeur.id,
                "nom":            routeur.nom,
                "username":       routeur.username,
                "adresse_ip":     routeur.adresse_ip,
                "port_api":       routeur.port_api,
                "statut":         routeur.statut,
                "connecte":       routeur.statut == "actif",
                "nb_profils":     len(profils),
                "modele":         "MikroTik RouterOS",
                "appareils":      0,
                "max_appareils":  20,
            })
        return zones

    def obtenir_routers(self) -> list[dict]:
        """Liste simple des routeurs (id + nom) pour les combos."""
        return [{"id": r.id, "nom": r.nom} for r in self._router_repo.lister_tous()]

    # ── Profils ──────────────────────────────────────────────────────────

    def obtenir_profils(self, router_id: int) -> list[dict]:
        """Tous les profils (actifs et inactifs) pour la gestion."""
        profils = self._profile_repo.lister_par_router(router_id)
        return [p.to_dict() for p in profils]

    def creer_profil(self, data: dict) -> None:
        profil = HotspotProfile(**{k: v for k, v in data.items() if k != "id"})
        self._profile_repo.creer(profil)

    def modifier_profil(self, data: dict) -> None:
        profil = HotspotProfile(**{k: v for k, v in data.items() if k != "id"})
        profil.id = data["id"]
        self._profile_repo.modifier(profil)

    def supprimer_profil(self, profile_id: int) -> None:
        self._profile_repo.supprimer(profile_id)

    def basculer_statut_profil(self, profile_id: int) -> str:
        return self._profile_repo.basculer_statut(profile_id)

    # ── Zones / routeurs ─────────────────────────────────────────────────

    def creer_zone(self, data: dict) -> None:
        routeur = Router(
            nom=data["nom"],
            adresse_ip=data["adresse_ip"],
            port_api=data["port_api"],
            username=data["username"],
            password_chiffre=data.get("password", ""),
            statut=data.get("statut", "inactif"),
        )
        self._router_repo.creer(routeur)

    def modifier_zone(self, data: dict) -> None:
        routeur = self._router_repo.obtenir_par_id(data["id"])
        if routeur is None:
            raise RuntimeError("Routeur introuvable.")

        routeur.nom = data["nom"]
        routeur.adresse_ip = data["adresse_ip"]
        routeur.port_api = data["port_api"]
        routeur.username = data["username"]
        routeur.statut = data.get("statut", routeur.statut)

        # Champ mot de passe laissé vide → on conserve l'existant
        if data.get("password"):
            routeur.password_chiffre = data["password"]

        self._router_repo.modifier(routeur)

    def supprimer_zone(self, router_id: int) -> None:
        # Supprime d'abord les profils liés (pas de ON DELETE CASCADE)
        for profil in self._profile_repo.lister_par_router(router_id):
            self._profile_repo.supprimer(profil.id)
        self._router_repo.supprimer(router_id)

    def basculer_connexion(self, router_id: int) -> bool:
        """Passe un routeur en 'actif' / 'inactif'. Retourne le nouvel état."""
        routeur = self._router_repo.obtenir_par_id(router_id)
        if routeur is None:
            raise RuntimeError("Routeur introuvable.")

        routeur.statut = "inactif" if routeur.statut == "actif" else "actif"
        self._router_repo.modifier(routeur)
        return routeur.statut == "actif"
