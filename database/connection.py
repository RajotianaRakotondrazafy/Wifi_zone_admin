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

    def get_connection(self) -> sqlite3.Connection:
        if self._connection is None:
            os.makedirs(os.path.dirname(DATABASE_PATH), exist_ok=True)

            self._connection = sqlite3.connect(
                DATABASE_PATH,
                check_same_thread=False,  # thread-safe via locking applicatif
            )

            self._connection.row_factory = sqlite3.Row

            self._connection.execute("PRAGMA foreign_keys = ON")

        return self._connection

    def close(self) -> None:
        if self._connection is not None:
            self._connection.close()
            self._connection = None
