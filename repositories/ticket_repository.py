import sqlite3, datetime
from typing import List, Optional
from database.connection import DatabaseConnection
from models.ticket import Ticket

class TicketRepository:
    def __init__(self):
        self._conn: sqlite3.Connection = DatabaseConnection().get_connection()


    def create_ticket(self, ticket: Ticket) -> Ticket:
        query = """
            INSERT INTO tickets (
                code, password, profile_id, duree_session_max, validite, statut,
                date_generation, date_premiere_connexion, date_expiration, nom_affichage
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        try:
            cursor = self._conn.cursor()
            cursor.execute(query, (
                ticket.code,
                ticket.password,
                ticket.profile_id,
                ticket.duree_session_max,
                ticket.validite,
                ticket.statut.value,
                ticket.date_generation or datetime.datetime.now(),
                ticket.date_premiere_connexion,
                ticket.date_expiration,
                ticket.nom_affichage,
            ))
            self._conn.commit()
            ticket.id = cursor.lastrowid
            return ticket
        
        except sqlite3.Error as e:
            self._conn.rollback()
            raise RuntimeError(f"Erreur lors de la création du Ticket : {e}")
        
    
    def get_all_tickets(self) -> List[Ticket]:
        query = "SELECT * FROM tickets ORDER BY date_generation DESC"
        try:
            cursor = self._conn.cursor()
            cursor.execute(query)
            rows = cursor.fetchall()
            return [Ticket.from_dict(dict(row)) for row in rows]
        except sqlite3.Error as e:
            raise RuntimeError(f"Erreur lors de la récupération des Tickets : {e}")
        

    def get_ticket_by_code(self, code: str) -> Optional[Ticket]:
        query = "SELECT * FROM tickets WHERE code = ?"
        try:
            cursor = self._conn.cursor()
            cursor.execute(query, (code,))
            row = cursor.fetchone()
            return Ticket.from_dict(dict(row)) if row else None
        except sqlite3.Error as e:
            raise RuntimeError(f"Erreur lors de la recherche du ticket : {e}")

    def obtenir_par_id(self, ticket_id: int) -> Optional[Ticket]:
        query = "SELECT * FROM tickets WHERE id = ?"
        try:
            cursor = self._conn.cursor()
            cursor.execute(query, (ticket_id,))
            row = cursor.fetchone()
            return Ticket.from_dict(dict(row)) if row else None
        except sqlite3.Error as e:
            raise RuntimeError(f"Erreur lors de la récupération du ticket : {e}")

    def lister_sans_premiere_connexion(self) -> List[Ticket]:
        """Tickets vendus dont le client ne s'est jamais connecté."""
        query = """
            SELECT * FROM tickets
            WHERE date_premiere_connexion IS NULL
            ORDER BY date_generation ASC
        """
        try:
            cursor = self._conn.cursor()
            cursor.execute(query)
            rows = cursor.fetchall()
            return [Ticket.from_dict(dict(row)) for row in rows]
        except sqlite3.Error as e:
            raise RuntimeError(f"Erreur lors de la récupération des tickets non utilisés : {e}")

    def marquer_premiere_connexion(
        self,
        ticket_id: int,
        date_connexion: datetime.datetime,
        date_expiration: datetime.datetime,
    ) -> bool:
        """Enregistre la première connexion du client et passe le ticket à 'actif'."""
        query = """
            UPDATE tickets
            SET date_premiere_connexion = ?, date_expiration = ?, statut = 'actif'
            WHERE id = ? AND date_premiere_connexion IS NULL
        """
        try:
            cursor = self._conn.cursor()
            cursor.execute(query, (
                date_connexion.isoformat(),
                date_expiration.isoformat(),
                ticket_id,
            ))
            self._conn.commit()
            return cursor.rowcount > 0
        except sqlite3.Error as e:
            self._conn.rollback()
            raise RuntimeError(f"Erreur lors de l'enregistrement de la première connexion : {e}")
        
    
    def marquer_cloture(self, ticket_id: int):
        """Passe le statut du ticket à 'epuise' (session libre clôturée)."""
        try:
            cursor = self._conn.cursor()
            cursor.execute(
                "UPDATE tickets SET statut = 'epuise' WHERE id = ?",
                (ticket_id,),
            )
            self._conn.commit()
        except sqlite3.Error as e:
            self._conn.rollback()
            raise RuntimeError(f"Erreur clôture ticket : {e}")

    def lister_expires_actifs(self) -> List[Ticket]:
        """Tickets encore 'actif' en DB dont la date d'expiration est dépassée."""
        query = """
            SELECT * FROM tickets
            WHERE statut = 'actif'
              AND date_expiration IS NOT NULL
              AND datetime(date_expiration) < datetime('now', 'localtime')
        """
        try:
            cursor = self._conn.cursor()
            cursor.execute(query)
            return [Ticket.from_dict(dict(row)) for row in cursor.fetchall()]
        except sqlite3.Error as e:
            raise RuntimeError(f"Erreur lister_expires_actifs : {e}")

    def lister_expirant_bientot(self, minutes: int = 30) -> List[Ticket]:
        """Tickets actifs dont l'expiration est dans moins de `minutes` minutes."""
        query = """
            SELECT * FROM tickets
            WHERE statut = 'actif'
              AND date_premiere_connexion IS NOT NULL
              AND duree_session_max > 0
              AND datetime(date_premiere_connexion, '+' || duree_session_max || ' minutes')
                  > datetime('now', 'localtime')
              AND datetime(date_premiere_connexion, '+' || duree_session_max || ' minutes')
                  < datetime('now', 'localtime', '+' || ? || ' minutes')
            ORDER BY datetime(date_premiere_connexion, '+' || duree_session_max || ' minutes') ASC
        """
        try:
            cursor = self._conn.cursor()
            cursor.execute(query, (minutes,))
            return [Ticket.from_dict(dict(row)) for row in cursor.fetchall()]
        except sqlite3.Error as e:
            raise RuntimeError(f"Erreur lister_expirant_bientot : {e}")

    def update_ticket(self, ticket: Ticket) -> bool:
        if ticket.id is None:
            raise ValueError("Impossible de mettre à jour un ticket sans id.")
        
        query = """
            UPDATE tickets
            SET code = ?, password = ?, profile_id = ?, duree_session_max = ?, validite = ?,
                statut = ?, date_generation = ?, date_premiere_connexion = ?, date_expiration = ?,
                nom_affichage = ?
            WHERE id = ?
        """

        try:
            cursor = self._conn.cursor()
            cursor.execute(query, (
                ticket.code,
                ticket.password,
                ticket.profile_id,
                ticket.duree_session_max,
                ticket.validite,
                ticket.statut.value,
                ticket.date_generation,
                ticket.date_premiere_connexion,
                ticket.date_expiration,
                ticket.nom_affichage,
                ticket.id
            ))
            self._conn.commit()
            return cursor.rowcount > 0
        
        except sqlite3.Error as e:
            self._conn.rollback()
            raise RuntimeError(f"Erreur lors de la mise à jour du ticket : {e}")