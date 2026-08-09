import qtawesome as qta
from PyQt6.QtCore import QPointF, QRectF, QSize, Qt, QTimer
from PyQt6.QtGui import QColor, QPainter
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFrame, QScrollArea, QMessageBox, QAbstractButton,
)

from controllers.zones.zones_controller import ZonesController
from services.mikrotik_worker import WorkerZones
from views.dashboard.components.dialog_profil import DialogProfil
from views.dashboard.components.dialog_zone import DialogZone


class ToggleSwitch(QAbstractButton):
    """Interrupteur à glissière utilisé pour filtrer les profils."""

    def __init__(self, coche: bool = False, parent=None):
        super().__init__(parent)
        self.setCheckable(True)
        self.setChecked(coche)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFixedSize(40, 22)

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setPen(Qt.PenStyle.NoPen)

        largeur, hauteur = self.width(), self.height()
        rayon = hauteur / 2
        p.setBrush(QColor("#4ade80") if self.isChecked() else QColor("#3a3a37"))
        p.drawRoundedRect(QRectF(0.5, 0.5, largeur - 1, hauteur - 1), rayon, rayon)

        p.setBrush(QColor("#ffffff") if self.isChecked() else QColor("#9a9da8"))
        r_knob = rayon - 3
        centre_x = largeur - rayon if self.isChecked() else rayon
        p.drawEllipse(QPointF(centre_x, hauteur / 2), r_knob, r_knob)

    def sizeHint(self) -> QSize:
        return QSize(40, 22)


class ProfilRow(QWidget):
    """Ligne représentant un profil hotspot dans le tableau."""

    def __init__(self, profil: dict, on_basculer_statut, on_modifier_profil=None, parent=None):
        super().__init__(parent)
        self._profil = profil
        actif = profil["statut"] == "actif"
        self.setObjectName("ligneProfilWifi")
        self.setProperty("inactif", not actif)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 8, 16, 8)
        layout.setSpacing(0)

        # Nom
        lbl_nom = QLabel(profil["nom"])
        lbl_nom.setObjectName("nomUtilisateur")
        lbl_nom.setFixedWidth(160)
        layout.addWidget(lbl_nom)

        # Débit
        debit = profil["debit_max"] // 1024
        lbl_debit = QLabel(f"{debit} Mbps")
        lbl_debit.setObjectName("loginUtilisateur")
        lbl_debit.setFixedWidth(80)
        layout.addWidget(lbl_debit)

        # Durée
        min_tot = profil["duree_session_max"]
        if min_tot >= 1440:
            duree = f"{min_tot // 1440}j"
        elif min_tot >= 60:
            duree = f"{min_tot // 60}h"
        else:
            duree = f"{min_tot} min"
        lbl_duree = QLabel(duree)
        lbl_duree.setObjectName("loginUtilisateur")
        lbl_duree.setFixedWidth(72)
        layout.addWidget(lbl_duree)

        # Validité
        val = profil["validite"]
        lbl_validite = QLabel(f"{val // 24}j" if val >= 24 else f"{val}h")
        lbl_validite.setObjectName("loginUtilisateur")
        lbl_validite.setFixedWidth(72)
        layout.addWidget(lbl_validite)

        # Prix
        lbl_prix = QLabel(f"{int(profil['prix'])} Ar")
        lbl_prix.setObjectName("montantVente")
        lbl_prix.setFixedWidth(96)
        layout.addWidget(lbl_prix)

        layout.addStretch()

        # Statut
        badge = QLabel("  Actif  " if actif else "  Inactif  ")
        badge.setObjectName("badgeProfilActif" if actif else "badgeProfilInactif")
        layout.addWidget(badge)
        layout.addSpacing(8)

        # Bouton modifier
        if on_modifier_profil is not None:
            btn_edit = QPushButton("Modifier")
            btn_edit.setObjectName("boutonActionLimiter")
            btn_edit.setFixedHeight(28)
            btn_edit.setFixedWidth(76)
            btn_edit.setCursor(Qt.CursorShape.PointingHandCursor)
            btn_edit.clicked.connect(lambda: on_modifier_profil(profil))
            layout.addWidget(btn_edit)
            layout.addSpacing(4)

        # Bouton bascule
        btn = QPushButton("Désactiver" if actif else "Activer")
        btn.setObjectName("boutonActionBloquer" if actif else "boutonActionActiver")
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.setFixedHeight(28)
        btn.setFixedWidth(92)
        btn.clicked.connect(lambda: on_basculer_statut(profil))
        layout.addWidget(btn)


