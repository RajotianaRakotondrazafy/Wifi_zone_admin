import sqlite3
from datetime import datetime
from typing import Optional

from database.connection import DatabaseConnection
from models.blocage import Blocage


class BlocageRepository:

    def __init__(self):
        self._conn: sqlite3.Connection = DatabaseConnection.get_connection()

    def creer(self, blocage: Blocage) -> Blocage:
        query = """
            INSERT INTO blocages (mac_address, nom, ip_assignee, raison, date_blocage)
            VALUES (?, ?, ?, ?, ?)
        """
        try:
            cursor = self._conn.cursor()
            cursor.execute(query, (
                blocage.mac_address,
                blocage.nom,
                blocage.ip_assignee,
                blocage.raison,
                blocage.date_blocage.isoformat() if blocage.date_blocage else datetime.now().isoformat(),
            ))
            self._conn.commit()
            blocage.id = cursor.lastrowid
            return blocage
        except sqlite3.Error as e:
            self._conn.rollback()
            raise RuntimeError(f"Erreur lors de la création du blocage : {e}")

    def lister_tous(self) -> list[Blocage]:
        query = "SELECT * FROM blocages ORDER BY date_blocage DESC"
        try:
            cursor = self._conn.cursor()
            cursor.execute(query)
            return [Blocage.from_dict(dict(row)) for row in cursor.fetchall()]
        except sqlite3.Error as e:
            raise RuntimeError(f"Erreur lors de la récupération des blocages : {e}")

    def obtenir_par_id(self, blocage_id: int) -> Optional[Blocage]:
        query = "SELECT * FROM blocages WHERE id = ?"
        try:
            cursor = self._conn.cursor()
            cursor.execute(query, (blocage_id,))
            row = cursor.fetchone()
            return Blocage.from_dict(dict(row)) if row else None
        except sqlite3.Error as e:
            raise RuntimeError(f"Erreur lors de la récupération du blocage : {e}")

    def trouver_par_mac(self, mac_address: str) -> Optional[Blocage]:
        query = "SELECT * FROM blocages WHERE mac_address = ? COLLATE NOCASE ORDER BY id DESC LIMIT 1"
        try:
            cursor = self._conn.cursor()
            cursor.execute(query, (mac_address,))
            row = cursor.fetchone()
            return Blocage.from_dict(dict(row)) if row else None
        except sqlite3.Error as e:
            raise RuntimeError(f"Erreur lors de la recherche du blocage : {e}")

    def supprimer(self, blocage_id: int) -> bool:
        query = "DELETE FROM blocages WHERE id = ?"
        try:
            cursor = self._conn.cursor()
            cursor.execute(query, (blocage_id,))
            self._conn.commit()
            return cursor.rowcount > 0
        except sqlite3.Error as e:
            self._conn.rollback()
            raise RuntimeError(f"Erreur lors de la suppression du blocage : {e}")
