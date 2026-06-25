import os
import glob
import sqlite3

from database.connection import DatabaseConnection

class MigrationRunner:
    _MIGRATIONS_DIR = os.path.join(os.path.dirname(__file__), "migrations")

    def __init__(self) -> None:
        self._conn: sqlite3.Connection = DatabaseConnection().get_connection()

    def _creer_table_version(self) -> None:
        self._conn.execute("""
            CREATE TABLE IF NOT EXISTS schema_version (
                id               INTEGER PRIMARY KEY AUTOINCREMENT,
                version          INTEGER NOT NULL,
                date_application TEXT    NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
        """)
        self._conn.commit()

    def _version_actuelle(self) -> int:
        curseur = self._conn.execute("SELECT MAX(version) FROM schema_version")
        resultat = curseur.fetchone()[0]
        return resultat if resultat is not None else 0

    def _lister_migrations(self) -> list[tuple[int, str]]:
        fichiers = glob.glob(os.path.join(self._MIGRATIONS_DIR, "*.sql"))
        migrations = []
        for chemin in fichiers:
            nom = os.path.basename(chemin)
            try:
                version = int(nom.split("_")[0])
                migrations.append((version, chemin))
            except ValueError:
                print(f"[Migration] Fichier ignoré (nom invalide) : {nom}")
        return sorted(migrations, key=lambda t: t[0])

    def _appliquer(self, version: int, chemin: str) -> None:
        nom = os.path.basename(chemin)
        print(f"[Migration] Application de {nom}...")

        try:
            with open(chemin, encoding="utf-8") as f:
                sql = f.read()

            # executescript fait un COMMIT implicite avant d'exécuter le script
            self._conn.executescript(sql)

            # Enregistrement de la migration appliquée
            self._conn.execute(
                "INSERT INTO schema_version (version) VALUES (?)",
                (version,),
            )
            self._conn.commit()
            print(f"[Migration] [OK] {nom} appliquee avec succes.")

        except (sqlite3.Error, OSError) as exc:
            # Tentative de rollback (pas toujours possible après executescript)
            try:
                self._conn.rollback()
            except sqlite3.Error:
                pass
            raise RuntimeError(
                f"[Migration] ERREUR lors de l'application de {nom} : {exc}"
            ) from exc

    def run(self) -> None:
        self._creer_table_version()
        version_courante = self._version_actuelle()
        migrations = self._lister_migrations()

        en_attente = [(v, c) for v, c in migrations if v > version_courante]

        if not en_attente:
            print(
                f"[Migration] Base de données à jour (version {version_courante})."
                " Aucune migration à appliquer."
            )
            return

        print(
            f"[Migration] Version actuelle : {version_courante}."
            f" {len(en_attente)} migration(s) à appliquer."
        )

        for version, chemin in en_attente:
            self._appliquer(version, chemin)

        print(
            f"[Migration] Terminé. Nouvelle version : {self._version_actuelle()}."
        )
