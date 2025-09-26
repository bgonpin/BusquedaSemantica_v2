#!/usr/bin/env python3
"""
Script de instalación automática para Búsqueda Semántica V2.

Este script verifica y configura automáticamente el entorno para la aplicación.

Uso:
    python install.py

Autor: Búsqueda Semántica V2
"""
import os
import sys
import subprocess
import platform
from pathlib import Path


def run_command(command, description=""):
    """Ejecutar un comando del sistema."""
    print(f"🔧 {description}")
    print(f"   Ejecutando: {command}")

    try:
        result = subprocess.run(command, shell=True, check=True, capture_output=True, text=True)
        print(f"   ✅ {description} completado exitosamente")
        return True
    except subprocess.CalledProcessError as e:
        print(f"   ❌ Error en {description}: {e}")
        print(f"   Error: {e.stderr}")
        return False


def check_conda():
    """Verificar si conda está disponible."""
    print("\n📦 Verificando Conda...")

    try:
        result = subprocess.run("conda --version", shell=True, capture_output=True, text=True)
        if result.returncode == 0:
            print(f"   ✅ Conda encontrado: {result.stdout.strip()}")
            return True
        else:
            print("   ❌ Conda no encontrado")
            return False
    except Exception as e:
        print(f"   ❌ Error al verificar Conda: {e}")
        return False


def create_conda_env():
    """Crear entorno conda."""
    print("\n🏗️  Creando entorno Conda...")

    commands = [
        ("conda create -n busqueda_semantica_v2 python=3.11 -y", "Creando entorno Python 3.11"),
        ("conda activate busqueda_semantica_v2", "Activando entorno"),
    ]

    for command, description in commands:
        if not run_command(command, description):
            return False

    return True


def install_dependencies():
    """Instalar dependencias."""
    print("\n📚 Instalando dependencias...")

    # Lista de dependencias
    dependencies = [
        "langchain",
        "langchain-community",
        "langchain-ollama",
        "pymongo",
        "pyside6",
        "python-dotenv",
        "sentence-transformers",
        "torch",
        "numpy",
        "pydantic",
        "requests"
    ]

    # Instalar dependencias
    pip_command = "pip install " + " ".join(dependencies)
    return run_command(pip_command, "Instalando dependencias Python")


def check_mongodb():
    """Verificar MongoDB."""
    print("\n🍃 Verificando MongoDB...")

    try:
        # Intentar conectar a MongoDB
        result = subprocess.run("mongosh --eval 'db.runCommand(\"ping\")' --quiet", shell=True, capture_output=True, text=True)

        if result.returncode == 0:
            print("   ✅ MongoDB está ejecutándose")
            return True
        else:
            print("   ⚠️  MongoDB no está ejecutándose o no es accesible")
            print("   💡 Para iniciar MongoDB:")
            print("      - Linux: sudo systemctl start mongod")
            print("      - macOS: brew services start mongodb-community")
            print("      - Windows: net start MongoDB")
            return False
    except Exception as e:
        print(f"   ❌ Error al verificar MongoDB: {e}")
        return False


def check_ollama():
    """Verificar Ollama."""
    print("\n🤖 Verificando Ollama...")

    try:
        result = subprocess.run("ollama --version", shell=True, capture_output=True, text=True)

        if result.returncode == 0:
            print(f"   ✅ Ollama encontrado: {result.stdout.strip()}")

            # Verificar modelos disponibles
            models_result = subprocess.run("ollama list", shell=True, capture_output=True, text=True)

            if models_result.returncode == 0:
                models = models_result.stdout.strip()
                if models and "NAME" in models:
                    print("   ✅ Modelos instalados:")
                    for line in models.split('\n')[1:]:  # Saltar la línea de encabezado
                        if line.strip():
                            print(f"      - {line}")
                else:
                    print("   ⚠️  No hay modelos instalados")
                    print("   💡 Instale modelos recomendados:")
                    print("      ollama pull qwen3:14b_40K")
                    print("      ollama pull all-MiniLM-L6-v2")
            else:
                print("   ⚠️  No se pudo verificar la lista de modelos")

            return True
        else:
            print("   ❌ Ollama no encontrado")
            print("   💡 Instale Ollama desde: https://ollama.ai/")
            return False
    except Exception as e:
        print(f"   ❌ Error al verificar Ollama: {e}")
        return False


