-- Table des transactions de vente de tickets WiFi
-- Correspond au modèle models/sale.py (classe Sale)
-- NOTE : user_id référence users(id) créée en migration 006 — les FK SQLite
--        ne sont vérifiées qu'à l'insertion, pas à la création de table.

CREATE TABLE IF NOT EXISTS sales (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    -- Ticket vendu lors de cette transaction
    ticket_id        INTEGER NOT NULL,
    -- Caissier ayant réalisé la vente
    user_id          INTEGER NOT NULL,
    -- Montant encaissé en unité monétaire locale
    montant          REAL    NOT NULL,
    -- Horodatage ISO 8601 de la transaction
    date_vente       TEXT    NOT NULL,
    -- Ex : 'especes', 'mobile_money', 'carte'
    methode_paiement TEXT    NOT NULL,

    FOREIGN KEY (ticket_id) REFERENCES tickets(id),
    FOREIGN KEY (user_id)   REFERENCES users(id)
);
