import sqlite3
from datetime import datetime

from database.connection import DatabaseConnection
from models.produit import Produit
from models.vente_produit import VenteProduit


class ProduitRepository:
    def __init__(self):
        self._conn: sqlite3.Connection = DatabaseConnection.get_connection()

    # ── Produits ─────────────────────────────────────────────────────────

    def lister_produits(self, actif_seulement: bool = False) -> list[Produit]:
        query = "SELECT * FROM produits"
        if actif_seulement:
            query += " WHERE actif = 1"
        query += " ORDER BY categorie ASC, nom ASC"
        try:
            cursor = self._conn.cursor()
            cursor.execute(query)
            return [Produit.from_dict(dict(row)) for row in cursor.fetchall()]
        except sqlite3.Error as e:
            raise RuntimeError(f"Erreur lors de la récupération des produits : {e}")

    def obtenir_par_id(self, produit_id: int) -> Produit | None:
        try:
            cursor = self._conn.cursor()
            cursor.execute("SELECT * FROM produits WHERE id = ?", (produit_id,))
            row = cursor.fetchone()
            return Produit.from_dict(dict(row)) if row else None
        except sqlite3.Error as e:
            raise RuntimeError(f"Erreur récupération produit {produit_id} : {e}")

    def creer_produit(self, produit: Produit) -> Produit:
        query = """
            INSERT INTO produits (nom, categorie, prix_unitaire, actif)
            VALUES (?, ?, ?, ?)
        """
        try:
            cursor = self._conn.cursor()
            cursor.execute(query, (
                produit.nom,
                produit.categorie,
                produit.prix_unitaire,
                int(produit.actif),
            ))
            self._conn.commit()
            produit.id = cursor.lastrowid
            return produit
        except sqlite3.Error as e:
            self._conn.rollback()
            raise RuntimeError(f"Erreur lors de la création du produit : {e}")

    def modifier_produit(self, produit: Produit) -> None:
        query = """
            UPDATE produits
            SET nom = ?, categorie = ?, prix_unitaire = ?
            WHERE id = ?
        """
        try:
            cursor = self._conn.cursor()
            cursor.execute(query, (
                produit.nom,
                produit.categorie,
                produit.prix_unitaire,
                produit.id,
            ))
            self._conn.commit()
        except sqlite3.Error as e:
            self._conn.rollback()
            raise RuntimeError(f"Erreur lors de la modification du produit : {e}")

    def definir_actif(self, produit_id: int, actif: bool) -> None:
        try:
            cursor = self._conn.cursor()
            cursor.execute(
                "UPDATE produits SET actif = ? WHERE id = ?",
                (int(actif), produit_id),
            )
            self._conn.commit()
        except sqlite3.Error as e:
            self._conn.rollback()
            raise RuntimeError(f"Erreur lors de l'activation/désactivation du produit : {e}")

    # ── Ventes de produits ───────────────────────────────────────────────

    def creer_vente(self, vente: VenteProduit) -> VenteProduit:
        query = """
            INSERT INTO ventes_produits
                (produit_id, quantite, prix_unitaire, montant, methode_paiement,
                 date_vente, user_id, annule)
            VALUES (?, ?, ?, ?, ?, ?, ?, 0)
        """
        try:
            cursor = self._conn.cursor()
            cursor.execute(query, (
                vente.produit_id,
                vente.quantite,
                vente.prix_unitaire,
                vente.montant,
                vente.methode_paiement,
                vente.date_vente,
                vente.user_id,
            ))
            self._conn.commit()
            vente.id = cursor.lastrowid
            return vente
        except sqlite3.Error as e:
            self._conn.rollback()
            raise RuntimeError(f"Erreur lors de la création de la vente produit : {e}")

    def lister_ventes_du_jour(self, date: str) -> list[dict]:
        query = """
            SELECT
                vp.id              AS vente_id,
                vp.annule,
                vp.date_vente,
                vp.quantite,
                vp.prix_unitaire,
                vp.montant,
                vp.methode_paiement,
                p.nom              AS produit_nom,
                p.categorie        AS categorie
            FROM ventes_produits vp
            JOIN produits p ON p.id = vp.produit_id
            WHERE date(vp.date_vente) = ?
            ORDER BY vp.date_vente DESC
        """
        try:
            cursor = self._conn.cursor()
            cursor.execute(query, (date,))
            return [dict(row) for row in cursor.fetchall()]
        except sqlite3.Error as e:
            raise RuntimeError(f"Erreur lors de la récupération des ventes produits : {e}")

    def agreger_du_jour(self, date: str) -> dict:
        query = """
            SELECT
                COUNT(*)                    AS nb_ventes,
                COALESCE(SUM(vp.quantite), 0) AS nb_articles,
                COALESCE(SUM(vp.montant), 0) AS ca_total
            FROM ventes_produits vp
            WHERE vp.annule = 0 AND date(vp.date_vente) = ?
        """
        try:
            cursor = self._conn.cursor()
            cursor.execute(query, (date,))
            row = cursor.fetchone()
            return {
                "nb_ventes":   row["nb_ventes"],
                "nb_articles": row["nb_articles"],
                "ca_total":    row["ca_total"],
            }
        except sqlite3.Error as e:
            raise RuntimeError(f"Erreur lors de l'agrégation des ventes produits : {e}")

    def ventes_par_categorie_du_jour(self, date: str) -> list[dict]:
        query = """
            SELECT
                p.categorie                       AS categorie,
                COUNT(*)                          AS nb_ventes,
                COALESCE(SUM(vp.quantite), 0)     AS quantite,
                COALESCE(SUM(vp.montant), 0)      AS ca
            FROM ventes_produits vp
            JOIN produits p ON p.id = vp.produit_id
            WHERE vp.annule = 0 AND date(vp.date_vente) = ?
            GROUP BY p.categorie
            ORDER BY ca DESC
        """
        try:
            cursor = self._conn.cursor()
            cursor.execute(query, (date,))
            return [dict(row) for row in cursor.fetchall()]
        except sqlite3.Error as e:
            raise RuntimeError(f"Erreur agrégation par catégorie : {e}")

    def annuler_vente(self, vente_id: int) -> None:
        try:
            cursor = self._conn.cursor()
            cursor.execute(
                "UPDATE ventes_produits SET annule = 1, date_annulation = CURRENT_TIMESTAMP "
                "WHERE id = ?",
                (vente_id,),
            )
            self._conn.commit()
        except sqlite3.Error as e:
            self._conn.rollback()
            raise RuntimeError(f"Erreur lors de l'annulation de la vente produit : {e}")

    def ventes_par_periode(self, date_debut: str, date_fin: str) -> list[dict]:
        query = """
            SELECT
                date(vp.date_vente)          AS jour,
                COUNT(*)                     AS nb_ventes,
                COALESCE(SUM(vp.quantite), 0) AS nb_articles,
                COALESCE(SUM(vp.montant), 0)  AS ca
            FROM ventes_produits vp
            WHERE vp.annule = 0
              AND date(vp.date_vente) >= ? AND date(vp.date_vente) <= ?
            GROUP BY jour
            ORDER BY jour ASC
        """
        try:
            cursor = self._conn.cursor()
            cursor.execute(query, (date_debut, date_fin))
            return [dict(row) for row in cursor.fetchall()]
        except sqlite3.Error as e:
            raise RuntimeError(f"Erreur ventes produits par période : {e}")
