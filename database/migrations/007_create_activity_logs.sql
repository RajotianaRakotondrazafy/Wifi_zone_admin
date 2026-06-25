-- Table du journal d'audit des actions utilisateurs
-- Correspond au modèle models/activity_log.py (classe ActivityLog)

CREATE TABLE IF NOT EXISTS activity_logs (
    id      INTEGER PRIMARY KEY AUTOINCREMENT,
    -- Utilisateur ayant déclenché l'action
    user_id INTEGER NOT NULL,
    -- Description courte : 'creation_ticket', 'login', 'suppression_profil', etc.
    action  TEXT    NOT NULL,
    -- Horodatage ISO 8601 de l'action
    date    TEXT    NOT NULL DEFAULT CURRENT_TIMESTAMP,
    -- Données complémentaires JSON ou texte libre (id de l'entité concernée, etc.)
    details TEXT,

    FOREIGN KEY (user_id) REFERENCES users(id)
);
