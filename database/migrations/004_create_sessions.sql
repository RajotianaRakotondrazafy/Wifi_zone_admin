-- Table des sessions de connexion hotspot des clients
-- Correspond au modèle models/session.py (classe Session)

CREATE TABLE IF NOT EXISTS sessions (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    -- Ticket utilisé pour ouvrir cette session
    ticket_id       INTEGER NOT NULL,
    -- Adresse MAC de l'appareil client (identifiant réseau unique)
    mac_address     TEXT    NOT NULL,
    -- Adresse IP attribuée par le DHCP du hotspot MikroTik
    ip_assignee     TEXT    NOT NULL,
    -- Horodatages ISO 8601
    date_debut      TEXT    NOT NULL,
    date_fin        TEXT,
    -- Volume de données en octets (sens montant : client → internet)
    octets_envoyes  INTEGER NOT NULL DEFAULT 0,
    -- Volume de données en octets (sens descendant : internet → client)
    octets_recus    INTEGER NOT NULL DEFAULT 0,
    -- Durée effective de la session en secondes
    duree_reelle    INTEGER,

    FOREIGN KEY (ticket_id) REFERENCES tickets(id)
);