def create_config_file():
    """Crear archivo de configuración."""
    print("\n⚙️  Creando archivo de configuración...")

    config_dir = Path("config")
    config_dir.mkdir(exist_ok=True)

    config_file = config_dir / ".env"

    if config_file.exists():
        print("   ✅ Archivo de configuración ya existe")
        return True

    config_content = """# Configuración de MongoDB
MONGODB_URI=mongodb://localhost:27017/
MONGODB_DATABASE=album
MONGODB_COLLECTION=imagenes_2

# Configuración de Ollama
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=qwen3:14b_40K

# Configuración de la aplicación
DEBUG=True
LOG_LEVEL=INFO
"""

    try:
        with open(config_file, 'w', encoding='utf-8') as f:
            f.write(config_content)
        print("   ✅ Archivo de configuración creado")
        return True
    except Exception as e:
        print(f"   ❌ Error al crear archivo de configuración: {e}")
        return False


def create_startup_script():
    """Crear script de inicio."""
    print("\n🚀 Creando script de inicio...")

    startup_content = """#!/bin/bash
# Script de inicio para Búsqueda Semántica V2

echo "=== Iniciando Búsqueda Semántica V2 ==="

# Verificar si conda está disponible
if ! command -v conda &> /dev/null; then
    echo "❌ Conda no encontrado. Instale Anaconda o Miniconda."
    exit 1
fi

# Activar entorno
echo "🔧 Activando entorno conda..."
conda activate busqueda_semantica_v2

if [ $? -ne 0 ]; then
    echo "❌ Error al activar entorno conda"
    exit 1
fi

# Verificar dependencias
echo "📦 Verificando dependencias..."
python -c "import pymongo, langchain, PySide6; print('✅ Todas las dependencias están disponibles')"

if [ $? -ne 0 ]; then
    echo "❌ Faltan dependencias. Ejecute install.py primero."
    exit 1
fi

# Iniciar aplicación
echo "🎯 Iniciando aplicación..."
python main.py
"""

    try:
        with open("start.sh", 'w', encoding='utf-8') as f:
            f.write(startup_content)

        # Hacer ejecutable en Unix
        if platform.system() != "Windows":
            os.chmod("start.sh", 0o755)

        print("   ✅ Script de inicio creado")
        return True
    except Exception as e:
        print(f"   ❌ Error al crear script de inicio: {e}")
        return False


def main():
    """Función principal del script de instalación."""
    print("🚀 Instalador de Búsqueda Semántica V2")
    print("=" * 50)

    # Verificar si ya está instalado
    if Path("config/.env").exists() and Path("main.py").exists():
        print("📁 Proyecto ya configurado encontrado")

        response = input("¿Desea reinstalar? (y/N): ").lower().strip()
        if response != 'y':
            print("✅ Instalación cancelada")
            return

    # Verificar conda
    if not check_conda():
        print("❌ Conda es requerido para continuar")
        print("💡 Instale Anaconda o Miniconda desde: https://www.anaconda.com/")
        sys.exit(1)

    # Crear entorno conda
    if not create_conda_env():
        print("❌ Error al crear entorno conda")
        sys.exit(1)

    # Instalar dependencias
    if not install_dependencies():
        print("❌ Error al instalar dependencias")
        sys.exit(1)

    # Verificar servicios externos
    check_mongodb()
    check_ollama()

    # Crear archivos de configuración
    if not create_config_file():
        print("❌ Error al crear configuración")
        sys.exit(1)

    # Crear script de inicio
    if not create_startup_script():
        print("❌ Error al crear script de inicio")
        sys.exit(1)

    print("\n🎉 ¡Instalación completada exitosamente!")
    print("\n📋 Próximos pasos:")
    print("1. Asegúrese de que MongoDB esté ejecutándose")
    print("2. Inicie Ollama: ollama serve")
    print("3. Instale modelos: ollama pull qwen3:14b_40K")
    print("4. Ejecute la aplicación: python main.py")
    print("   O use el script: ./start.sh (en Linux/macOS)")


if __name__ == "__main__":
    main()