CREATE TABLE IF NOT EXISTS parametres (
    cle   TEXT PRIMARY KEY,
    valeur TEXT NOT NULL
);

INSERT OR IGNORE INTO parametres (cle, valeur) VALUES
    ('tarif_prix_par_heure',    '1000'),
    ('tarif_debit_defaut_mbps', '2'),
    ('tarif_libre_min_ar',      '500'),
    ('tarif_libre_min_min',     '30'),
    ('app_refresh_interval_s',  '60');
