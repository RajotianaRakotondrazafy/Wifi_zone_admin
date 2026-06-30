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
                code, password, profile_id, statut,
                date_generation, date_premiere_connexion, date_expiration
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
        """
        try:
            cursor = self._conn.cursor()
            cursor.execute(query, (
                ticket["code"],
                ticket["password"],
                ticket["profile_id"],
                ticket.date_generation or datetime.now(),
                ticket.date_premiere_connexion,
                ticket.date_expiration,
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
        
    
    def update_ticket(self, ticket: Ticket) -> bool:
        if ticket.id is None:
            raise ValueError("Impossible de mettre à jour un ticket sans id.")
        
        query = """
            UPDATE tickets
            SET code = ?, password = ?, profile_id = ?, statut = ?,
                date_generation = ?, date_premiere_connexion = ?, date_expiration = ?
            WHERE id = ?
        """

        try:
            cursor = self._conn.cursor()
            cursor.execute(query, (
                ticket.code,
                ticket.password,
                ticket.profile_id,
                ticket.statut.value,
                ticket.date_generation,
                ticket.date_premiere_connexion,
                ticket.date_expiration,
                ticket.id
            ))
            self._conn.commit()
            return cursor.rowcount > 0
        
        except sqlite3.Error as e:
            self._conn.rollback()
            raise RuntimeError(f"Erreur lors de la mise à jour du ticket : {e}")