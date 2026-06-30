import sqlite3
from database.connection import DatabaseConnection
from models.user import User
from typing import Optional

class UserRepository:
    def __init__(self):
        self._conn: sqlite3.Connection = DatabaseConnection.get_connection()
    
    def create_user(self, user: User):
        query = """
            INSERT INTO users (nom, login, mot_de_passe_hash, role)
            VALUES (?, ?, ?, ?)
        """

        try:
            cursor = self._conn.cursor()
            cursor.execute(query, (
                user.nom,
                user.login,
                user.mot_de_passe_hash,
                user.role.value,
            ))
            self._conn.commit()
            user.id = cursor.lastrowid
            return user
        
        except sqlite3.Error as e:
            self._conn.rollback()
            raise RuntimeError(f"Erreur lors de la création d'un user : {e}")
        
    def get_by_login(self, login: str) -> Optional[User]:
        query = "SELECT * FROM users WHERE login = ?"
        try:
            cursor = self._conn.cursor()
            cursor.execute(query, (login,))
            row = cursor.fetchone()
            return User.from_dict(dict(row)) if row else None
        except sqlite3.Error as e:
            raise RuntimeError(f"Erreur lors de la recherche de l'utilisateur : {e}")
        
    def update(self, user: User) -> bool:
        if user.id is None:
            raise ValueError("Impossible de mettre à jour un utilisateur sans id.")
 
        query = """
            UPDATE users SET
                nom = ?, login = ?, mot_de_passe_hash = ?, role = ?
            WHERE id = ?
        """
        try:
            cursor = self._conn.cursor()
            cursor.execute(
                query,
                (
                    user.nom,
                    user.login,
                    user.mot_de_passe_hash,
                    user.role.value,
                    user.id,
                ),
            )
            self._conn.commit()
            return cursor.rowcount > 0
        
        except sqlite3.Error as e:
            self.conn.rollback()
            raise RuntimeError(f"Erreur lors de la mise à jour de l'utilisateur : {e}")


    