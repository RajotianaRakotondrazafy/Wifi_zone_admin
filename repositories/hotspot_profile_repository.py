import sqlite3
from database.connection import DatabaseConnection
from models.hotspot_profile import HotspotProfile


class HotspotProfileRepository:

    def __init__(self):
        self._conn: sqlite3.Connection = DatabaseConnection.get_connection()

    def lister_tous(self, actif_seulement: bool = False,
                    exclure_internes: bool = False) -> list[HotspotProfile]:
        conditions = []
        if actif_seulement:
            conditions.append("statut = 'actif'")
        if exclure_internes:
            conditions.append("interne = 0")
        query = "SELECT * FROM hotspot_profiles"
        if conditions:
            query += " WHERE " + " AND ".join(conditions)
        query += " ORDER BY prix ASC"
        try:
            cursor = self._conn.cursor()
            cursor.execute(query)
            rows = cursor.fetchall()
            return [HotspotProfile.from_dict(dict(row)) for row in rows]
        except sqlite3.Error as e:
            raise RuntimeError(f"Erreur lors de la récupération des profils : {e}")

    def lister_par_router(self, router_id: int, actif_seulement: bool = False,
                          exclure_internes: bool = False) -> list[HotspotProfile]:
        conditions = ["router_id = ?"]
        if actif_seulement:
            conditions.append("statut = 'actif'")
        if exclure_internes:
            conditions.append("interne = 0")
        query = "SELECT * FROM hotspot_profiles WHERE " + " AND ".join(conditions)
        query += " ORDER BY prix ASC"
        try:
            cursor = self._conn.cursor()
            cursor.execute(query, (router_id,))
            rows = cursor.fetchall()
            return [HotspotProfile.from_dict(dict(row)) for row in rows]
        except sqlite3.Error as e:
            raise RuntimeError(f"Erreur lors de la récupération des profils : {e}")

    def obtenir_par_id(self, profile_id: int) -> HotspotProfile | None:
        query = "SELECT * FROM hotspot_profiles WHERE id = ?"
        try:
            cursor = self._conn.cursor()
            cursor.execute(query, (profile_id,))
            row = cursor.fetchone()
            return HotspotProfile.from_dict(dict(row)) if row else None
        except sqlite3.Error as e:
            raise RuntimeError(f"Erreur lors de la récupération du profil : {e}")

    def creer(self, profil: HotspotProfile) -> HotspotProfile:
        query = """
            INSERT INTO hotspot_profiles
                (router_id, nom, debit_max, duree_session_max, validite, prix,
                 utilisateurs_max, statut, interne)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        try:
            cursor = self._conn.cursor()
            cursor.execute(query, (
                profil.router_id, profil.nom, profil.debit_max,
                profil.duree_session_max, profil.validite, profil.prix,
                profil.utilisateurs_max, profil.statut, int(profil.interne),
            ))
            self._conn.commit()
            profil.id = cursor.lastrowid
            return profil
        except sqlite3.Error as e:
            self._conn.rollback()
            raise RuntimeError(f"Erreur lors de la création du profil : {e}")

    def modifier(self, profil: HotspotProfile) -> bool:
        if profil.id is None:
            raise ValueError("Impossible de modifier un profil sans id.")
        query = """
            UPDATE hotspot_profiles
            SET router_id = ?, nom = ?, debit_max = ?, duree_session_max = ?,
                validite = ?, prix = ?, utilisateurs_max = ?, statut = ?, interne = ?
            WHERE id = ?
        """
        try:
            cursor = self._conn.cursor()
            cursor.execute(query, (
                profil.router_id, profil.nom, profil.debit_max,
                profil.duree_session_max, profil.validite, profil.prix,
                profil.utilisateurs_max, profil.statut, int(profil.interne), profil.id,
            ))
            self._conn.commit()
            return cursor.rowcount > 0
        except sqlite3.Error as e:
            self._conn.rollback()
            raise RuntimeError(f"Erreur lors de la modification du profil : {e}")

    def basculer_statut(self, profile_id: int) -> str:
        """Bascule 'actif' ↔ 'inactif'. Retourne le nouveau statut."""
        profil = self.obtenir_par_id(profile_id)
        if profil is None:
            raise RuntimeError("Profil introuvable.")

        nouveau = "inactif" if profil.statut == "actif" else "actif"
        try:
            cursor = self._conn.cursor()
            cursor.execute(
                "UPDATE hotspot_profiles SET statut = ? WHERE id = ?",
                (nouveau, profile_id),
            )
            self._conn.commit()
            return nouveau
        except sqlite3.Error as e:
            self._conn.rollback()
            raise RuntimeError(f"Erreur lors du changement de statut du profil : {e}")

    def supprimer(self, profile_id: int) -> bool:
        # Protection FK : un profil déjà utilisé par des tickets ne peut pas être supprimé
        cursor = self._conn.cursor()
        cursor.execute("SELECT COUNT(*) AS n FROM tickets WHERE profile_id = ?", (profile_id,))
        if cursor.fetchone()["n"] > 0:
            raise RuntimeError(
                "Impossible de supprimer ce profil : il est déjà utilisé par des tickets émis."
            )

        query = "DELETE FROM hotspot_profiles WHERE id = ?"
        try:
            cursor.execute(query, (profile_id,))
            self._conn.commit()
            return cursor.rowcount > 0
        except sqlite3.Error as e:
            self._conn.rollback()
            raise RuntimeError(f"Erreur lors de la suppression du profil : {e}")
