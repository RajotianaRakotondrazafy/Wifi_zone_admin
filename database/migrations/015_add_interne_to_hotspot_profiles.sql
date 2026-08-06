ALTER TABLE hotspot_profiles ADD COLUMN interne INTEGER NOT NULL DEFAULT 0;
-- Les profils à prix=0 sont ceux créés automatiquement lors des ventes (Perso/Libre/Forfait)
UPDATE hotspot_profiles SET interne = 1 WHERE prix = 0;
