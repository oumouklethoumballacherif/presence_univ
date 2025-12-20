
import os

config_content = """class LocalConfig:
    # Secrets
    SECRET_KEY = 'uir-presence-secret-key-2024'

    # MySQL
    SQLALCHEMY_DATABASE_URI = "mysql+pymysql://PresenceUniv:Oumaima@2001@PresenceUniv.mysql.pythonanywhere-services.com/PresenceUniv$presence_univ"
    SQLALCHEMY_TRACK_MODIFICATIONS = False    

    # Email
    MAIL_USERNAME = 'balla33cherif@gmail.com' 
    MAIL_PASSWORD = 'boyf sath nlti omdb'     
    MAIL_DEFAULT_SENDER = ('UIR Présence', 'balla33cherif@gmail.com')
"""

file_path = os.path.join('app', 'config_local.py')

with open(file_path, 'w', encoding='utf-8') as f:
    f.write(config_content)

print(f"✅ Fichier créé avec succès : {file_path}")
print("Contenu :")
print(config_content)
