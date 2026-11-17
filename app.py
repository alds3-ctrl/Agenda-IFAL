import os

from dotenv import load_dotenv

load_dotenv()

from agenda import create_app

app = create_app()


if __name__ == "__main__":
    host = os.environ.get("HOST", "0.0.0.0")
    port = int(os.environ.get("PORT", "5000"))
    debug = os.environ.get("FLASK_DEBUG", "0") == "1"
    print("\nAgenda IFAL iniciado.")
    print(f"Acesso neste computador: http://127.0.0.1:{port}")
    print(f"Acesso pela rede local: http://IP-DO-COMPUTADOR:{port}\n")
    app.run(host=host, port=port, debug=debug)
