-- 020 : gestion des dépenses

CREATE TABLE IF NOT EXISTS depenses (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    montant          REAL    NOT NULL,
    motif            TEXT    NOT NULL,
    categorie        TEXT    NOT NULL DEFAULT 'autre',
    methode_paiement TEXT    NOT NULL DEFAULT 'especes',
    date_depense     TEXT    NOT NULL DEFAULT CURRENT_TIMESTAMP,
    user_id          INTEGER REFERENCES users(id),
    annule           INTEGER NOT NULL DEFAULT 0,
    date_annulation  TEXT
);

CREATE INDEX IF NOT EXISTS idx_depenses_date ON depenses(date_depense);