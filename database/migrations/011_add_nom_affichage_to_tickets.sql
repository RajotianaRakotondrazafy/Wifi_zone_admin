-- Nom d'affichage du ticket (ex. "Perso 10 Mbps" pour un ticket personnalisé)
-- NULL → la liste retombe sur le nom du profil associé (hp.nom)

ALTER TABLE tickets ADD COLUMN nom_affichage TEXT;
