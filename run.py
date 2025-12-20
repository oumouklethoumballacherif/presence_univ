from app import create_app

app = create_app()

import os

# ... (rest of imports)

if __name__ == '__main__':
    debug_mode = os.environ.get('FLASK_DEBUG', '0') == '1'
    try:
        print("Serveur en mode HTTP (Plus simple).")
        app.run(debug=debug_mode, host='0.0.0.0', port=5000)
    except Exception as e:
        print(f"Erreur démarrage HTTPS: {e}. Retour au mode HTTP.")
        app.run(debug=debug_mode, host='0.0.0.0', port=5000)
