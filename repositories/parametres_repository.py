import sqlite3
from database.connection import DatabaseConnection


class ParametresRepository:
    def __init__(self):
        self._conn: sqlite3.Connection = DatabaseConnection.get_connection()

    def get(self, cle: str, defaut: str = "") -> str:
        try:
            cursor = self._conn.cursor()
            cursor.execute("SELECT valeur FROM parametres WHERE cle = ?", (cle,))
            row = cursor.fetchone()
            return row["valeur"] if row else defaut
        except sqlite3.Error:
            return defaut

    def get_int(self, cle: str, defaut: int = 0) -> int:
        try:
            return int(self.get(cle, str(defaut)))
        except ValueError:
            return defaut

    def set(self, cle: str, valeur: str) -> None:
        cursor = self._conn.cursor()
        cursor.execute(
            "INSERT INTO parametres (cle, valeur) VALUES (?, ?)"
            " ON CONFLICT(cle) DO UPDATE SET valeur = excluded.valeur",
            (cle, valeur),
        )
        self._conn.commit()

    def get_all(self) -> dict[str, str]:
        try:
            cursor = self._conn.cursor()
            cursor.execute("SELECT cle, valeur FROM parametres")
            return {row["cle"]: row["valeur"] for row in cursor.fetchall()}
        except sqlite3.Error:
            return {}
