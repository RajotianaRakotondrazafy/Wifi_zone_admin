-- Table des comptes utilisateurs de l'interface d'administration
-- Correspond au modèle models/user.py (classe User)

CREATE TABLE IF NOT EXISTS users (
    id                INTEGER PRIMARY KEY AUTOINCREMENT,
    nom               TEXT NOT NULL,
    -- Identifiant de connexion unique
    login             TEXT NOT NULL UNIQUE,
    -- Hash bcrypt (ou argon2) — jamais le mot de passe en clair
    mot_de_passe_hash TEXT NOT NULL,
    -- Rôles disponibles : 'admin', 'caissier'
    role              TEXT NOT NULL DEFAULT 'caissier'
);
