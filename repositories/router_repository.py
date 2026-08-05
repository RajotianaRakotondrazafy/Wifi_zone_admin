import sqlite3
from database.connection import DatabaseConnection
from models.router import Router


class RouterRepository:

    def __init__(self):
        self._conn: sqlite3.Connection = DatabaseConnection.get_connection()

    def lister_tous(self) -> list[Router]:
        query = "SELECT * FROM routers ORDER BY nom ASC"
        try:
            cursor = self._conn.cursor()
            cursor.execute(query)
            rows = cursor.fetchall()
            return [Router.from_dict(dict(row)) for row in rows]
        except sqlite3.Error as e:
            raise RuntimeError(f"Erreur lors de la récupération des routeurs : {e}")

    def obtenir_par_id(self, router_id: int) -> Router | None:
        query = "SELECT * FROM routers WHERE id = ?"
        try:
            cursor = self._conn.cursor()
            cursor.execute(query, (router_id,))
            row = cursor.fetchone()
            return Router.from_dict(dict(row)) if row else None
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
                routeur.username, routeur.password_chiffre, routeur.statut,
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
                routeur.username, routeur.password_chiffre, routeur.statut,
                routeur.id,
            ))
            self._conn.commit()
            return cursor.rowcount > 0
        except sqlite3.Error as e:
            self._conn.rollback()
            raise RuntimeError(f"Erreur lors de la modification du routeur : {e}")

    def supprimer(self, router_id: int) -> bool:
        query = "DELETE FROM routers WHERE id = ?"
        try:
            cursor = self._conn.cursor()
            cursor.execute(query, (router_id,))
            self._conn.commit()
            return cursor.rowcount > 0
        except sqlite3.Error as e:
            self._conn.rollback()
            raise RuntimeError(f"Erreur lors de la suppression du routeur : {e}")
