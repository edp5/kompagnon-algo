import os
import subprocess
import sys

def main():
    # Define paths
    base_dir = os.path.dirname(os.path.abspath(__file__))
    venv_dir = os.path.join(base_dir, ".venv")
    requirements_file = os.path.join(base_dir, "requirements.txt")

    print("🚀 Initializing Kompagnon Algo project...")

    # 1. Create virtual environment if not exists
    if not os.path.exists(venv_dir):
        print("📦 Creating virtual environment (.venv)...")
        subprocess.run([sys.executable, "-m", "venv", ".venv"], check=True)
    else:
        print("✅ Virtual environment already exists.")

    # Define paths to executables based on operating system
    if os.name == 'nt':  # Windows
        pip_exe = os.path.join(venv_dir, "Scripts", "pip")
        python_exe = os.path.join(venv_dir, "Scripts", "python")
    else:                # macOS / Linux
        pip_exe = os.path.join(venv_dir, "bin", "pip")
        python_exe = os.path.join(venv_dir, "bin", "python")

    # 2. Upgrade pip and install dependencies
    print("🔄 Installing/Upgrading dependencies...")
    subprocess.run([pip_exe, "install", "--upgrade", "pip", "-q"], check=True)
    if os.path.exists(requirements_file):
        subprocess.run([pip_exe, "install", "-r", "requirements.txt", "-q"], check=True)
        print("✅ Dependencies verified and installed.")
    else:
        print("⚠️ Warning: requirements.txt file not found!")

    # 3. Start API
    print("🌟 Starting FastAPI server...")
    try:
        subprocess.run(
            [python_exe, "-m", "uvicorn", "src.api.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"],
            cwd=base_dir,
            check=True
        )
    except KeyboardInterrupt:
        print("\n🛑 Server stopped manually.")
    except subprocess.CalledProcessError as e:
        print(f"\n❌ Server stopped with an error: {e}")
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")

if __name__ == "__main__":
    main()
