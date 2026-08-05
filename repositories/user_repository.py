import sqlite3
from database.connection import DatabaseConnection
from models.user import User
from typing import Optional

class UserRepository:
    def __init__(self):
        self._conn: sqlite3.Connection = DatabaseConnection.get_connection()
    
    def create_user(self, user: User):
        query = """
            INSERT INTO users (nom, login, mot_de_passe_hash, role, actif)
            VALUES (?, ?, ?, ?, ?)
        """

        try:
            cursor = self._conn.cursor()
            cursor.execute(query, (
                user.nom,
                user.login,
                user.mot_de_passe_hash,
                user.role.value,
                int(user.actif),
            ))
            self._conn.commit()
            user.id = cursor.lastrowid
            return user
        
        except sqlite3.IntegrityError as e:
            self._conn.rollback()
            if "users.login" in str(e):
                raise RuntimeError("Un compte avec cet identifiant existe déjà.")
            raise RuntimeError(f"Erreur lors de la création d'un user : {e}")
        except sqlite3.Error as e:
            self._conn.rollback()
            raise RuntimeError(f"Erreur lors de la création d'un user : {e}")
        
    def lister_tous(self) -> list[User]:
        query = "SELECT * FROM users ORDER BY id"
        try:
            cursor = self._conn.cursor()
            cursor.execute(query)
            return [User.from_dict(dict(row)) for row in cursor.fetchall()]
        except sqlite3.Error as e:
            raise RuntimeError(f"Erreur lors du chargement des utilisateurs : {e}")

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
                nom = ?, login = ?, mot_de_passe_hash = ?, role = ?, actif = ?
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
                    int(user.actif),
                    user.id,
                ),
            )
            self._conn.commit()
            return cursor.rowcount > 0
        
        except sqlite3.IntegrityError as e:
            self._conn.rollback()
            if "users.login" in str(e):
                raise RuntimeError("Un compte avec cet identifiant existe déjà.")
            raise RuntimeError(f"Erreur lors de la mise à jour de l'utilisateur : {e}")
        except sqlite3.Error as e:
            self._conn.rollback()
            raise RuntimeError(f"Erreur lors de la mise à jour de l'utilisateur : {e}")

    def basculer_actif(self, user_id: int) -> bool:
        """Inverse l'état actif/inactif. Retourne le nouvel état."""
        try:
            curseur = self._conn.cursor()
            curseur.execute("SELECT actif FROM users WHERE id = ?", (user_id,))
            row = curseur.fetchone()
            if row is None:
                raise RuntimeError("Utilisateur introuvable.")

            nouvel_etat = 0 if row[0] else 1
            curseur.execute(
                "UPDATE users SET actif = ? WHERE id = ?",
                (nouvel_etat, user_id),
            )
            self._conn.commit()
            return bool(nouvel_etat)
        except sqlite3.Error as e:
            self._conn.rollback()
            raise RuntimeError(f"Erreur lors de la bascule de l'état utilisateur : {e}")

    def supprimer(self, user_id: int) -> None:
        """Supprime un utilisateur, sauf s'il est référencé par des ventes ou des journaux."""
        try:
            curseur = self._conn.cursor()

            curseur.execute("SELECT COUNT(*) FROM sales WHERE user_id = ?", (user_id,))
            nb_ventes = curseur.fetchone()[0]
            curseur.execute("SELECT COUNT(*) FROM activity_logs WHERE user_id = ?", (user_id,))
            nb_journaux = curseur.fetchone()[0]

            if nb_ventes or nb_journaux:
                raise RuntimeError(
                    "Impossible de supprimer ce compte : il est déjà utilisé par des ventes "
                    "ou des journaux d'activité. Désactivez-le à la place."
                )

            curseur.execute("DELETE FROM users WHERE id = ?", (user_id,))
            self._conn.commit()
        except sqlite3.Error as e:
            self._conn.rollback()
            raise RuntimeError(f"Erreur lors de la suppression de l'utilisateur : {e}")


    