#!/usr/bin/env python3
"""
Script de verificación para Búsqueda Semántica V2.

Este script verifica que todos los componentes estén funcionando correctamente.

Uso:
    python test_setup.py

Autor: Búsqueda Semántica V2
"""
import sys
import os
from pathlib import Path

def test_imports():
    """Probar importaciones de módulos."""
    print("📦 Probando importaciones...")

    modules_to_test = [
        ("pymongo", "PyMongo"),
        ("langchain", "LangChain"),
        ("langchain_ollama", "LangChain Ollama"),
        ("PySide6.QtWidgets", "PySide6"),
        ("dotenv", "Python Dotenv"),
        ("torch", "PyTorch"),
        ("numpy", "NumPy"),
    ]

    failed_imports = []

    for module, name in modules_to_test:
        try:
            __import__(module)
            print(f"   ✅ {name}")
        except ImportError as e:
            print(f"   ❌ {name}: {e}")
            failed_imports.append(name)

    return len(failed_imports) == 0, failed_imports


def test_configuration():
    """Probar configuración."""
    print("\n⚙️  Verificando configuración...")

    config_file = Path("config/.env")
    if config_file.exists():
        print("   ✅ Archivo de configuración encontrado")

        # Verificar variables de entorno críticas
        critical_vars = [
            'MONGODB_URI',
            'MONGODB_DATABASE',
            'OLLAMA_BASE_URL'
        ]

        missing_vars = []
        for var in critical_vars:
            if not os.getenv(var):
                missing_vars.append(var)

        if missing_vars:
            print(f"   ⚠️  Variables de entorno faltantes: {', '.join(missing_vars)}")
            return False, missing_vars
        else:
            print("   ✅ Todas las variables de entorno críticas están definidas")
            return True, []
    else:
        print("   ❌ Archivo de configuración no encontrado")
        return False, ["config/.env"]


def test_file_structure():
    """Verificar estructura de archivos."""
    print("\n📁 Verificando estructura de archivos...")

    required_files = [
        "main.py",
        "README.md",
        "requirements.txt",
        "install.py",
        "src/__init__.py",
        "src/models.py",
        "src/database.py",
        "src/busqueda_semantica.py",
        "ui/main_window.py",
        "config/.env"
    ]

    missing_files = []

    for file_path in required_files:
        if Path(file_path).exists():
            print(f"   ✅ {file_path}")
        else:
            print(f"   ❌ {file_path}")
            missing_files.append(file_path)

    return len(missing_files) == 0, missing_files


def test_mongodb_connection():
    """Probar conexión a MongoDB."""
    print("\n🍃 Probando conexión a MongoDB...")

    try:
        from pymongo import MongoClient

        mongodb_uri = os.getenv('MONGODB_URI', 'mongodb://localhost:27017/')
        client = MongoClient(mongodb_uri, serverSelectionTimeoutMS=5000)

        # Probar conexión
        client.admin.command('ping')
        print("   ✅ Conexión a MongoDB exitosa")

        # Verificar base de datos
        db_name = os.getenv('MONGODB_DATABASE', 'album')
        db = client[db_name]
        print(f"   ✅ Base de datos '{db_name}' accesible")

        client.close()
        return True, None

    except Exception as e:
        print(f"   ❌ Error de conexión a MongoDB: {e}")
        return False, str(e)


def test_ollama_connection():
    """Probar conexión a Ollama."""
    print("\n🤖 Probando conexión a Ollama...")

    try:
        import requests

        ollama_url = os.getenv('OLLAMA_BASE_URL', 'http://localhost:11434')
        response = requests.get(f"{ollama_url}/api/tags", timeout=5)

        if response.status_code == 200:
            models = response.json().get('models', [])
            print(f"   ✅ Ollama accesible, {len(models)} modelos disponibles")

            if models:
                print("   📋 Modelos instalados:")
                for model in models[:3]:  # Mostrar primeros 3
                    print(f"      - {model.get('name', 'Unknown')}")
                if len(models) > 3:
                    print(f"      ... y {len(models) - 3} más")
            else:
                print("   ⚠️  No hay modelos instalados")

            return True, None
        else:
            print(f"   ❌ Error HTTP {response.status_code} al conectar con Ollama")
            return False, f"HTTP {response.status_code}"

    except requests.exceptions.RequestException as e:
        print(f"   ❌ Error de conexión con Ollama: {e}")
        return False, str(e)
    except Exception as e:
        print(f"   ❌ Error inesperado al probar Ollama: {e}")
        return False, str(e)


def test_embeddings():
    """Probar generación de embeddings."""
    print("\n🔢 Probando generación de embeddings...")

    try:
        from langchain_ollama import OllamaEmbeddings

        ollama_base_url = os.getenv('OLLAMA_BASE_URL', 'http://localhost:11434')
        embedding_model = os.getenv('EMBEDDING_MODEL', 'embeddinggemma')
        model = OllamaEmbeddings(base_url=ollama_base_url, model=embedding_model)

        # Probar con texto de ejemplo
        test_text = "Esto es una prueba de embeddings"
        embedding = model.encode(test_text)

        print(f"   ✅ Modelo de embeddings cargado: {model_name}")
        print(f"   ✅ Embedding generado: {len(embedding)} dimensiones")

        return True, None

    except Exception as e:
        print(f"   ❌ Error al probar embeddings: {e}")
        return False, str(e)


def main():
    """Función principal de verificación."""
    print("🧪 Verificación de Búsqueda Semántica V2")
    print("=" * 50)

    tests = [
        ("Importaciones", test_imports),
        ("Estructura de archivos", test_file_structure),
        ("Configuración", test_configuration),
        ("Conexión MongoDB", test_mongodb_connection),
        ("Conexión Ollama", test_ollama_connection),
        ("Embeddings", test_embeddings),
    ]

    results = []
    all_passed = True

    for test_name, test_func in tests:
        print(f"\n{'='*20} {test_name} {'='*20}")
        passed, error = test_func()
        results.append((test_name, passed, error))

        if not passed:
            all_passed = False

    # Resumen
    print(f"\n{'='*50}")
    print("📊 RESUMEN DE VERIFICACIÓN")
    print(f"{'='*50}")

    for test_name, passed, error in results:
        status = "✅ PASSED" if passed else "❌ FAILED"
        print(f"{test_name:<25} {status}")

        if not passed and error:
            if isinstance(error, list):
                for err in error:
                    print(f"   - {err}")
            else:
                print(f"   Error: {error}")

    print(f"\n{'='*50}")

    if all_passed:
        print("🎉 ¡Todas las verificaciones pasaron exitosamente!")
        print("\n🚀 Puede ejecutar la aplicación con:")
        print("   python main.py")
        print("   o")
        print("   ./start.sh (en Linux/macOS)")
    else:
        print("⚠️  Algunas verificaciones fallaron.")
        print("\n🔧 Para solucionar los problemas:")
        print("1. Revise los errores mostrados arriba")
        print("2. Ejecute install.py para reinstalar")
        print("3. Verifique que MongoDB y Ollama estén ejecutándose")
        print("4. Consulte el README.md para instrucciones detalladas")

    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())