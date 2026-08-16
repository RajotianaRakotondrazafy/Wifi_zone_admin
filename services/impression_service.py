import os
from datetime import datetime
from pathlib import Path

from config import settings
from utils.formatage import formater_montant


def generer_html_ticket(data: dict) -> str:
    methodes = {"especes": "Espèces", "mobile_money": "Mobile Money", "carte": "Carte"}
    methode_label = methodes.get(data.get("methode", ""), data.get("methode", ""))

    duree_min = data.get("duree_min", 0)
    if duree_min == 0:
        duree_label = "Session libre"
    elif duree_min >= 1440:
        duree_label = f"{duree_min // 1440} jour(s)"
    elif duree_min >= 60:
        h = duree_min // 60
        m = duree_min % 60
        duree_label = f"{h}h{f' {m}min' if m else ''}"
    else:
        duree_label = f"{duree_min} min"

    date  = data.get("date",  datetime.now().strftime("%d/%m/%Y"))
    heure = data.get("heure", datetime.now().strftime("%H:%M"))

    qr_html = ""
    qr_chemin = data.get("qr_chemin")
    if qr_chemin and os.path.exists(qr_chemin):
        qr_html = f"""
        <div style="text-align:center;margin:6px 0 8px;">
          <img src="{Path(qr_chemin).as_uri()}" width="130" height="130"
               style="border:1px solid #ddd;border-radius:6px;padding:4px;" />
          <div style="font-size:8px;color:#999;margin-top:3px;">Scannez pour vous connecter au WiFi</div>
        </div>
        """

    return f"""
    <html><body style="margin:0;padding:0;font-family:Arial,sans-serif;">
    <div style="width:100%;padding:6px 8px;box-sizing:border-box;">

      <!-- En-tête -->
      <div style="text-align:center;border-bottom:2px solid #222;padding-bottom:6px;margin-bottom:8px;">
        <div style="font-size:15px;font-weight:bold;color:#1a1a2e;letter-spacing:1px;">E-Konnekta</div>
        <div style="font-size:9px;color:#666;margin-top:1px;">WiFi Hotspot</div>
      </div>

      <!-- Code + mot de passe -->
      <div style="background:#f4f4f8;border-radius:4px;padding:8px 6px;margin-bottom:8px;text-align:center;">
        <div style="font-size:8px;color:#999;text-transform:uppercase;letter-spacing:1px;margin-bottom:2px;">Identifiant</div>
        <div style="font-size:18px;font-weight:bold;font-family:monospace;letter-spacing:3px;color:#1a1a2e;">{data.get('code','')}</div>
        <div style="font-size:8px;color:#999;text-transform:uppercase;letter-spacing:1px;margin:5px 0 2px;">Mot de passe</div>
        <div style="font-size:18px;font-weight:bold;font-family:monospace;letter-spacing:3px;color:#4a57c8;">{data.get('password','')}</div>
      </div>

      <!-- Détails -->
      <table style="width:100%;font-size:10px;border-collapse:collapse;margin-bottom:6px;">
        <tr>
          <td style="padding:2px 0;color:#666;">Forfait</td>
          <td style="text-align:right;font-weight:bold;">{data.get('profil','')}</td>
        </tr>
        <tr>
          <td style="padding:2px 0;color:#666;">Durée</td>
          <td style="text-align:right;font-weight:bold;">{duree_label}</td>
        </tr>
        <tr>
          <td style="padding:2px 0;color:#666;">Montant</td>
          <td style="text-align:right;font-weight:bold;">{formater_montant(data.get('montant', 0))} Ar</td>
        </tr>
        <tr>
          <td style="padding:2px 0;color:#666;">Paiement</td>
          <td style="text-align:right;font-weight:bold;">{methode_label}</td>
        </tr>
      </table>

      {qr_html}

      <!-- Connexion -->
      <div style="border-top:1px dashed #ccc;padding-top:6px;margin-bottom:6px;text-align:center;font-size:9px;color:#555;">
        <div style="margin-bottom:1px;">Portail : <b>{settings.HOTSPOT_LOGIN_IP}</b></div>
        <div>Réseau : <b>{data.get('ssid','WiFi Zone')}</b></div>
      </div>

      <!-- Pied -->
      <div style="text-align:center;font-size:8px;color:#aaa;border-top:1px solid #eee;padding-top:4px;">
        {date} à {heure}
      </div>

    </div>
    </body></html>
    """


def imprimer_ticket(data: dict, parent=None) -> bool:
    """Ouvre le dialog d'impression système et imprime le ticket."""
    try:
        from PyQt6.QtPrintSupport import QPrinter, QPrintDialog
        from PyQt6.QtGui import QTextDocument, QPageSize, QPageLayout
        from PyQt6.QtCore import QSizeF, QMarginsF
    except ImportError:
        return False

    # QR code : fichier temporaire embarqué dans le HTML, supprimé après impression
    chemin_qr = None
    if data.get("qr"):
        try:
            from services.qr_service import generer_png_fichier
            chemin_qr = generer_png_fichier(data["qr"])
            data = {**data, "qr_chemin": chemin_qr}
        except Exception:
            chemin_qr = None

    printer = QPrinter(QPrinter.PrinterMode.HighResolution)

    # Format reçu thermique 80mm × 200mm, marges 3mm
    page_size = QPageSize(QSizeF(80, 200), QPageSize.Unit.Millimeter, "Recu thermique")
    layout = QPageLayout(
        page_size,
        QPageLayout.Orientation.Portrait,
        QMarginsF(3, 3, 3, 3),
        QPageLayout.Unit.Millimeter,
    )
    printer.setPageLayout(layout)

    dialog = QPrintDialog(printer, parent)
    dialog.setWindowTitle("Imprimer le ticket")
    if dialog.exec() != QPrintDialog.DialogCode.Accepted:
        _supprimer_qr(chemin_qr)
        return False

    try:
        doc = QTextDocument()
        doc.setPageSize(printer.pageRect(QPrinter.Unit.Point).size())
        doc.setHtml(generer_html_ticket(data))
        doc.print(printer)
        return True
    finally:
        _supprimer_qr(chemin_qr)


def _supprimer_qr(chemin: str | None):
    if not chemin:
        return
    try:
        os.remove(chemin)
    except OSError:
        pass
