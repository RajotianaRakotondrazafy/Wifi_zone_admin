-- Ajoute le nom d'hôte DHCP (nom d'appareil) aux sessions enregistrées
ALTER TABLE sessions ADD COLUMN nom_hote TEXT;
