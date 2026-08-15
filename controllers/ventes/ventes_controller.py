import csv
import logging
import os
from datetime import datetime, timedelta

from models.ticket import Ticket
from repositories.session_repository import SessionRepository

logger = logging.getLogger(__name__)
from models.sale import Sale
from models.hotspot_profile import HotspotProfile
from repositories.hotspot_profile_repository import HotspotProfileRepository
from repositories.ticket_repository import TicketRepository
from repositories.sale_repository import SaleRepository
from repositories.router_repository import RouterRepository
from repositories.parametres_repository import ParametresRepository
from services.mikrotik_service import MikroTikErreur, MikroTikService

from config.settings import (
    TARIFICATION_DEBIT_DEFAUT_MBPS,
    TARIFICATION_LIBRE_MIN_AR,
    TARIFICATION_LIBRE_MIN_MIN,
    TARIFICATION_PRIX_PAR_HEURE,
)
from services.qr_service import url_connexion_hotspot


class VentesController:
    def __init__(self):
        self._profile_repo = HotspotProfileRepository()
        self._ticket_repo = TicketRepository()
        self._sale_repo = SaleRepository()
        self._session_repo = SessionRepository()
        self._router_repo = RouterRepository()
        self._parametres_repo = ParametresRepository()

    def obtenir_profils(self, router_id: int | None = None) -> list[dict]:
        if router_id is not None:
            profils = self._profile_repo.lister_par_router(
                router_id, actif_seulement=True, exclure_internes=True
            )
        else:
            profils = self._profile_repo.lister_tous(
                actif_seulement=True, exclure_internes=True
            )
        return [profil.to_dict() for profil in profils]

    def obtenir_ventes_du_jour(self, date: str | None = None) -> list[dict]:
        date = date or datetime.now().date().isoformat()
        ventes_brutes = self._sale_repo.get_ventes_du_jour(date)
        return [self._construire_vente(v) for v in ventes_brutes]

    def obtenir_ventes_actives(self) -> list[dict]:
        """Tous les tickets encore actifs, quel que soit le jour de vente."""
        ventes_brutes = self._sale_repo.get_ventes_actives()
        return [self._construire_vente(v) for v in ventes_brutes]

    @staticmethod
    def _construire_vente(v: dict) -> dict:
        """Transforme une ligne de vente brute en dict prêt pour l'UI."""
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
            return {
                "vente_id":              v.get("vente_id"),
                "annule":                bool(v.get("annule", 0)),
                "heure_dt":              heure_dt,
                "heure":                 heure_dt.strftime("%H:%M"),
                "profil":                v["profil_nom"],
                "profil_duree_min":      0,
                "code":                  v["code"],
                "methode":               v["methode_paiement"],
                "montant":               v["montant"],
                "demarre":               demarre,
                "premiere_connexion_dt": premiere,
                "expiration_dt":         None,
                "actif":                 not est_cloturee,
                "libre":                 not est_cloturee,
            }

        expiration_dt = premiere + timedelta(minutes=duree_min) if demarre else None
        return {
            "vente_id":              v.get("vente_id"),
            "annule":                bool(v.get("annule", 0)),
            "heure_dt":              heure_dt,
            "heure":                 heure_dt.strftime("%H:%M"),
            "profil":                v["profil_nom"],
            "profil_duree_min":      duree_min,
            "code":                  v["code"],
            "methode":               v["methode_paiement"],
            "montant":               v["montant"],
            "demarre":               demarre,
            "premiere_connexion_dt": premiere,
            "expiration_dt":         expiration_dt,
            "actif":                 not demarre or (expiration_dt is not None and expiration_dt > datetime.now()),
            "libre":                 False,
        }

    def calculer_cout_libre(self, uptime_sec: float) -> int:
        """Calcule le coût d'une session libre selon la durée effective (tarifs en DB)."""
        min_ar  = self._parametres_repo.get_int("tarif_libre_min_ar",   TARIFICATION_LIBRE_MIN_AR)
        min_min = self._parametres_repo.get_int("tarif_libre_min_min",  TARIFICATION_LIBRE_MIN_MIN)
        par_h   = self._parametres_repo.get_int("tarif_prix_par_heure", TARIFICATION_PRIX_PAR_HEURE)
        minutes = uptime_sec / 60
        if minutes < min_min:
            return min_ar
        return round((minutes / 60) * par_h)

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

    def annuler_vente(self, vente_id: int) -> dict:
        """Annule une vente : retrait du hotspot + clôture des sessions + soft delete.

        Le nettoyage routeur est fait au mieux ; s'il échoue, la vente est tout de
        même annulée en local et le message signale l'action manuelle à faire.
        """
        try:
            info = self._sale_repo.obtenir_vente_par_id(vente_id)
            if info is None:
                return {"ok": False, "message": "Vente introuvable."}
            if info["annule"]:
                return {"ok": True, "message": "Cette vente est déjà annulée."}

            routeur_ok = True
            message_routeur = None
            routeur = self._router_repo.obtenir_par_id(info["router_id"])
            if routeur and routeur.adresse_ip and routeur.username and routeur.password_chiffre:
                svc = MikroTikService()
                try:
                    if svc.connecter_routeur(
                        routeur.adresse_ip, routeur.username,
                        routeur.password_chiffre, routeur.port_api or 8728,
                    ):
                        svc.deconnecter_par_username(info["code"])
                        svc.supprimer_utilisateur_hotspot(info["code"])
                        logger.info("annuler_vente(%s) : hotspot %s supprimé.", vente_id, info["code"])
                    else:
                        routeur_ok = False
                        message_routeur = (
                            f"Routeur « {routeur.nom} » injoignable : l'utilisateur "
                            f"hotspot {info['code']} devra être supprimé manuellement."
                        )
                except Exception as exc:
                    routeur_ok = False
                    message_routeur = f"Échec de la suppression sur le routeur : {exc}"
                finally:
                    svc.deconnecter()

            self._sale_repo.marquer_annulee(vente_id)
            self._session_repo.fermer_par_ticket(info["ticket_id"])

            if routeur_ok:
                return {"ok": True, "message": "Ticket annulé (retiré du hotspot)."}
            return {"ok": True, "message": f"Ticket annulé en local. {message_routeur}"}
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
            # Cherche un profil interne existant correspondant (inclut les internes)
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
            interne=True,
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

    def obtenir_details_impression(self, code: str) -> dict | None:
        """Retourne les données nécessaires à l'impression d'un ticket historique."""
        row = self._sale_repo.get_vente_par_code(code)
        if row is None:
            return None
        date_vente = row["date_vente"]
        if isinstance(date_vente, str):
            from datetime import datetime as _dt
            date_vente = _dt.fromisoformat(date_vente)
        return {
            "code":     code,
            "password": row["password"],
            "profil":   row["profil_nom"],
            "duree_min": row["duree_session_max"],
            "montant":  row["montant"],
            "methode":  row["methode_paiement"],
            "date":     date_vente.strftime("%d/%m/%Y"),
            "heure":    date_vente.strftime("%H:%M"),
            "qr":       url_connexion_hotspot(code, row["password"]),
        }

    def exporter_ventes_csv(self, chemin: str, date: str, ventes: list[dict]) -> int:
        os.makedirs(os.path.dirname(chemin), exist_ok=True) if os.path.dirname(chemin) else None
        entetes = ["Date", "Heure", "Code", "Profil", "Méthode", "Montant (Ar)", "Statut"]
        methodes = {"especes": "Espèces", "mobile_money": "Mobile Money", "carte": "Carte"}
        with open(chemin, "w", newline="", encoding="utf-8-sig") as f:
            writer = csv.writer(f, delimiter=";")
            writer.writerow(entetes)
            for v in ventes:
                writer.writerow([
                    date,
                    v.get("heure", ""),
                    v.get("code", ""),
                    v.get("profil", ""),
                    methodes.get(v.get("methode", ""), v.get("methode", "")),
                    int(v.get("montant", 0)),
                    "Actif" if v.get("actif") else "Expiré",
                ])
        return len(ventes)

    def total_du_jour(self, date: str | None = None) -> dict:
        date = date or datetime.now().date().isoformat()
        totaux = self._sale_repo.agreger_par_date(date)
        if date == datetime.now().date().isoformat():
            # Pour aujourd'hui, nb_actifs = tous les tickets actifs (multi-jours)
            totaux["nb_actifs"] = len([v for v in self.obtenir_ventes_actives() if v["actif"]])
        return totaux
