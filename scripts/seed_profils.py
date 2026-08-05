import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from database.connection import DatabaseConnection

conn = DatabaseConnection().get_connection()

# Routeur par défaut
conn.execute(
    "INSERT INTO routers (nom, adresse_ip, port_api, username, password_chiffre, statut) VALUES (?, ?, ?, ?, ?, ?)",
    ("Routeur Principal", "192.168.1.1", 8728, "admin", "", "actif"),
)

# 3 profils vitesse (prix = 0 car le prix est calculé sur le ticket)
conn.execute(
    "INSERT INTO hotspot_profiles (router_id, nom, debit_max, duree_session_max, validite, prix) VALUES (1, ?, 2048, 60, 24, 0)",
    ("2 Mbps",),
)
conn.execute(
    "INSERT INTO hotspot_profiles (router_id, nom, debit_max, duree_session_max, validite, prix) VALUES (1, ?, 5120, 60, 24, 0)",
    ("5 Mbps",),
)
conn.execute(
    "INSERT INTO hotspot_profiles (router_id, nom, debit_max, duree_session_max, validite, prix) VALUES (1, ?, 10240, 60, 24, 0)",
    ("10 Mbps",),
)

conn.commit()
print("Seed OK : 1 routeur + 3 profils vitesse créés")
