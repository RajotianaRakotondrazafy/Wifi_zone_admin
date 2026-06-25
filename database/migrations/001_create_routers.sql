CREATE TABLE IF NOT EXISTS routers (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    nom              TEXT    NOT NULL,
    adresse_ip       TEXT    NOT NULL,
    port_api         INTEGER NOT NULL,
    username         TEXT    NOT NULL,
    password_chiffre TEXT    NOT NULL,
    -- Valeurs possibles : 'actif', 'inactif', 'erreur'
    statut           TEXT    NOT NULL DEFAULT 'inactif'
);
