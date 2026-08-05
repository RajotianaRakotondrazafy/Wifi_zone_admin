import sqlite3
from database.connection import DatabaseConnection
from models.sale import Sale

class SaleRepository:
    
    def __init__(self):
        self._conn: sqlite3.Connection = DatabaseConnection.get_connection()

    def create_sale(self, sale: Sale):
        query = """
            INSERT INTO sales (ticket_id, user_id, montant, date_vente, methode_paiement)
            VALUES (?, ?, ?, ?, ?)
        """

        try:
            cursor = self._conn.cursor()
            cursor.execute(query, (
                sale.ticket_id,
                sale.user_id,
                sale.montant,
                sale.date_vente,
                sale.methode_paiement
            ))
            self._conn.commit()
            sale.id = cursor.lastrowid
            return sale
        
        except sqlite3.Error as e:
            self._conn.rollback()
            raise RuntimeError(f"Erreur lors de la création de la vente : {e}")
        
    def get_all_sales_by_date(self, date: str):
        query = "SELECT * FROM sales WHERE date(date_vente) = ? ORDER BY date_vente DESC"
        try:
            cursor = self._conn.cursor()
            cursor.execute(query, (date,))
            rows = cursor.fetchall()
            return [Sale.from_dict(dict(row)) for row in rows]
        except sqlite3.Error as e:
            raise RuntimeError(f"Erreur lors de la récupération des ventes : {e}")

    def get_ventes_du_jour(self, date: str) -> list[dict]:
        query = """
            SELECT
                s.date_vente,
                s.methode_paiement,
                s.montant,
                t.code,
                COALESCE(t.nom_affichage, hp.nom) AS profil_nom,
                t.duree_session_max AS duree_session_max,
                t.date_premiere_connexion AS date_premiere_connexion
            FROM sales s
            JOIN tickets t          ON t.id = s.ticket_id
            JOIN hotspot_profiles hp ON hp.id = t.profile_id
            WHERE s.date_vente >= ? AND s.date_vente < date(?, '+1 day')
            ORDER BY s.date_vente DESC
        """
        try:
            cursor = self._conn.cursor()
            cursor.execute(query, (date, date))
            return [dict(row) for row in cursor.fetchall()]
        except sqlite3.Error as e:
            raise RuntimeError(f"Erreur lors de la récupération des ventes du jour : {e}")

    def agreger_par_date(self, date: str) -> dict:
        query = """
            SELECT
                COUNT(*)                                    AS nb_ventes,
                COALESCE(SUM(s.montant), 0)                 AS ca_total,
                SUM(
                    CASE
                        WHEN t.date_premiere_connexion IS NULL THEN 1
                        WHEN datetime(t.date_premiere_connexion,
                                     '+' || t.duree_session_max || ' minutes')
                                  > datetime('now', 'localtime')
                             THEN 1
                        ELSE 0
                    END
                )                                           AS nb_actifs
            FROM sales s
            JOIN tickets t ON t.id = s.ticket_id
            WHERE s.date_vente >= ? AND s.date_vente < date(?, '+1 day')
        """
        try:
            cursor = self._conn.cursor()
            cursor.execute(query, (date, date))
            row = cursor.fetchone()
            return {
                "nb_ventes": row["nb_ventes"],
                "ca_total":  row["ca_total"],
                "nb_actifs": row["nb_actifs"],
            }
        except sqlite3.Error as e:
            raise RuntimeError(f"Erreur lors de l'agrégation des ventes : {e}")
        