import sqlite3
from datetime import datetime

from database.connection import DatabaseConnection
from models.depense import Depense


class DepenseRepository:
    def __init__(self):
        self._conn: sqlite3.Connection = DatabaseConnection.get_connection()

    def creer(self, depense: Depense) -> Depense:
        query = """
            INSERT INTO depenses
                (montant, motif, categorie, methode_paiement, date_depense, user_id, annule)
            VALUES (?, ?, ?, ?, ?, ?, 0)
        """
        try:
            cursor = self._conn.cursor()
            cursor.execute(query, (
                depense.montant,
                depense.motif,
                depense.categorie,
                depense.methode_paiement,
                depense.date_depense.isoformat() if depense.date_depense else None,
                depense.user_id,
            ))
            self._conn.commit()
            depense.id = cursor.lastrowid
            return depense
        except sqlite3.Error as e:
            self._conn.rollback()
            raise RuntimeError(f"Erreur lors de la création de la dépense : {e}")

    def lister_du_jour(self, date: str) -> list[dict]:
        query = """
            SELECT * FROM depenses
            WHERE date(date_depense) = ?
            ORDER BY date_depense DESC
        """
        try:
            cursor = self._conn.cursor()
            cursor.execute(query, (date,))
            return [dict(row) for row in cursor.fetchall()]
        except sqlite3.Error as e:
            raise RuntimeError(f"Erreur lors de la récupération des dépenses : {e}")

    def agreger_du_jour(self, date: str) -> dict:
        query = """
            SELECT
                COUNT(*)                          AS nb_depenses,
                COALESCE(SUM(CASE WHEN annule = 0 THEN montant END), 0) AS total,
                COALESCE(SUM(CASE WHEN annule = 1 THEN montant END), 0) AS total_annulees
            FROM depenses
            WHERE date(date_depense) = ?
        """
        try:
            cursor = self._conn.cursor()
            cursor.execute(query, (date,))
            row = cursor.fetchone()
            return {
                "nb_depenses":     row["nb_depenses"] or 0,
                "total":           int(row["total"] or 0),
                "total_annulees":  int(row["total_annulees"] or 0),
            }
        except sqlite3.Error as e:
            raise RuntimeError(f"Erreur lors de l'agrégation des dépenses : {e}")

    def agreger_par_periode(self, date_debut: str, date_fin: str) -> int:
        query = """
            SELECT COALESCE(SUM(montant), 0) AS total
            FROM depenses
            WHERE annule = 0
              AND date(date_depense) >= ? AND date(date_depense) <= ?
        """
        try:
            cursor = self._conn.cursor()
            cursor.execute(query, (date_debut, date_fin))
            row = cursor.fetchone()
            return int(row["total"] or 0)
        except sqlite3.Error as e:
            raise RuntimeError(f"Erreur lors de l'agrégation des dépenses par période : {e}")

    def annuler(self, depense_id: int) -> None:
        try:
            cursor = self._conn.cursor()
            cursor.execute(
                "UPDATE depenses SET annule = 1, date_annulation = CURRENT_TIMESTAMP "
                "WHERE id = ?",
                (depense_id,),
            )
            self._conn.commit()
        except sqlite3.Error as e:
            self._conn.rollback()
            raise RuntimeError(f"Erreur lors de l'annulation de la dépense : {e}")