class ZoneCard(QFrame):
    """Carte représentant une zone WiFi / routeur avec ses profils."""

    def __init__(self, donnees: dict, profils: list[dict],
                 on_configurer, on_basculer, on_supprimer_zone,
                 on_modifier_profil, on_basculer_statut, parent=None):
        super().__init__(parent)
        self._donnees = donnees
        self._profils = profils
        self._on_configurer = on_configurer
        self._on_basculer = on_basculer
        self._on_supprimer_zone = on_supprimer_zone
        self._on_modifier_profil = on_modifier_profil
        self._on_basculer_statut = on_basculer_statut
        self.setObjectName("zoneCard")
        self.setProperty("statut", self._statut_bordure())

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 18, 20, 18)
        layout.setSpacing(12)

        # ── En-tête ──────────────────────────────────────────────────
        header = QHBoxLayout()

        self._cercle = QLabel()
        self._cercle.setObjectName(self._style_cercle())
        self._cercle.setFixedSize(40, 40)
        self._cercle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._cercle.setPixmap(qta.icon("fa5s.wifi", color=self._couleur_etat()).pixmap(18, 18))
        header.addWidget(self._cercle)

        bloc_titre = QVBoxLayout()
        bloc_titre.setSpacing(2)
        nom = QLabel(donnees["nom"])
        nom.setObjectName("nomZone")
        bloc_titre.addWidget(nom)
        lieu = QLabel(f"Utilisateur : {donnees['username']}")
        lieu.setObjectName("descriptionZone")
        bloc_titre.addWidget(lieu)
        header.addLayout(bloc_titre)
        header.addStretch()

        self._badge = QLabel(self._libelle_badge())
        self._badge.setObjectName(self._style_badge())
        header.addWidget(self._badge)
        layout.addLayout(header)

        # ── Séparateur ───────────────────────────────────────────────
        layout.addWidget(self._sep())

        # ── Infos routeur ────────────────────────────────────────────
        infos = QHBoxLayout()
        infos.setSpacing(24)

        for etiquette, valeur in [
            ("Modèle",     donnees["modele"]),
            ("Adresse IP", donnees["adresse_ip"]),
            ("Port API",   str(donnees["port_api"])),
        ]:
            bloc = QVBoxLayout()
            bloc.setSpacing(3)
            lbl_et = QLabel(etiquette)
            lbl_et.setObjectName("descriptionZone")
            bloc.addWidget(lbl_et)
            lbl_val = QLabel(valeur)
            lbl_val.setObjectName("nomZone" if etiquette != "Adresse IP" else "ipZone")
            bloc.addWidget(lbl_val)
            infos.addLayout(bloc)

        infos.addStretch()
        layout.addLayout(infos)

        # ── Séparateur ───────────────────────────────────────────────
        layout.addWidget(self._sep())

        # ── Profils ──────────────────────────────────────────────────
        h_profils = QHBoxLayout()
        lbl_titre_profils = QLabel("Profils WiFi")
        lbl_titre_profils.setObjectName("titreSectionSessions")
        h_profils.addWidget(lbl_titre_profils)

        self._badge_nb = QLabel(f"  {len(self._profils)}  ")
        self._badge_nb.setObjectName("badgeNeutre")
        h_profils.addWidget(self._badge_nb)
        h_profils.addStretch()

        self._switch_actifs = ToggleSwitch()
        self._switch_actifs.setToolTip("Afficher uniquement les profils actifs")
        h_profils.addWidget(self._switch_actifs)

        lbl_filtre = QLabel("Actifs uniquement")
        lbl_filtre.setObjectName("descriptionZone")
        lbl_filtre.setFixedWidth(100)
        h_profils.addWidget(lbl_filtre)
        h_profils.addSpacing(8)

        btn_ajouter = QPushButton("  Ajouter")
        btn_ajouter.setObjectName("boutonActionLimiter")
        btn_ajouter.setIcon(qta.icon("fa5s.plus", color="#8b8d98"))
        btn_ajouter.setFixedHeight(30)
        btn_ajouter.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_ajouter.clicked.connect(lambda: on_modifier_profil(None, donnees["id"]))
        h_profils.addWidget(btn_ajouter)
        layout.addLayout(h_profils)
        layout.addSpacing(8)

        # Conteneur tableau des profils
        tableau = QFrame()
        tableau.setObjectName("tableauProfils")
        tableau_lay = QVBoxLayout(tableau)
        tableau_lay.setContentsMargins(0, 0, 0, 0)
        tableau_lay.setSpacing(0)

        self._lignes: list[tuple[bool, QWidget]] = []
        self._entete_widget = None

        self._lbl_aucun_actif = QLabel("Aucun profil actif.")
        self._lbl_aucun_actif.setObjectName("loginUtilisateur")
        self._lbl_aucun_actif.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._lbl_aucun_actif.setContentsMargins(0, 14, 0, 14)
        self._lbl_aucun_actif.hide()

        if self._profils:
            # En-tête colonnes
            entete = QWidget()
            entete_lay = QVBoxLayout(entete)
            entete_lay.setContentsMargins(0, 0, 0, 0)
            entete_lay.setSpacing(0)
            h_entete = QHBoxLayout()
            h_entete.setContentsMargins(16, 10, 16, 8)
            for texte, largeur in [("Nom", 160), ("Débit", 80), ("Durée", 72), ("Validité", 72), ("Prix", 96)]:
                lbl = QLabel(texte)
                lbl.setObjectName("titreSectionSessions")
                lbl.setFixedWidth(largeur)
                h_entete.addWidget(lbl)
            h_entete.addStretch()
            entete_lay.addLayout(h_entete)
            entete_lay.addWidget(self._sep())
            self._entete_widget = entete
            tableau_lay.addWidget(self._entete_widget)

            for i, profil in enumerate(self._profils):
                bloc = QWidget()
                bloc_lay = QVBoxLayout(bloc)
                bloc_lay.setContentsMargins(0, 0, 0, 0)
                bloc_lay.setSpacing(0)
                if i > 0:
                    bloc_lay.addWidget(self._sep())
                bloc_lay.addWidget(ProfilRow(
                    profil,
                    self._on_basculer_statut,
                    lambda p=profil: self._on_modifier_profil(p, donnees["id"]),
                ))
                tableau_lay.addWidget(bloc)
                self._lignes.append((profil["statut"] == "actif", bloc))
        else:
            lbl_vide = QLabel("Aucun profil configuré pour cette zone.")
            lbl_vide.setObjectName("loginUtilisateur")
            lbl_vide.setAlignment(Qt.AlignmentFlag.AlignCenter)
            lbl_vide.setContentsMargins(0, 14, 0, 14)
            tableau_lay.addWidget(lbl_vide)

        tableau_lay.addWidget(self._lbl_aucun_actif)

        layout.addWidget(tableau)

        # Filtre actif par défaut : seuls les profils actifs sont affichés
        self._switch_actifs.toggled.connect(self._appliquer_filtre_profils)
        self._switch_actifs.setChecked(True)

        # ── Boutons actions ──────────────────────────────────────────
        actions = QHBoxLayout()
        actions.setSpacing(8)
        actions.addStretch()

        btn_config = QPushButton("Configurer")
        btn_config.setObjectName("boutonActionLimiter")
        btn_config.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_config.setFixedHeight(32)
        btn_config.clicked.connect(lambda: on_configurer(donnees))
        actions.addWidget(btn_config)

        btn_action = QPushButton(
            "Déconnecter" if donnees["statut"] == "actif" else "Reconnecter"
        )
        btn_action.setObjectName(
            "boutonActionBloquer" if donnees["statut"] == "actif" else "boutonActionActiver"
        )
        btn_action.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_action.setFixedHeight(32)
        btn_action.clicked.connect(lambda: on_basculer(donnees))
        actions.addWidget(btn_action)

        btn_suppr = QPushButton("Supprimer")
        btn_suppr.setObjectName("boutonActionBloquer")
        btn_suppr.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_suppr.setFixedHeight(32)
        btn_suppr.clicked.connect(lambda: on_supprimer_zone(donnees))
        actions.addWidget(btn_suppr)

        layout.addLayout(actions)

    # ── État de la zone ────────────────────────────────────────────────

    def _etat(self) -> str:
        """État réel de la zone : connecte / deconnecte / inconnu / inactif."""
        if self._donnees["statut"] != "actif":
            return "inactif"
        if self._donnees.get("connexion_inconnue"):
            return "inconnu"
        return "connecte" if self._donnees["connecte"] else "deconnecte"

    def _couleur_etat(self) -> str:
        return {
            "connecte":   "#4ade80",
            "deconnecte": "#f87171",
            "inconnu":    "#e8c45b",
            "inactif":    "#9a9da8",
        }[self._etat()]

    def _libelle_badge(self) -> str:
        return {
            "connecte":   " Routeur connecté ",
            "deconnecte": " Routeur déconnecté ",
            "inconnu":    " Vérification… ",
            "inactif":    " Inactif ",
        }[self._etat()]

    def _style_badge(self) -> str:
        return {
            "connecte":   "badgeZoneActif",
            "deconnecte": "badgeZoneInactif",
            "inconnu":    "badgeZoneErreur",
            "inactif":    "badgeZoneInactif",
        }[self._etat()]

    def _style_cercle(self) -> str:
        return {
            "connecte":   "cercleIconeZoneActif",
            "deconnecte": "cercleIconeZoneInactif",
            "inconnu":    "cercleIconeZoneErreur",
            "inactif":    "cercleIconeZoneInactif",
        }[self._etat()]

    def _statut_bordure(self) -> str:
        """Valeur de la propriété `statut` de la carte (couleur de la bordure)."""
        return {
            "connecte":   "actif",
            "deconnecte": "inactif",
            "inconnu":    "erreur",
            "inactif":    "inactif",
        }[self._etat()]

    def mettre_a_jour_connexion(self, connecte: bool):
        """Met à jour l'affichage avec le dernier état de connexion réel."""
        self._donnees["connecte"] = connecte
        self._donnees["connexion_inconnue"] = False

        self._cercle.setPixmap(
            qta.icon("fa5s.wifi", color=self._couleur_etat()).pixmap(18, 18)
        )
        self._badge.setText(self._libelle_badge())

        for widget, cle in ((self._badge, self._style_badge()),
                            (self._cercle, self._style_cercle())):
            widget.setObjectName(cle)
            widget.style().unpolish(widget)
            widget.style().polish(widget)

        self.setProperty("statut", self._statut_bordure())
        self.style().unpolish(self)
        self.style().polish(self)

    @staticmethod
    def _sep() -> QFrame:
        f = QFrame()
        f.setFrameShape(QFrame.Shape.HLine)
        f.setObjectName("separateurSession")
        return f

    def _appliquer_filtre_profils(self, coche: bool):
        nb_visibles = 0
        for actif, widget in self._lignes:
            visible = not coche or actif
            widget.setVisible(visible)
            if visible:
                nb_visibles += 1
        self._badge_nb.setText(f"  {nb_visibles}  ")
        if self._entete_widget is not None:
            self._entete_widget.setVisible(nb_visibles > 0)
        self._lbl_aucun_actif.setVisible(bool(self._lignes) and coche and nb_visibles == 0)


