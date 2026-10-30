"""Restaure sur MikroTik les tickets actifs absents apres un reset.

Par defaut, le script est en lecture seule et affiche les comptes qui seraient
crees. Ajouter ``--apply`` pour appliquer la restauration.

Usage::

    venv\\Scripts\\python scripts\\restaurer_tickets_actifs.py
    venv\\Scripts\\python scripts\\restaurer_tickets_actifs.py --apply

Seuls les tickets dont le statut est ``actif`` et dont l'expiration n'est pas
depassee sont consideres. Pour chaque compte recree, le mot de passe est le
code utilisateur lui-meme. La base est mise a jour avant sa recreation.
Un compte deja present sur le routeur est laisse tel quel : le script ne
l'ecrase jamais.
"""

from __future__ import annotations

import argparse
import sys
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path


# Le script peut etre lance depuis le dossier du projet ou depuis ailleurs.
RACINE_PROJET = Path(__file__).resolve().parent.parent
if str(RACINE_PROJET) not in sys.path:
    sys.path.insert(0, str(RACINE_PROJET))

from database.init_db import initialiser_base
from models.ticket import StatutTicket, Ticket
from repositories.hotspot_profile_repository import HotspotProfileRepository
from repositories.router_repository import RouterRepository
from repositories.ticket_repository import TicketRepository
from services.mikrotik_service import MikroTikErreur, MikroTikService


@dataclass
class Bilan:
    actifs_non_expires: int = 0
    deja_presents: int = 0
    a_creer: int = 0
    crees: int = 0
    ignores: list[str] = field(default_factory=list)
    erreurs: list[str] = field(default_factory=list)


def tickets_restaurables(tickets: list[Ticket], maintenant: datetime) -> list[Ticket]:
    """Retourne les tickets actifs dont la validite n'est pas terminee."""
    return [
        ticket
        for ticket in tickets
        if ticket.statut == StatutTicket.ACTIF
        and (ticket.date_expiration is None or ticket.date_expiration >= maintenant)
    ]


