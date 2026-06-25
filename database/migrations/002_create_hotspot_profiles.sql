CREATE TABLE IF NOT EXISTS hotspot_profiles (
    id                INTEGER PRIMARY KEY AUTOINCREMENT,
    -- Routeur MikroTik qui héberge ce profil
    router_id         INTEGER NOT NULL,
    nom               TEXT    NOT NULL,
    -- Débit maximum alloué en kbps
    debit_max         INTEGER NOT NULL,
    -- Durée maximale d'une session en minutes
    duree_session_max INTEGER NOT NULL,
    -- Validité du ticket en heures après la première connexion
    validite          INTEGER NOT NULL,
    -- Prix de vente en unité monétaire locale (Ariary, etc.)
    prix              REAL    NOT NULL,

    FOREIGN KEY (router_id) REFERENCES routers(id)
);
