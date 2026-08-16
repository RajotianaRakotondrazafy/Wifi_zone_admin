import time

from models.router import Router
from models.hotspot_profile import HotspotProfile
from repositories.router_repository import RouterRepository
from repositories.hotspot_profile_repository import HotspotProfileRepository
from services.mikrotik_service import MikroTikService

# Délai minimum entre deux tentatives de connexion échouées par zone
_BACKOFF = 15.0


class ZonesController:
    """Orchestration des zones WiFi (routeurs MikroTik) et de leurs profils."""

    def __init__(self):
        self._router_repo = RouterRepository()
        self._profile_repo = HotspotProfileRepository()
        self._mikrotik = MikroTikService()
        # Dernier état de connexion réel connu par zone : {router_id: bool}
        self._etats_connexion: dict[int, bool] = {}
        # Horodatages de dernier échec par zone : {router_id: monotonic_ts}
        self._echecs: dict[int, float] = {}

    # ── Vérification réelle de la connexion ─────────────────────────────────

    def verifier_connexions(self) -> dict[int, bool]:
        """Teste la connexion de chaque zone active (thread de fond).

        Respecte un délai d'attente (_BACKOFF) après un échec pour éviter de
        marteler les routeurs. Retourne {router_id: bool} des derniers états
        connus.
        """
        now = time.monotonic()
        for routeur in self._router_repo.lister_tous():
            if routeur.statut != "actif":
                self._etats_connexion.pop(routeur.id, None)
                continue

            if now - self._echecs.get(routeur.id, 0.0) < _BACKOFF:
                continue

            if not (routeur.adresse_ip and routeur.username and routeur.password_chiffre):
                self._etats_connexion[routeur.id] = False
                self._echecs[routeur.id] = now
                continue

            try:
                ok = self._mikrotik.connecter_routeur(
                    routeur.adresse_ip,
                    routeur.username,
                    routeur.password_chiffre,
                    routeur.port_api or 8728,
                )
            except Exception:
                ok = False
            finally:
                try:
                    self._mikrotik.deconnecter()
                except Exception:
                    pass

            self._etats_connexion[routeur.id] = ok
            if not ok:
                self._echecs[routeur.id] = now

        return dict(self._etats_connexion)

    # ── Lecture ────────────────────────────────────────────────────────────

    def obtenir_zones(self) -> list[dict]:
        """Retourne les zones WiFi depuis la base de données avec l'état de
        connexion réel (déterminé par `verifier_connexions`)."""
        zones = []
        for routeur in self._router_repo.lister_tous():
            profils = self._profile_repo.lister_par_router(routeur.id, exclure_internes=True)
            zones.append({
                "id":                  routeur.id,
                "nom":                 routeur.nom,
                "username":            routeur.username,
                "adresse_ip":          routeur.adresse_ip,
                "port_api":            routeur.port_api,
                "statut":              routeur.statut,
                "connecte":            self._etats_connexion.get(routeur.id, False),
                "connexion_inconnue":  routeur.id not in self._etats_connexion,
                "nb_profils":          len(profils),
                "modele":              "MikroTik RouterOS",
                "appareils":           0,
                "max_appareils":       20,
            })
        return zones

    def obtenir_routers(self) -> list[dict]:
        """Liste simple des routeurs (id + nom) pour les combos."""
        return [{"id": r.id, "nom": r.nom} for r in self._router_repo.lister_tous()]

    def obtenir_mot_de_passe(self, router_id: int) -> str:
        """Retourne le mot de passe déchiffré d'un routeur (pré-remplissage)."""
        routeur = self._router_repo.obtenir_par_id(router_id)
        return routeur.password_chiffre if routeur else ""

    # ── Profils ──────────────────────────────────────────────────────────

    def obtenir_profils(self, router_id: int) -> list[dict]:
        """Tous les profils manuels (actifs et inactifs) pour la gestion — exclut les internes."""
        profils = self._profile_repo.lister_par_router(router_id, exclure_internes=True)
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
