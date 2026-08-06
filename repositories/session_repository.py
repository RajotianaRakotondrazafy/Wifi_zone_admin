import sqlite3
from datetime import datetime
from typing import Optional

from database.connection import DatabaseConnection
from models.session import Session


class SessionRepository:

    def __init__(self):
        self._conn: sqlite3.Connection = DatabaseConnection.get_connection()

    # ── Écriture ──────────────────────────────────────────────────────────

    def creer(self, session: Session) -> Session:
        query = """
            INSERT INTO sessions
                (ticket_id, mac_address, ip_assignee, date_debut, date_fin,
                 octets_envoyes, octets_recus, duree_reelle, nom_hote)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        try:
            cursor = self._conn.cursor()
            cursor.execute(query, (
                session.ticket_id,
                session.mac_address,
                session.ip_assignee,
                session.date_debut.isoformat() if session.date_debut else None,
                session.date_fin.isoformat() if session.date_fin else None,
                session.octets_envoyes,
                session.octets_recus,
                session.duree_reelle,
                session.nom_hote,
            ))
            self._conn.commit()
            session.id = cursor.lastrowid
            return session
        except sqlite3.Error as e:
            self._conn.rollback()
            raise RuntimeError(f"Erreur lors de la création de la session : {e}")

    def mettre_a_jour(self, session: Session) -> bool:
        if session.id is None:
            raise ValueError("Impossible de mettre à jour une session sans id.")
        query = """
            UPDATE sessions
            SET ip_assignee = ?, date_fin = ?, octets_envoyes = ?, octets_recus = ?,
                duree_reelle = ?, nom_hote = ?
            WHERE id = ?
        """
        try:
            cursor = self._conn.cursor()
            cursor.execute(query, (
                session.ip_assignee,
                session.date_fin.isoformat() if session.date_fin else None,
                session.octets_envoyes,
                session.octets_recus,
                session.duree_reelle,
                session.nom_hote,
                session.id,
            ))
            self._conn.commit()
            return cursor.rowcount > 0
        except sqlite3.Error as e:
            self._conn.rollback()
            raise RuntimeError(f"Erreur lors de la mise à jour de la session : {e}")

    def obtenir_ouverte(self, ticket_id: int, mac_address: str) -> Optional[Session]:
        query = """
            SELECT * FROM sessions
            WHERE ticket_id = ? AND mac_address = ? AND date_fin IS NULL
            ORDER BY id DESC LIMIT 1
        """
        try:
            cursor = self._conn.cursor()
            cursor.execute(query, (ticket_id, mac_address))
            row = cursor.fetchone()
            return Session.from_dict(dict(row)) if row else None
        except sqlite3.Error as e:
            raise RuntimeError(f"Erreur lors de la recherche de la session : {e}")

    def fermer_les_autres(self, conserves: list[int], date_fin: datetime) -> int:
        """Clôture toutes les sessions ouvertes hors de la liste donnée."""
        if conserves:
            placeholders = ",".join("?" * len(conserves))
            query = (
                f"UPDATE sessions SET date_fin = ? "
                f"WHERE date_fin IS NULL AND id NOT IN ({placeholders})"
            )
            params: tuple = (date_fin.isoformat(), *conserves)
        else:
            query = "UPDATE sessions SET date_fin = ? WHERE date_fin IS NULL"
            params = (date_fin.isoformat(),)

        try:
            cursor = self._conn.cursor()
            cursor.execute(query, params)
            self._conn.commit()
            return cursor.rowcount
        except sqlite3.Error as e:
            self._conn.rollback()
            raise RuntimeError(f"Erreur lors de la clôture des sessions : {e}")

    # ── Statistiques ──────────────────────────────────────────────────────

    def statistiques_journalieres(self, date: str) -> dict:
        query = """
            SELECT
                COUNT(*)                    AS nb_sessions,
                COALESCE(SUM(octets_recus), 0) AS volume_recu,
                COALESCE(AVG(duree_reelle), 0) AS duree_moyenne
            FROM sessions
            WHERE date(date_debut) = ?
        """
        try:
            cursor = self._conn.cursor()
            cursor.execute(query, (date,))
            row = cursor.fetchone()
            return {
                "nb_sessions":   row["nb_sessions"],
                "volume_recu":   row["volume_recu"],
                "duree_moyenne": row["duree_moyenne"],
            }
        except sqlite3.Error as e:
            raise RuntimeError(f"Erreur lors de l'agrégation des sessions : {e}")

    def activite_du_jour(self, date: str) -> list[int]:
        """Nombre de sessions démarrées par heure (24 cases, 00h à 23h)."""
        query = """
            SELECT strftime('%H', date_debut) AS heure, COUNT(*) AS nb
            FROM sessions
            WHERE date(date_debut) = ?
            GROUP BY heure
        """
        par_heure = [0] * 24
        try:
            cursor = self._conn.cursor()
            cursor.execute(query, (date,))
            for row in cursor.fetchall():
                par_heure[int(row["heure"])] = row["nb"]
            return par_heure
        except sqlite3.Error as e:
            raise RuntimeError(f"Erreur lors de l'agrégation de l'activité : {e}")

    def top_consommateurs(self, date: str, limite: int = 5) -> list[dict]:
        query = """
            SELECT
                t.code                       AS code,
                MAX(s.nom_hote)              AS nom_hote,
                SUM(s.octets_recus)          AS octets
            FROM sessions s
            JOIN tickets t ON t.id = s.ticket_id
            WHERE date(s.date_debut) = ?
            GROUP BY s.ticket_id, s.mac_address
            ORDER BY octets DESC
            LIMIT ?
        """
        try:
            cursor = self._conn.cursor()
            cursor.execute(query, (date, limite))
            return [dict(row) for row in cursor.fetchall()]
        except sqlite3.Error as e:
            raise RuntimeError(f"Erreur lors du classement des consommateurs : {e}")
