import sqlite3
import os
from config.settings import DATABASE_PATH

class DatabaseConnection:
    _instance: "DatabaseConnection | None" = None
    _connection: "sqlite3.Connection | None" = None

    def __new__(cls) -> "DatabaseConnection":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    @classmethod
    def get_connection(cls) -> sqlite3.Connection:
        if cls._connection is None:
            os.makedirs(os.path.dirname(DATABASE_PATH), exist_ok=True)

            cls._connection = sqlite3.connect(
                DATABASE_PATH,
                check_same_thread=False,  # thread-safe via locking applicatif
            )

            cls._connection.row_factory = sqlite3.Row

            cls._connection.execute("PRAGMA foreign_keys = ON")

        return cls._connection

    def close(self) -> None:
        if self._connection is not None:
            self._connection.close()
            self._connection = None
