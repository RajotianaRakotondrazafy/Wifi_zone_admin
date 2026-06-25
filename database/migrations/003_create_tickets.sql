CREATE TABLE IF NOT EXISTS tickets (
    id                      INTEGER PRIMARY KEY AUTOINCREMENT,
    -- Code imprimé sur le ticket, saisi par le client dans le portail hotspot
    code                    TEXT    NOT NULL UNIQUE,
    -- Mot de passe MikroTik associé au code
    password                TEXT    NOT NULL,
    -- Profil hotspot qui définit les limites de ce ticket
    profile_id              INTEGER NOT NULL,
    -- Cycle de vie : 'non_utilise', 'actif', 'expire', 'epuise'
    statut                  TEXT    NOT NULL DEFAULT 'non_utilise',
    -- Horodatage de création du ticket (ISO 8601)
    date_generation         TEXT             DEFAULT CURRENT_TIMESTAMP,
    -- Renseignée lors de la première authentification client
    date_premiere_connexion TEXT,
    -- Calculée : date_premiere_connexion + validite (en heures) du profil
    date_expiration         TEXT,

    FOREIGN KEY (profile_id) REFERENCES hotspot_profiles(id)
);
