import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parent.parent))
 
import bcrypt
 
from database.connection import DatabaseConnection
from database.init_db import initialiser_base
from models.user import User, RoleUtilisateur
from repositories.user_repository import UserRepository
 
 
def creer_ou_mettre_a_jour_admin(login: str, mot_de_passe_clair: str, nom: str = "Administrateur"):
    DatabaseConnection()
    initialiser_base()
 
    UserRepo = UserRepository()
 
    hash_mdp = bcrypt.hashpw(mot_de_passe_clair.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
 
    utilisateur_existant = UserRepo.get_by_login(login)
 
    if utilisateur_existant:
        utilisateur_existant.mot_de_passe_hash = hash_mdp
        UserRepo.update(utilisateur_existant)
        print(f"Mot de passe mis à jour pour l'utilisateur '{login}'.")
    else:
        nouvel_admin = User(
            nom=nom,
            login=login,
            mot_de_passe_hash=hash_mdp,
            role=RoleUtilisateur.ADMIN,
        )
        UserRepo.create_user(nouvel_admin)
        print(f"Utilisateur admin '{login}' créé avec succès.")
 
 
if __name__ == "__main__":
    LOGIN = "admin@wifizone.mg"
    MOT_DE_PASSE = "admin123" 
 
    creer_ou_mettre_a_jour_admin(LOGIN, MOT_DE_PASSE)