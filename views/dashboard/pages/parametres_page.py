import qtawesome as qta
from PyQt6.QtCore import QThread, Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFrame, QLineEdit, QScrollArea, QMessageBox, QFileDialog,
)

from controllers.parametres.parametres_controller import ParametresController
from scripts.restaurer_tickets_actifs import restaurer


class RestaurationTicketsActifsThread(QThread):
    """Restaure les comptes hotspot manquants hors du thread de l'interface."""

    terminee = pyqtSignal(object)

    def run(self):
        try:
            self.terminee.emit({"bilan": restaurer(appliquer=True)})
        except Exception as exc:
            self.terminee.emit({"erreur": str(exc)})


class ParametresPage(QWidget):
    def __init__(self, controller: ParametresController, parent=None):
        super().__init__(parent)
        self._controller = controller
        self._champs: dict[str, QLineEdit] = {}
        self._restauration_thread: RestaurationTicketsActifsThread | None = None
        self._construire_interface()
        self._charger_valeurs()

    # ── Construction ─────────────────────────────────────────────────────

    def _construire_interface(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(32, 28, 32, 28)
        layout.setSpacing(20)

        titre = QLabel("Paramètres")
        titre.setObjectName("titreDashboard")
        layout.addWidget(titre)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        contenu = QWidget()
        cl = QVBoxLayout(contenu)
        cl.setSpacing(16)
        cl.setContentsMargins(0, 0, 0, 0)

        cl.addWidget(self._section_tarification())
        cl.addWidget(self._section_application())
        cl.addWidget(self._section_sauvegarde())
        cl.addWidget(self._section_maintenance_mikrotik())

        # ── Bouton Sauvegarder ───────────────────────────────────────────
        btn = QPushButton("  Sauvegarder")
        btn.setObjectName("boutonSauvegarder")
        btn.setIcon(qta.icon("fa5s.save", color="#ffffff"))
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.setFixedHeight(46)
        btn.setFixedWidth(200)
        btn.clicked.connect(self._sauvegarder)
        cl.addWidget(btn, alignment=Qt.AlignmentFlag.AlignLeft)

        cl.addStretch()
        scroll.setWidget(contenu)
        layout.addWidget(scroll, stretch=1)

    def _section_tarification(self) -> QFrame:
        card = QFrame()
        card.setObjectName("sectionParametres")
        lay = QVBoxLayout(card)
        lay.setContentsMargins(20, 16, 20, 20)
        lay.setSpacing(14)

        lay.addWidget(self._entete("fa5s.tag", "TARIFICATION"))
        lay.addWidget(self._separateur())

        grille = QHBoxLayout()
        grille.setSpacing(16)

        col_g = QVBoxLayout()
        col_g.setSpacing(14)
        col_d = QVBoxLayout()
        col_d.setSpacing(14)

        champs = [
            ("tarif_prix_par_heure",    "Prix par heure (Ar)",              "1000", "col_g"),
            ("tarif_debit_defaut_mbps", "Débit par défaut (Mbps)",           "2",    "col_d"),
            ("tarif_libre_min_ar",      "Session libre — minimum facturable (Ar)",  "500",  "col_g"),
            ("tarif_libre_min_min",     "Session libre — durée minimum (min)",       "30",   "col_d"),
        ]

        for cle, label, placeholder, col in champs:
            bloc = QVBoxLayout()
            bloc.setSpacing(4)
            bloc.addWidget(self._label(label))
            champ = QLineEdit()
            champ.setFixedHeight(38)
            champ.setPlaceholderText(placeholder)
            bloc.addWidget(champ)
            self._champs[cle] = champ
            (col_g if col == "col_g" else col_d).addLayout(bloc)

        grille.addLayout(col_g)
        grille.addLayout(col_d)
        lay.addLayout(grille)

        lbl_aide = QLabel(
            "Le montant d'une session libre est calculé : durée (h) × prix/heure. "
            "En dessous de la durée minimum, le minimum facturable s'applique."
        )
        lbl_aide.setObjectName("descriptionZone")
        lbl_aide.setWordWrap(True)
        lay.addWidget(lbl_aide)

        return card

    def _section_application(self) -> QFrame:
        card = QFrame()
        card.setObjectName("sectionParametres")
        lay = QVBoxLayout(card)
        lay.setContentsMargins(20, 16, 20, 20)
        lay.setSpacing(14)

        lay.addWidget(self._entete("fa5s.sliders-h", "APPLICATION"))
        lay.addWidget(self._separateur())

        bloc = QVBoxLayout()
        bloc.setSpacing(4)
        bloc.addWidget(self._label("Intervalle de rafraîchissement des données (secondes)"))
        champ = QLineEdit()
        champ.setFixedHeight(38)
        champ.setFixedWidth(200)
        champ.setPlaceholderText("60")
        bloc.addWidget(champ)
        self._champs["app_refresh_interval_s"] = champ
        lay.addLayout(bloc)

        lbl_aide = QLabel("Fréquence de mise à jour des tickets et statistiques. Minimum : 10 s.")
        lbl_aide.setObjectName("descriptionZone")
        lay.addWidget(lbl_aide)

        return card

    def _section_sauvegarde(self) -> QFrame:
        card = QFrame()
        card.setObjectName("sectionParametres")
        lay = QVBoxLayout(card)
        lay.setContentsMargins(20, 16, 20, 20)
        lay.setSpacing(14)

        lay.addWidget(self._entete("fa5s.database", "SAUVEGARDE"))
        lay.addWidget(self._separateur())

        lbl_aide = QLabel(
            "Crée une copie de la base de données (tickets, ventes, utilisateurs, "
            "routeurs). Une sauvegarde automatique est effectuée toutes les 24h "
            "dans le dossier backups/ (7 fichiers conservés)."
        )
        lbl_aide.setObjectName("descriptionZone")
        lbl_aide.setWordWrap(True)
        lay.addWidget(lbl_aide)

        # Dernière sauvegarde automatique
        self._lbl_derniere_auto = QLabel(self._derniere_sauvegarde_auto())
        self._lbl_derniere_auto.setObjectName("descriptionZone")
        lay.addWidget(self._lbl_derniere_auto)

        ligne = QHBoxLayout()
        ligne.setSpacing(12)

        btn_backup = QPushButton("  Sauvegarder la base")
        btn_backup.setObjectName("boutonSauvegarder")
        btn_backup.setIcon(qta.icon("fa5s.download", color="#ffffff"))
        btn_backup.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_backup.setFixedHeight(40)
        btn_backup.clicked.connect(self._faire_backup)
        ligne.addWidget(btn_backup)

        self._lbl_derniere_sauvegarde = QLabel("Aucune sauvegarde effectuée.")
        self._lbl_derniere_sauvegarde.setObjectName("descriptionZone")
        ligne.addWidget(self._lbl_derniere_sauvegarde)
        ligne.addStretch()

        lay.addLayout(ligne)
        return card

    def _section_maintenance_mikrotik(self) -> QFrame:
        card = QFrame()
        card.setObjectName("sectionParametres")
        lay = QVBoxLayout(card)
        lay.setContentsMargins(20, 16, 20, 20)
        lay.setSpacing(14)

        lay.addWidget(self._entete("fa5s.broom", "MAINTENANCE MIKROTIK"))
        lay.addWidget(self._separateur())

        lbl_aide = QLabel(
            "Supprime du routeur les comptes hotspot dont le ticket est expiré ou "
            "inexistant en base de données (utilisateurs orphelins créés avant la "
            "mise à jour automatique)."
        )
        lbl_aide.setObjectName("descriptionZone")
        lbl_aide.setWordWrap(True)
        lay.addWidget(lbl_aide)

        lbl_restauration = QLabel(
            "Restaure les comptes des tickets actifs non expirés absents du routeur "
            "après un reset. Le login et le mot de passe seront le code du ticket."
        )
        lbl_restauration.setObjectName("descriptionZone")
        lbl_restauration.setWordWrap(True)
        lay.addWidget(lbl_restauration)

        ligne = QHBoxLayout()
        ligne.setSpacing(12)

        self._btn_purger = QPushButton("  Purger les utilisateurs orphelins")
        self._btn_purger.setObjectName("boutonSauvegarder")
        self._btn_purger.setIcon(qta.icon("fa5s.trash-alt", color="#ffffff"))
        self._btn_purger.setCursor(Qt.CursorShape.PointingHandCursor)
        self._btn_purger.setFixedHeight(40)
        self._btn_purger.clicked.connect(self._purger_orphelins)
        ligne.addWidget(self._btn_purger)

        self._btn_restaurer = QPushButton("  Restaurer les tickets actifs")
        self._btn_restaurer.setObjectName("boutonSauvegarder")
        self._btn_restaurer.setIcon(qta.icon("fa5s.redo", color="#ffffff"))
        self._btn_restaurer.setCursor(Qt.CursorShape.PointingHandCursor)
        self._btn_restaurer.setFixedHeight(40)
        self._btn_restaurer.clicked.connect(self._demander_restauration_tickets)
        ligne.addWidget(self._btn_restaurer)

        self._lbl_purge = QLabel("")
        self._lbl_purge.setObjectName("descriptionZone")
        ligne.addWidget(self._lbl_purge)
        ligne.addStretch()
        lay.addLayout(ligne)

        return card

    def _purger_orphelins(self):
        """Supprime du MikroTik tous les comptes sans ticket valide en DB."""
        from repositories.ticket_repository import TicketRepository
        from repositories.router_repository import RouterRepository
        from services.mikrotik_service import MikroTikService

        try:
            repo = TicketRepository()
            codes_valides    = repo.lister_codes_valides()
            codes_ekonnekta  = repo.lister_tous_les_codes()
            routers = RouterRepository().lister_tous()
        except Exception as exc:
            QMessageBox.critical(self, "Erreur", f"Lecture base de données :\n{exc}")
            return

        if not routers:
            QMessageBox.warning(self, "Aucun routeur", "Aucun routeur configuré.")
            return

        total_supprimes = 0
        erreurs = []

        for router in routers:
            svc = MikroTikService()
            if not svc.connecter_routeur(
                router.adresse_ip,
                router.username,
                router.password_chiffre,
                router.port_api or 8728,
            ):
                erreurs.append(f"Impossible de se connecter à {router.adresse_ip}")
                continue

            try:
                tous_users = svc.lister_utilisateurs_hotspot()
                # Uniquement les comptes créés par E-Konnekta ET dont le ticket
                # est expiré/épuisé — jamais les comptes manuels (admin, etc.)
                orphelins = [
                    u for u in tous_users
                    if u in codes_ekonnekta and u not in codes_valides
                ]
                for code in orphelins:
                    try:
                        svc.supprimer_utilisateur_hotspot(code)
                        total_supprimes += 1
                    except Exception as exc:
                        erreurs.append(f"{code} ({router.adresse_ip}) : {exc}")
            except Exception as exc:
                erreurs.append(f"Listing {router.adresse_ip} : {exc}")
            finally:
                svc.deconnecter()

        msg = f"{total_supprimes} utilisateur(s) orphelin(s) supprimé(s)."
        if erreurs:
            msg += f"\n\n{len(erreurs)} erreur(s) :\n" + "\n".join(erreurs[:5])
            QMessageBox.warning(self, "Purge terminée", msg)
        else:
            QMessageBox.information(self, "Purge terminée", msg)

        self._lbl_purge.setText(
            f"Dernière purge : {total_supprimes} supprimé(s)"
        )

    # ── Helpers UI ────────────────────────────────────────────────────────

    def _demander_restauration_tickets(self):
        """Demande confirmation puis restaure les comptes effaces du routeur."""
        if self._restauration_thread is not None and self._restauration_thread.isRunning():
            return

        reponse = QMessageBox.question(
            self,
            "Restaurer les tickets actifs",
            "Les comptes hotspot des tickets actifs non expirés qui sont absents du "
            "routeur vont être recréés.\n\n"
            "Le code du ticket sera utilisé comme identifiant et comme mot de passe. "
            "Les comptes déjà présents ne seront pas modifiés, et la date d'expiration "
            "des tickets est conservée.\n\n"
            "Lancer la restauration ?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if reponse != QMessageBox.StandardButton.Yes:
            return

        self._btn_purger.setEnabled(False)
        self._btn_restaurer.setEnabled(False)
        self._lbl_purge.setText("Restauration des tickets actifs en cours...")

        self._restauration_thread = RestaurationTicketsActifsThread(self)
        self._restauration_thread.terminee.connect(self._fin_restauration_tickets)
        self._restauration_thread.finished.connect(self._restauration_thread.deleteLater)
        self._restauration_thread.start()

    def _fin_restauration_tickets(self, resultat: object):
        self._btn_purger.setEnabled(True)
        self._btn_restaurer.setEnabled(True)
        self._restauration_thread = None

        if not isinstance(resultat, dict) or "erreur" in resultat:
            erreur = (
                resultat.get("erreur", "Erreur inconnue")
                if isinstance(resultat, dict)
                else "Erreur inconnue"
            )
            self._lbl_purge.setText("Restauration interrompue.")
            QMessageBox.critical(self, "Restauration impossible", str(erreur))
            return

        bilan = resultat["bilan"]
        self._lbl_purge.setText(f"Dernière restauration : {bilan.crees} compte(s) créé(s)")

        message = (
            f"{bilan.crees} compte(s) restauré(s).\n"
            f"{bilan.deja_presents} compte(s) déjà présent(s).\n"
            f"{bilan.actifs_non_expires} ticket(s) actif(s) non expiré(s) traité(s)."
        )
        details = bilan.ignores + bilan.erreurs
        if details:
            message += "\n\nDétails :\n" + "\n".join(details[:5])
            QMessageBox.warning(self, "Restauration terminée", message)
        else:
            QMessageBox.information(self, "Restauration terminée", message)

    def _entete(self, icone_id: str, titre: str) -> QWidget:
        w = QWidget()
        h = QHBoxLayout(w)
        h.setContentsMargins(0, 0, 0, 0)
        h.setSpacing(8)
        ico = QLabel()
        ico.setPixmap(qta.icon(icone_id, color="#5b6ee8").pixmap(14, 14))
        h.addWidget(ico)
        lbl = QLabel(titre)
        lbl.setObjectName("titreSectionParametres")
        h.addWidget(lbl)
        h.addStretch()
        return w

    def _separateur(self) -> QFrame:
        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setObjectName("separateurSession")
        return sep

    @staticmethod
    def _label(texte: str) -> QLabel:
        lbl = QLabel(texte)
        lbl.setObjectName("labelParametre")
        return lbl

    # ── Données ───────────────────────────────────────────────────────────

    @staticmethod
    def _derniere_sauvegarde_auto() -> str:
        import glob, os
        from config.settings import _chemin_donnees
        dossier = _chemin_donnees("backups")
        fichiers = sorted(glob.glob(os.path.join(dossier, "auto_*.db")))
        if not fichiers:
            return "Sauvegarde automatique : aucune encore effectuée."
        nom = os.path.basename(fichiers[-1])  # auto_20260808_103000.db
        try:
            ts = nom.replace("auto_", "").replace(".db", "")
            from datetime import datetime
            dt = datetime.strptime(ts, "%Y%m%d_%H%M%S")
            return f"Dernière sauvegarde auto : {dt.strftime('%d/%m/%Y à %H:%M')}"
        except ValueError:
            return f"Dernière sauvegarde auto : {nom}"

    def _faire_backup(self):
        from datetime import datetime
        nom_suggere = f"ekonnekta_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db"
        chemin, _ = QFileDialog.getSaveFileName(
            self,
            "Sauvegarder la base de données",
            nom_suggere,
            "Base SQLite (*.db);;Tous les fichiers (*)",
        )
        if not chemin:
            return
        try:
            chemin_final = self._controller.sauvegarder_base(chemin)
            self._lbl_derniere_sauvegarde.setText(
                f"Dernière sauvegarde : {datetime.now().strftime('%d/%m/%Y %H:%M')}"
            )
            QMessageBox.information(
                self, "Sauvegarde réussie",
                f"Base de données sauvegardée :\n{chemin_final}",
            )
        except Exception as exc:
            QMessageBox.critical(self, "Erreur", f"Échec de la sauvegarde :\n{exc}")

    def _charger_valeurs(self):
        valeurs = self._controller.charger()
        for cle, champ in self._champs.items():
            if cle in valeurs:
                champ.setText(str(valeurs[cle]))

    def _sauvegarder(self):
        donnees: dict[str, int] = {}
        erreurs: list[str] = []

        validations = {
            "tarif_prix_par_heure":    ("Prix par heure",          1,  999_999),
            "tarif_debit_defaut_mbps": ("Débit par défaut",        1,  1000),
            "tarif_libre_min_ar":      ("Minimum facturable",       0,  999_999),
            "tarif_libre_min_min":     ("Durée minimum",            0,  1440),
            "app_refresh_interval_s":  ("Intervalle rafraîchissement", 10, 3600),
        }

        for cle, (nom, mini, maxi) in validations.items():
            texte = self._champs[cle].text().strip()
            try:
                valeur = int(texte)
                if not (mini <= valeur <= maxi):
                    erreurs.append(f"• {nom} : doit être entre {mini} et {maxi}.")
                else:
                    donnees[cle] = valeur
            except ValueError:
                erreurs.append(f"• {nom} : valeur invalide « {texte} ».")

        if erreurs:
            QMessageBox.warning(
                self, "Valeurs invalides",
                "Corrigez les erreurs suivantes :\n\n" + "\n".join(erreurs),
            )
            return

        try:
            self._controller.sauvegarder(donnees)
            QMessageBox.information(
                self, "Paramètres sauvegardés",
                "Les paramètres ont été enregistrés avec succès.",
            )
        except Exception as exc:
            QMessageBox.critical(self, "Erreur", f"Impossible de sauvegarder :\n{exc}")
