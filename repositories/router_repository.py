import logging
import sqlite3

from database.connection import DatabaseConnection
from models.router import Router
from services.crypto_service import CryptoService

logger = logging.getLogger(__name__)


class RouterRepository:

    def __init__(self):
        self._conn: sqlite3.Connection = DatabaseConnection.get_connection()
        self._crypto = CryptoService()

    # ── Chiffrement transparent ───────────────────────────────────────────

    def _chiffrer(self, mdp: str) -> str:
        if not mdp:
            return mdp
        return self._crypto.chiffrer(mdp)

    def _dechiffrer(self, valeur: str, router_id: int | None = None) -> str:
        """Déchiffre le mot de passe.

        Si la valeur est en clair (ancienne entrée sans chiffrement),
        la re-chiffre automatiquement en base pour assurer la migration.
        """
        if not valeur:
            return valeur
        if self._crypto.est_chiffre(valeur):
            try:
                return self._crypto.dechiffrer(valeur)
            except ValueError:
                return valeur

        # Valeur en clair détectée → migration silencieuse
        logger.info(
            "RouterRepository : migration du mot de passe en clair (router_id=%s)", router_id
        )
        try:
            chiffre = self._chiffrer(valeur)
            self._conn.execute(
                "UPDATE routers SET password_chiffre = ? WHERE id = ?",
                (chiffre, router_id),
            )
            self._conn.commit()
        except sqlite3.Error as exc:
            logger.warning("RouterRepository : échec de la migration du mot de passe : %s", exc)
        return valeur

    def _router_depuis_row(self, row: dict) -> Router:
        r = Router.from_dict(row)
        r.password_chiffre = self._dechiffrer(r.password_chiffre, r.id)
        return r

    # ── CRUD ─────────────────────────────────────────────────────────────

    def lister_tous(self) -> list[Router]:
        try:
            cursor = self._conn.cursor()
            cursor.execute("SELECT * FROM routers ORDER BY nom ASC")
            return [self._router_depuis_row(dict(row)) for row in cursor.fetchall()]
        except sqlite3.Error as e:
            raise RuntimeError(f"Erreur lors de la récupération des routeurs : {e}")

    def obtenir_par_id(self, router_id: int) -> Router | None:
        try:
            cursor = self._conn.cursor()
            cursor.execute("SELECT * FROM routers WHERE id = ?", (router_id,))
            row = cursor.fetchone()
            return self._router_depuis_row(dict(row)) if row else None
        except sqlite3.Error as e:
            raise RuntimeError(f"Erreur lors de la récupération du routeur : {e}")

    def creer(self, routeur: Router) -> Router:
        query = """
            INSERT INTO routers (nom, adresse_ip, port_api, username, password_chiffre, statut)
            VALUES (?, ?, ?, ?, ?, ?)
        """
        try:
            cursor = self._conn.cursor()
            cursor.execute(query, (
                routeur.nom, routeur.adresse_ip, routeur.port_api,
                routeur.username, self._chiffrer(routeur.password_chiffre), routeur.statut,
            ))
            self._conn.commit()
            routeur.id = cursor.lastrowid
            return routeur
        except sqlite3.Error as e:
            self._conn.rollback()
            raise RuntimeError(f"Erreur lors de la création du routeur : {e}")

    def modifier(self, routeur: Router) -> bool:
        if routeur.id is None:
            raise ValueError("Impossible de modifier un routeur sans id.")
        query = """
            UPDATE routers
            SET nom = ?, adresse_ip = ?, port_api = ?, username = ?, password_chiffre = ?, statut = ?
            WHERE id = ?
        """
        try:
            cursor = self._conn.cursor()
            cursor.execute(query, (
                routeur.nom, routeur.adresse_ip, routeur.port_api,
                routeur.username, self._chiffrer(routeur.password_chiffre), routeur.statut,
                routeur.id,
            ))
            self._conn.commit()
            return cursor.rowcount > 0
        except sqlite3.Error as e:
            self._conn.rollback()
            raise RuntimeError(f"Erreur lors de la modification du routeur : {e}")

    def supprimer(self, router_id: int) -> bool:
        try:
            cursor = self._conn.cursor()
            cursor.execute("DELETE FROM routers WHERE id = ?", (router_id,))
            self._conn.commit()
            return cursor.rowcount > 0
        except sqlite3.Error as e:
            self._conn.rollback()
            raise RuntimeError(f"Erreur lors de la suppression du routeur : {e}")
