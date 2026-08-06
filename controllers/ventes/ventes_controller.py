import logging
from datetime import datetime, timedelta

from models.ticket import Ticket

logger = logging.getLogger(__name__)
from models.sale import Sale
from models.hotspot_profile import HotspotProfile
from repositories.hotspot_profile_repository import HotspotProfileRepository
from repositories.ticket_repository import TicketRepository
from repositories.sale_repository import SaleRepository
from repositories.router_repository import RouterRepository
from services.mikrotik_service import MikroTikErreur, MikroTikService

from config.settings import (
    TARIFICATION_DEBIT_DEFAUT_MBPS,
    TARIFICATION_LIBRE_MIN_AR,
    TARIFICATION_LIBRE_MIN_MIN,
    TARIFICATION_PRIX_PAR_HEURE,
)


class VentesController:
    def __init__(self):
        self._profile_repo = HotspotProfileRepository()
        self._ticket_repo = TicketRepository()
        self._sale_repo = SaleRepository()
        self._router_repo = RouterRepository()

    def obtenir_profils(self, router_id: int | None = None) -> list[dict]:
        if router_id is not None:
            profils = self._profile_repo.lister_par_router(router_id, actif_seulement=True)
        else:
            profils = self._profile_repo.lister_tous(actif_seulement=True)

        return [profil.to_dict() for profil in profils]

    def obtenir_ventes_du_jour(self) -> list[dict]:
        now = datetime.now()
        ventes_brutes = self._sale_repo.get_ventes_du_jour(now.date().isoformat())

        ventes = []
        for v in ventes_brutes:
            heure_dt = v["date_vente"]
            if isinstance(heure_dt, str):
                heure_dt = datetime.fromisoformat(heure_dt)
            duree_min = v["duree_session_max"]

            premiere = v.get("date_premiere_connexion")
            if isinstance(premiere, str):
                premiere = datetime.fromisoformat(premiere)
            demarre = premiere is not None

            if duree_min == 0:
                # Session libre : active jusqu'à clôture (statut 'epuise')
                est_cloturee = v.get("statut") in ("epuise", "expire")
                ventes.append({
                    "heure_dt":             heure_dt,
                    "heure":                heure_dt.strftime("%H:%M"),
                    "profil":               v["profil_nom"],
                    "profil_duree_min":     0,
                    "code":                 v["code"],
                    "methode":              v["methode_paiement"],
                    "montant":              v["montant"],
                    "demarre":              demarre,
                    "premiere_connexion_dt": premiere,
                    "expiration_dt":        None,
                    "actif":                not est_cloturee,
                    "libre":                not est_cloturee,
                })
            else:
                expiration_dt = premiere + timedelta(minutes=duree_min) if demarre else None
                ventes.append({
                    "heure_dt":             heure_dt,
                    "heure":                heure_dt.strftime("%H:%M"),
                    "profil":               v["profil_nom"],
                    "profil_duree_min":     duree_min,
                    "code":                 v["code"],
                    "methode":              v["methode_paiement"],
                    "montant":              v["montant"],
                    "demarre":              demarre,
                    "premiere_connexion_dt": premiere,
                    "expiration_dt":        expiration_dt,
                    "actif":                not demarre or (expiration_dt is not None and expiration_dt > now),
                    "libre":                False,
                })

        return ventes

    @staticmethod
    def calculer_cout_libre(uptime_sec: float) -> int:
        """Calcule le coût d'une session libre selon la durée effective."""
        minutes = uptime_sec / 60
        if minutes < TARIFICATION_LIBRE_MIN_MIN:
            return TARIFICATION_LIBRE_MIN_AR
        return round((minutes / 60) * TARIFICATION_PRIX_PAR_HEURE)

    def cloture_session_libre(
        self,
        code: str,
        uptime_sec: float,
        montant: int,
        methode: str,
    ) -> dict:
        try:
            # Mise à jour du montant + statut en DB
            ticket = self._ticket_repo.get_ticket_by_code(code)
            if ticket:
                self._sale_repo.update_montant(ticket.id, montant)
                self._ticket_repo.marquer_cloture(ticket.id)

            # Déconnexion MikroTik
            try:
                router_id = self._router_id_par_defaut()
            except RuntimeError:
                return {"ok": True, "message": "Montant enregistré (routeur non disponible)."}

            routeur = self._router_repo.obtenir_par_id(router_id)
            if not (routeur and routeur.adresse_ip and routeur.username and routeur.password_chiffre):
                return {"ok": True, "message": "Montant enregistré (routeur non configuré)."}

            svc = MikroTikService()
            try:
                connecte = svc.connecter_routeur(
                    routeur.adresse_ip, routeur.username,
                    routeur.password_chiffre, routeur.port_api,
                )
                logger.info("cloture_session_libre(%s) : connexion routeur = %s", code, connecte)
                if connecte:
                    ok_deconnect = svc.deconnecter_par_username(code)
                    logger.info("cloture_session_libre(%s) : deconnexion = %s", code, ok_deconnect)
            finally:
                svc.deconnecter()

            return {"ok": True, "message": f"Session {code} clôturée — {montant} Ar."}
        except Exception as exc:
            return {"ok": False, "message": str(exc)}

    def detecter_premieres_connexions(self) -> dict:
        tickets = self._ticket_repo.lister_sans_premiere_connexion()
        if not tickets:
            return {"detectes": 0}

        par_routeur: dict[int, list[Ticket]] = {}
        for t in tickets:
            profil = self._profile_repo.obtenir_par_id(t.profile_id)
            if profil is None:
                continue
            par_routeur.setdefault(profil.router_id, []).append(t)

        detectes = 0
        for router_id, tickets_r in par_routeur.items():
            routeur = self._router_repo.obtenir_par_id(router_id)
            if not (routeur and routeur.adresse_ip and routeur.username and routeur.password_chiffre):
                continue

            svc = MikroTikService()
            try:
                if not svc.connecter_routeur(
                    routeur.adresse_ip, routeur.username, routeur.password_chiffre, routeur.port_api
                ):
                    continue
                connexions = svc.obtenir_connexions_actives_par_code()
            except Exception:
                continue
            finally:
                svc.deconnecter()

            for t in tickets_r:
                if t.code not in connexions:
                    continue
                connexion_dt = datetime.now() - timedelta(seconds=connexions[t.code])
                expiration_dt = connexion_dt + timedelta(hours=t.validite)
                if self._ticket_repo.marquer_premiere_connexion(t.id, connexion_dt, expiration_dt):
                    detectes += 1

        return {"detectes": detectes}

    def _router_id_par_defaut(self) -> int:
        """Routeur actif de préférence, sinon le premier routeur configuré."""
        routeurs = self._router_repo.lister_tous()
        for routeur in routeurs:
            if routeur.statut == "actif":
                return routeur.id
        if routeurs:
            return routeurs[0].id
        raise RuntimeError(
            "Aucun routeur configuré. Ajoutez d'abord une zone dans « Zones WiFi »."
        )

    def _trouver_ou_creer_profil(
        self,
        debit_max: int,
        router_id: int | None = None,
        nom: str | None = None,
        duree_session_max: int = 60,
        utilisateurs_max: int = 1,
    ) -> int:
        if router_id is None:
            router_id = self._router_id_par_defaut()

        if nom is not None:
            for p in self._profile_repo.lister_tous(actif_seulement=True):
                if (p.nom == nom
                        and p.debit_max == debit_max
                        and p.utilisateurs_max == utilisateurs_max):
                    return p.id

        nouveau = HotspotProfile(
            router_id=router_id,
            nom=nom or f"{debit_max // 1024} Mbps",
            debit_max=debit_max,
            duree_session_max=duree_session_max,
            validite=24,
            prix=0,
            utilisateurs_max=utilisateurs_max,
        )
        self._profile_repo.creer(nouveau)
        return nouveau.id

    def enregistrer_vente(self, ticket: dict, user_id: int) -> dict:
        try:
            profile_id = ticket.get("profil_id")
            if profile_id is None:
                profile_id = self._trouver_ou_creer_profil(
                    ticket["debit_max"],
                    nom=ticket.get("profil"),
                    duree_session_max=ticket["duree_session_max"],
                    utilisateurs_max=ticket.get("utilisateurs_max", 1),
                )

            nouveau_ticket = Ticket(
                code=ticket["code"],
                password=ticket["password"],
                profile_id=profile_id,
                duree_session_max=ticket["duree_session_max"],
                validite=ticket["validite"],
                date_generation=datetime.now(),
                nom_affichage=ticket.get("profil"),
            )
            self._ticket_repo.create_ticket(nouveau_ticket)

            vente = Sale(
                ticket_id=nouveau_ticket.id,
                user_id=user_id,
                montant=ticket["prix"],
                date_vente=datetime.now(),
                methode_paiement=ticket["methode"],
            )
            self._sale_repo.create_sale(vente)

            return {
                "ok": True,
                "erreur": None,
                "ticket_id": nouveau_ticket.id,
                "code": nouveau_ticket.code,
            }
        except Exception as exc:
            return {"ok": False, "erreur": str(exc), "ticket_id": None, "code": None}

    def synchroniser_ticket_mikrotik(self, ticket_id: int) -> dict:
        try:
            ticket = self._ticket_repo.obtenir_par_id(ticket_id)
            if ticket is None:
                return {"ok": False, "message": "Ticket introuvable."}

            profil = self._profile_repo.obtenir_par_id(ticket.profile_id)
            if profil is None:
                return {"ok": False, "message": "Profil introuvable."}

            routeur = self._router_repo.obtenir_par_id(profil.router_id)
            if routeur is None:
                return {
                    "ok": False,
                    "message": "Aucun routeur n'est configuré pour ce profil. Ajoutez une zone dans « Zones WiFi ».",
                }
            if not (routeur.adresse_ip and routeur.username and routeur.password_chiffre):
                return {
                    "ok": False,
                    "message": f"Identifiants incomplets pour le routeur « {routeur.nom} ». Complétez-les dans « Zones WiFi ».",
                }

            svc = MikroTikService()
            if not svc.connecter_routeur(
                routeur.adresse_ip, routeur.username, routeur.password_chiffre, routeur.port_api
            ):
                return {
                    "ok": False,
                    "message": f"Impossible de se connecter au routeur « {routeur.nom} » "
                               f"({routeur.adresse_ip}:{routeur.port_api}). "
                               "Vérifiez l'adresse et que IP → Services → api est activé.",
                }

            try:
                est_forfait = profil.utilisateurs_max > 1
                noms_profils = {p.get("name") for p in svc.lister_profils()}
                if profil.nom not in noms_profils:
                    svc.creer_profil(
                        profil.nom,
                        debit_max_kbps=profil.debit_max,
                        session_timeout_min=None if est_forfait else profil.duree_session_max,
                        shared_users=profil.utilisateurs_max,
                    )

                svc.ajouter_utilisateur_hotspot(
                    ticket.code,
                    ticket.password,
                    profil.nom,
                    # Pour les forfaits partagés, pas de limit-uptime (partage multi-appareils)
                    duree_min=0 if est_forfait else ticket.duree_session_max,
                )
                return {"ok": True, "message": f"Ticket {ticket.code} enregistré sur {routeur.nom}."}
            except MikroTikErreur as exc:
                return {"ok": False, "message": str(exc)}
            finally:
                svc.deconnecter()
        except Exception as exc:
            return {"ok": False, "message": f"Erreur inattendue : {exc}"}

    def obtenir_temps_restants_mikrotik(self) -> dict[str, int]:
        try:
            router_id = self._router_id_par_defaut()
        except RuntimeError:
            return {}

        routeur = self._router_repo.obtenir_par_id(router_id)
        if not (routeur and routeur.adresse_ip and routeur.username and routeur.password_chiffre):
            return {}

        svc = MikroTikService()
        try:
            if not svc.connecter_routeur(
                routeur.adresse_ip, routeur.username,
                routeur.password_chiffre, routeur.port_api,
            ):
                return {}
            return svc.obtenir_temps_restants_sessions()
        except Exception:
            return {}
        finally:
            svc.deconnecter()

    def total_du_jour(self) -> dict:
        return self._sale_repo.agreger_par_date(datetime.now().date().isoformat())
