from app import create_app

app = create_app()

if __name__ == '__main__':
    try:
        print("ATTENTION: Serveur en mode HTTPS. Utilisez https:// et acceptez l'avertissement de sécurité.")
        app.run(debug=True, host='0.0.0.0', port=5000, ssl_context='adhoc')
    except Exception as e:
        print(f"Erreur démarrage HTTPS: {e}. Retour au mode HTTP.")
        app.run(debug=True, host='0.0.0.0', port=5000)