class ZonesWifiPage(QWidget):
    """Page de gestion des zones WiFi / routeurs MikroTik."""

    def __init__(self, zones_controller: ZonesController, parent=None):
        super().__init__(parent)
        self._controller = zones_controller
        self._cartes: dict[int, ZoneCard] = {}
        self._worker: WorkerZones | None = None

        self._construire_interface()

        # Vérification périodique de l'état réel de chaque routeur
        self._timer = QTimer(self)
        self._timer.setInterval(15_000)
        self._timer.timeout.connect(self._lancer_verification)
        self._timer.start()
        self._lancer_verification()

    def _lancer_verification(self):
        if self._worker and self._worker.isRunning():
            return
        self._worker = WorkerZones(self._controller, parent=self)
        self._worker.connexions_prete.connect(self._mettre_a_jour_connexions)
        self._worker.start()

    def _mettre_a_jour_connexions(self, etats: dict):
        for router_id, connecte in etats.items():
            carte = self._cartes.get(router_id)
            if carte is not None:
                carte.mettre_a_jour_connexion(connecte)

    def _construire_interface(self):
        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(32, 28, 32, 28)
        self._layout.setSpacing(20)
        self._remplir()

    def _vider_layout(self):
        while self._layout.count():
            item = self._layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

    def _remplir(self):
        self._vider_layout()
        self._cartes.clear()

        # ── Header ──────────────────────────────────────────────────────
        header = QHBoxLayout()
        titre = QLabel("Zones WiFi")
        titre.setObjectName("titreDashboard")
        header.addWidget(titre)
        header.addStretch()

        btn = QPushButton("  Ajouter une zone")
        btn.setObjectName("boutonActionPage")
        btn.setIcon(qta.icon("fa5s.plus", color="#ffffff"))
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.setFixedHeight(38)
        btn.clicked.connect(self._ajouter_zone)
        header.addWidget(btn)
        self._layout.addLayout(header)

        # ── Cards zones ─────────────────────────────────────────────────
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        contenu = QWidget()
        contenu_layout = QVBoxLayout(contenu)
        contenu_layout.setSpacing(16)
        contenu_layout.setContentsMargins(0, 0, 0, 0)

        zones = self._controller.obtenir_zones()
        if not zones:
            lbl_vide = QLabel("Aucune zone WiFi configurée. Cliquez sur « Ajouter une zone ».")
            lbl_vide.setObjectName("loginUtilisateur")
            lbl_vide.setAlignment(Qt.AlignmentFlag.AlignCenter)
            lbl_vide.setContentsMargins(0, 40, 0, 40)
            contenu_layout.addWidget(lbl_vide)
        else:
            for zone in zones:
                profils = self._controller.obtenir_profils(zone["id"])
                carte = ZoneCard(
                    zone, profils,
                    self._configurer_zone,
                    self._basculer_connexion,
                    self._supprimer_zone,
                    self._ouvrir_dialog_profil,
                    self._basculer_statut_profil,
                )
                self._cartes[zone["id"]] = carte
                contenu_layout.addWidget(carte)

        contenu_layout.addStretch()
        scroll.setWidget(contenu)
        self._layout.addWidget(scroll, stretch=1)

    # ── Actions zones ────────────────────────────────────────────────────

    def _ajouter_zone(self):
        dialog = DialogZone(zone=None, parent=self)
        if dialog.exec():
            try:
                self._controller.creer_zone(dialog.donnees)
            except Exception as e:
                QMessageBox.critical(self, "Erreur", str(e))
                return
            self._remplir()

    def _configurer_zone(self, zone: dict):
        dialog = DialogZone(zone=zone, parent=self)
        if dialog.exec():
            try:
                self._controller.modifier_zone(dialog.donnees)
            except Exception as e:
                QMessageBox.critical(self, "Erreur", str(e))
                return
            self._remplir()

    def _basculer_connexion(self, zone: dict):
        try:
            self._controller.basculer_connexion(zone["id"])
        except Exception as e:
            QMessageBox.critical(self, "Erreur", str(e))
            return
        self._remplir()

    def _supprimer_zone(self, zone: dict):
        reply = QMessageBox.question(
            self, "Confirmer",
            f"Supprimer la zone « {zone['nom']} » et tous ses profils ?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            try:
                self._controller.supprimer_zone(zone["id"])
                self._remplir()
            except Exception as e:
                QMessageBox.critical(self, "Erreur", str(e))

    # ── Actions profils ──────────────────────────────────────────────────

    def _ouvrir_dialog_profil(self, profil: dict | None, router_id: int):
        routers = self._controller.obtenir_routers()

        dialog = DialogProfil(routers, profil=profil, parent=self)

        if profil:
            for i, r in enumerate(routers):
                if r["id"] == profil["router_id"]:
                    dialog._combo_router.setCurrentIndex(i)
                    break

        if dialog.exec():
            data = dialog.donnees
            if data is None:
                return
            try:
                if "id" in data:
                    self._controller.modifier_profil(data)
                else:
                    self._controller.creer_profil(data)
            except Exception as e:
                QMessageBox.critical(self, "Erreur", str(e))
                return

            self._remplir()

    def _basculer_statut_profil(self, profil: dict):
        try:
            self._controller.basculer_statut_profil(profil["id"])
        except Exception as e:
            QMessageBox.critical(self, "Erreur", str(e))
            return
        self._remplir()
