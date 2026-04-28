import os
import subprocess
import sys

def main():
    # Définition des chemins
    base_dir = os.path.dirname(os.path.abspath(__file__))
    venv_dir = os.path.join(base_dir, ".venv")
    requirements_file = os.path.join(base_dir, "requirements.txt")

    print("🚀 Initialisation du projet Kompagnon Algo...")

    # 1. Créer l'environnement virtuel s'il n'existe pas
    if not os.path.exists(venv_dir):
        print("📦 Création de l'environnement virtuel (.venv)...")
        subprocess.run([sys.executable, "-m", "venv", ".venv"], check=True)
    else:
        print("✅ L'environnement virtuel est déjà présent.")

    # Définition des chemins vers les exécutables selon le système d'exploitation
    if os.name == 'nt':  # Windows
        pip_exe = os.path.join(venv_dir, "Scripts", "pip")
        python_exe = os.path.join(venv_dir, "Scripts", "python")
    else:                # macOS / Linux
        pip_exe = os.path.join(venv_dir, "bin", "pip")
        python_exe = os.path.join(venv_dir, "bin", "python")

    # 2. Mise à jour de pip et installation des dépendances
    print("🔄 Installation/Mise à jour des dépendances...")
    subprocess.run([pip_exe, "install", "--upgrade", "pip", "-q"], check=True)
    if os.path.exists(requirements_file):
        subprocess.run([pip_exe, "install", "-r", "requirements.txt", "-q"], check=True)
        print("✅ Dépendances vérifiées et installées.")
    else:
        print("⚠️ Attention : fichier requirements.txt introuvable !")

    # 3. Lancer l'API
    print("🌟 Lancement de l'API FastAPI...")
    try:
        # On lance Uvicorn en tant que module depuis la racine du projet
        # Cela permet à Python de comprendre les imports de type 'from src.api...'
        subprocess.run(
            [python_exe, "-m", "uvicorn", "src.api.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"],
            cwd=base_dir,
            check=True
        )
    except KeyboardInterrupt:
        print("\n🛑 Arrêt manuel du serveur.")
    except subprocess.CalledProcessError as e:
        print(f"\n❌ Le serveur s'est arrêté avec une erreur : {e}")
    except Exception as e:
        print(f"\n❌ Erreur inattendue : {e}")

if __name__ == "__main__":
    main()