def decrire_echeance(ticket: Ticket, maintenant: datetime) -> str:
    """Rend visible l'echeance existante, sans jamais la modifier."""
    if ticket.date_expiration is None:
        return "aucune date d'expiration enregistree"

    restant = ticket.date_expiration - maintenant
    total_minutes = max(0, int(restant.total_seconds() // 60))
    jours, minutes = divmod(total_minutes, 24 * 60)
    heures, minutes = divmod(minutes, 60)
    return (
        f"expire le {ticket.date_expiration:%d/%m/%Y %H:%M} "
        f"(reste {jours} j {heures} h {minutes} min)"
    )


def restaurer(*, appliquer: bool) -> Bilan:
    """Liste ou recree les comptes hotspot manquants, routeur par routeur."""
    initialiser_base()

    ticket_repo = TicketRepository()
    profil_repo = HotspotProfileRepository()
    routeur_repo = RouterRepository()
    bilan = Bilan()

    maintenant = datetime.now()
    tickets = tickets_restaurables(ticket_repo.get_all_tickets(), maintenant)
    bilan.actifs_non_expires = len(tickets)
    if not tickets:
        return bilan

    # Un ticket est rattache a un routeur via son profil hotspot.
    par_routeur: dict[int, list[tuple[Ticket, object]]] = defaultdict(list)
    for ticket in tickets:
        profil = profil_repo.obtenir_par_id(ticket.profile_id)
        if profil is None:
            bilan.ignores.append(f"{ticket.code} : profil #{ticket.profile_id} introuvable")
            continue
        par_routeur[profil.router_id].append((ticket, profil))

    for routeur_id, tickets_routeur in par_routeur.items():
        routeur = routeur_repo.obtenir_par_id(routeur_id)
        if routeur is None:
            bilan.erreurs.append(f"Routeur #{routeur_id} introuvable")
            continue
        if not (routeur.adresse_ip and routeur.username and routeur.password_chiffre):
            bilan.erreurs.append(f"{routeur.nom} : identifiants MikroTik incomplets")
            continue

        service = MikroTikService()
        try:
            if not service.connecter_routeur(
                routeur.adresse_ip,
                routeur.username,
                routeur.password_chiffre,
                routeur.port_api or 8728,
            ):
                bilan.erreurs.append(
                    f"{routeur.nom} ({routeur.adresse_ip}) : connexion impossible"
                )
                continue

            utilisateurs_presents = set(service.lister_utilisateurs_hotspot())
            manquants = [
                (ticket, profil)
                for ticket, profil in tickets_routeur
                if ticket.code not in utilisateurs_presents
            ]
            deja_presents = len(tickets_routeur) - len(manquants)
            bilan.deja_presents += deja_presents
            bilan.a_creer += len(manquants)

            if not manquants:
                print(f"{routeur.nom} : tous les tickets actifs sont deja presents.")
                continue

            print(f"{routeur.nom} : {len(manquants)} ticket(s) manquant(s).")
            for ticket, _ in manquants:
                print(f"  - {ticket.code} : {decrire_echeance(ticket, maintenant)}")

            if not appliquer:
                continue

            profils_presents = {profil.get("name") for profil in service.lister_profils()}
            for ticket, profil in manquants:
                try:
                    if profil.nom not in profils_presents:
                        est_forfait = profil.utilisateurs_max > 1
                        service.creer_profil(
                            profil.nom,
                            debit_max_kbps=profil.debit_max,
                            session_timeout_min=(
                                None if est_forfait else profil.duree_session_max
                            ),
                            shared_users=profil.utilisateurs_max,
                        )
                        profils_presents.add(profil.nom)
                        print(f"  profil cree : {profil.nom}")

                    est_forfait = profil.utilisateurs_max > 1
                    # Maintenir l'impression, la DB et le routeur sur le meme mot de passe.
                    # Cette mise a jour precede l'appel MikroTik : si ce dernier echoue,
                    # une nouvelle execution pourra reprendre sans incoherence de mot de passe.
                    if ticket.password != ticket.code:
                        ticket.password = ticket.code
                        if not ticket_repo.update_ticket(ticket):
                            raise RuntimeError("mise a jour du mot de passe en base impossible")

                    service.ajouter_utilisateur_hotspot(
                        ticket.code,
                        # Apres le reset, le login et le mot de passe sont le code.
                        ticket.code,
                        profil.nom,
                        # Meme regle que la synchronisation normale des ventes.
                        duree_min=0 if est_forfait else ticket.duree_session_max,
                    )
                    bilan.crees += 1
                    print(f"  restaure : {ticket.code}")
                except Exception as exc:
                    bilan.erreurs.append(f"{routeur.nom} / {ticket.code} : {exc}")
        except MikroTikErreur as exc:
            bilan.erreurs.append(f"{routeur.nom} : {exc}")
        finally:
            service.deconnecter()

    return bilan


def afficher_bilan(bilan: Bilan, *, appliquer: bool) -> None:
    action = "crees" if appliquer else "a creer"
    total_action = bilan.crees if appliquer else bilan.a_creer
    print("\nBilan")
    print(f"  Tickets actifs non expires : {bilan.actifs_non_expires}")
    print(f"  Deja presents              : {bilan.deja_presents}")
    print(f"  Comptes {action:<19}: {total_action}")
    if bilan.ignores:
        print("  Ignores :")
        for message in bilan.ignores:
            print(f"    - {message}")
    if bilan.erreurs:
        print("  Erreurs :")
        for message in bilan.erreurs:
            print(f"    - {message}")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Restaure les tickets actifs absents des routeurs MikroTik."
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="cree effectivement les comptes manquants (sinon : apercu seulement)",
    )
    args = parser.parse_args()

    if not args.apply:
        print("Apercu uniquement : aucun compte ne sera cree. Utilisez --apply pour restaurer.")
    else:
        print("Les comptes recrees utiliseront leur code comme mot de passe.")

    bilan = restaurer(appliquer=args.apply)
    afficher_bilan(bilan, appliquer=args.apply)
    return 1 if bilan.erreurs else 0


if __name__ == "__main__":
    raise SystemExit(main())
