-- Table des appareils bloqués (blocages persistants du hotspot)
CREATE TABLE IF NOT EXISTS blocages (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    -- Adresse MAC de l'appareil bloqué (unique parmi les blocages actifs)
    mac_address  TEXT    NOT NULL,
    -- Nom affiché (hostname ou code de ticket)
    nom          TEXT    NOT NULL DEFAULT 'Appareil inconnu',
    -- Adresse IP au moment du blocage
    ip_assignee  TEXT    NOT NULL DEFAULT '',
    -- Motif du blocage
    raison       TEXT    NOT NULL DEFAULT 'Bloqué manuellement',
    -- Horodatage ISO 8601 du blocage
    date_blocage TEXT    NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_blocages_mac ON blocages (mac_address);
