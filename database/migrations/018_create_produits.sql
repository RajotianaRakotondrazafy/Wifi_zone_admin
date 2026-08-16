-- 018 : gestion de stock du multiservice (produits et ventes de produits)

CREATE TABLE IF NOT EXISTS produits (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    nom           TEXT    NOT NULL,
    categorie     TEXT    NOT NULL,
    prix_unitaire REAL,                -- NULL / 0 → prix variable saisi à la vente
    actif         INTEGER NOT NULL DEFAULT 1,
    created_at    TEXT    NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS ventes_produits (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    produit_id       INTEGER NOT NULL REFERENCES produits(id),
    quantite         INTEGER NOT NULL DEFAULT 1,
    prix_unitaire    REAL    NOT NULL,
    montant          REAL    NOT NULL,
    methode_paiement TEXT    NOT NULL DEFAULT 'especes',
    date_vente       TEXT    NOT NULL DEFAULT CURRENT_TIMESTAMP,
    user_id          INTEGER REFERENCES users(id),
    annule           INTEGER NOT NULL DEFAULT 0,
    date_annulation  TEXT
);

CREATE INDEX IF NOT EXISTS idx_ventes_produits_date ON ventes_produits(date_vente);
