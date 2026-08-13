"""Génération des QR codes de connexion WiFi (MikroTik hotspot)."""

import io
import os
import tempfile
import uuid
from urllib.parse import quote

import qrcode

from config import settings


def url_connexion_hotspot(code: str, password: str) -> str:
    """URL de connexion hotspot pré-remplie, encodée dans le QR code.

    La page de login par défaut de MikroTik lit les paramètres
    ``username`` et ``password`` de l'URL pour pré-remplir le formulaire :
    le client n'a plus qu'à valider une fois le QR scanné.
    """
    hote = getattr(settings, "HOTSPOT_LOGIN_IP", "192.168.88.1")
    return (
        f"http://{hote}/login"
        f"?username={quote(code)}&password={quote(password)}"
    )


def _generer_png(donnees: str) -> bytes:
    """Génère un QR code en PNG (bytes)."""
    qr = qrcode.QRCode(
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=10,
        border=2,
    )
    qr.add_data(donnees)
    qr.make(fit=True)
    image = qr.make_image(fill_color="black", back_color="white")
    buf = io.BytesIO()
    image.save(buf, format="PNG")
    return buf.getvalue()


def generer_pixmap(donnees: str, taille: int = 160):
    """Retourne un QPixmap du QR code (None en cas d'échec)."""
    try:
        from PyQt6.QtCore import QByteArray, Qt
        from PyQt6.QtGui import QPixmap
    except ImportError:
        return None
    try:
        pix = QPixmap()
        pix.loadFromData(QByteArray(_generer_png(donnees)))
        return pix.scaled(
            taille,
            taille,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
    except Exception:
        return None


def generer_png_fichier(donnees: str) -> str:
    """Écrit un QR PNG dans un fichier temporaire et retourne son chemin."""
    chemin = os.path.join(
        tempfile.gettempdir(), f"ekonnekta_qr_{uuid.uuid4().hex}.png"
    )
    with open(chemin, "wb") as f:
        f.write(_generer_png(donnees))
    return chemin
