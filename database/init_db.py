from database.connection import DatabaseConnection
from database.migration_runner import MigrationRunner


def initialiser_base() -> None:
    DatabaseConnection().get_connection()
    MigrationRunner().run()


if __name__ == "__main__":
    initialiser_base()
