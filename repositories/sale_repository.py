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
                t.statut,
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

    def get_ventes_actives(self) -> list[dict]:
        """Ventes dont le ticket est encore actif, tous jours confondus.

        Un ticket est actif si :
        - session libre (duree_session_max = 0) non clôturée ;
        - session démarrée dont la durée n'est pas écoulée ;
        - session jamais démarrée mais encore dans sa validité (date_vente + validité).
        """
        query = """
            SELECT
                s.date_vente,
                s.methode_paiement,
                s.montant,
                t.code,
                t.statut,
                COALESCE(t.nom_affichage, hp.nom) AS profil_nom,
                t.duree_session_max AS duree_session_max,
                t.date_premiere_connexion AS date_premiere_connexion
            FROM sales s
            JOIN tickets t          ON t.id = s.ticket_id
            JOIN hotspot_profiles hp ON hp.id = t.profile_id
            WHERE
                (t.duree_session_max = 0 AND t.statut NOT IN ('epuise', 'expire'))
                OR (t.duree_session_max != 0
                    AND t.date_premiere_connexion IS NOT NULL
                    AND datetime(t.date_premiere_connexion,
                                 '+' || t.duree_session_max || ' minutes')
                        > datetime('now', 'localtime'))
                OR (t.duree_session_max != 0
                    AND t.date_premiere_connexion IS NULL
                    AND datetime(s.date_vente,
                                 '+' || t.validite || ' hours')
                        > datetime('now', 'localtime'))
            ORDER BY s.date_vente DESC
        """
        try:
            cursor = self._conn.cursor()
            cursor.execute(query)
            return [dict(row) for row in cursor.fetchall()]
        except sqlite3.Error as e:
            raise RuntimeError(f"Erreur lors de la récupération des ventes actives : {e}")

    def get_vente_par_code(self, code: str) -> dict | None:
        query = """
            SELECT s.montant, s.methode_paiement, s.date_vente,
                   t.password, t.duree_session_max,
                   COALESCE(t.nom_affichage, hp.nom) AS profil_nom
            FROM sales s
            JOIN tickets t          ON t.id = s.ticket_id
            JOIN hotspot_profiles hp ON hp.id = t.profile_id
            WHERE t.code = ?
            ORDER BY s.date_vente DESC
            LIMIT 1
        """
        try:
            cursor = self._conn.cursor()
            cursor.execute(query, (code,))
            row = cursor.fetchone()
            return dict(row) if row else None
        except sqlite3.Error as e:
            raise RuntimeError(f"Erreur récupération vente par code : {e}")

    def update_montant(self, ticket_id: int, montant: float):
        """Met à jour le montant de la vente liée à un ticket (session libre)."""
        try:
            cursor = self._conn.cursor()
            cursor.execute(
                "UPDATE sales SET montant = ? WHERE ticket_id = ?",
                (montant, ticket_id),
            )
            self._conn.commit()
        except sqlite3.Error as e:
            self._conn.rollback()
            raise RuntimeError(f"Erreur mise à jour montant : {e}")

    def agreger_par_date(self, date: str) -> dict:
        query = """
            SELECT
                COUNT(*)                                    AS nb_ventes,
                COALESCE(SUM(s.montant), 0)                 AS ca_total,
                SUM(
                    CASE
                        WHEN t.duree_session_max = 0
                             AND t.statut NOT IN ('epuise','expire') THEN 1
                        WHEN t.duree_session_max != 0
                             AND t.date_premiere_connexion IS NULL   THEN 1
                        WHEN t.duree_session_max != 0
                             AND datetime(t.date_premiere_connexion,
                                         '+' || t.duree_session_max || ' minutes')
                                  > datetime('now', 'localtime')     THEN 1
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

    def agreger_par_periode(self, date_debut: str, date_fin: str) -> dict:
        query = """
            SELECT
                COUNT(*)                    AS nb_ventes,
                COALESCE(SUM(s.montant), 0) AS ca_total
            FROM sales s
            WHERE date(s.date_vente) >= ? AND date(s.date_vente) <= ?
        """
        try:
            cursor = self._conn.cursor()
            cursor.execute(query, (date_debut, date_fin))
            row = cursor.fetchone()
            nb   = row["nb_ventes"] or 0
            ca   = row["ca_total"]  or 0
            return {
                "nb_ventes":    nb,
                "ca_total":     int(ca),
                "ticket_moyen": round(ca / nb) if nb else 0,
            }
        except sqlite3.Error as e:
            raise RuntimeError(f"Erreur agrégation période : {e}")

    def ventes_par_jour(self, date_debut: str, date_fin: str) -> list[dict]:
        query = """
            SELECT
                date(s.date_vente)          AS jour,
                COUNT(*)                    AS nb_ventes,
                COALESCE(SUM(s.montant), 0) AS ca
            FROM sales s
            WHERE date(s.date_vente) >= ? AND date(s.date_vente) <= ?
            GROUP BY jour
            ORDER BY jour ASC
        """
        try:
            cursor = self._conn.cursor()
            cursor.execute(query, (date_debut, date_fin))
            return [dict(row) for row in cursor.fetchall()]
        except sqlite3.Error as e:
            raise RuntimeError(f"Erreur ventes par jour : {e}")

    def top_profils_periode(self, date_debut: str, date_fin: str, limite: int = 5) -> list[dict]:
        query = """
            SELECT
                COALESCE(t.nom_affichage, hp.nom) AS profil,
                COUNT(*)                           AS nb_ventes,
                COALESCE(SUM(s.montant), 0)        AS ca
            FROM sales s
            JOIN tickets t          ON t.id = s.ticket_id
            JOIN hotspot_profiles hp ON hp.id = t.profile_id
            WHERE date(s.date_vente) >= ? AND date(s.date_vente) <= ?
            GROUP BY profil
            ORDER BY nb_ventes DESC
            LIMIT ?
        """
        try:
            cursor = self._conn.cursor()
            cursor.execute(query, (date_debut, date_fin, limite))
            return [dict(row) for row in cursor.fetchall()]
        except sqlite3.Error as e:
            raise RuntimeError(f"Erreur top profils : {e}")
