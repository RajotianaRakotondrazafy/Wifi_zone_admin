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
        