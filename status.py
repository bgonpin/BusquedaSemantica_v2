#!/usr/bin/env python3
"""
Script para verificar el estado de la aplicación Búsqueda Semántica V2.

Este script proporciona información detallada sobre:
- Estado de los servicios (MongoDB, Ollama)
- Configuración de la aplicación
- Estado de la base de datos
- Modelos disponibles

Uso:
    python status.py

Autor: Búsqueda Semántica V2
"""
import os
import sys
from pathlib import Path
from dotenv import load_dotenv

def load_configuration():
    """Cargar configuración."""
    dotenv_path = Path(__file__).parent / "config" / ".env"
    load_dotenv(dotenv_path=dotenv_path)

def check_mongodb_status():
    """Verificar estado de MongoDB."""
    print("🍃 Estado de MongoDB:")
    print("-" * 30)

    try:
        from pymongo import MongoClient

        mongodb_uri = os.getenv('MONGODB_URI', 'mongodb://localhost:27017/')
        database_name = os.getenv('MONGODB_DATABASE', 'album')
        collection_name = os.getenv('MONGODB_COLLECTION', 'imagenes_2')

        client = MongoClient(mongodb_uri, serverSelectionTimeoutMS=5000)
        client.admin.command('ping')

        db = client[database_name]
        collection = db[collection_name]

        # Obtener estadísticas
        total_docs = collection.count_documents({})
        docs_procesados = collection.count_documents({"objeto_procesado": True})
        docs_con_embedding = collection.count_documents({"embedding": {"$exists": True}})

        print(f"   ✅ Conectado: {mongodb_uri}")
        print(f"   📊 Base de datos: {database_name}")
        print(f"   📁 Colección: {collection_name}")
        print(f"   📈 Total documentos: {total_docs:,}")
        print(f"   ✅ Procesados: {docs_procesados:,}")
        print(f"   🔢 Con embeddings: {docs_con_embedding:,}")

        # Verificar índices
        indexes = list(collection.list_indexes())
        text_indexes = [idx for idx in indexes if 'text' in str(idx.get('key', {}))]
        print(f"   📋 Índices de texto: {len(text_indexes)}")

        client.close()
        return True

    except Exception as e:
        print(f"   ❌ Error: {e}")
        return False

def check_ollama_status():
    """Verificar estado de Ollama."""
    print("\n🤖 Estado de Ollama:")
    print("-" * 30)

    try:
        import requests

        ollama_url = os.getenv('OLLAMA_BASE_URL', 'http://localhost:11434')
        ollama_model = os.getenv('OLLAMA_MODEL', 'qwen3:14b_40K')

        # Verificar conexión
        response = requests.get(f"{ollama_url}/api/tags", timeout=5)

        if response.status_code == 200:
            models = response.json().get('models', [])
            print(f"   ✅ Conectado: {ollama_url}")
            print(f"   🤖 Modelo configurado: {ollama_model}")
            print(f"   📋 Modelos disponibles: {len(models)}")

            # Buscar modelo específico
            model_found = any(model.get('name') == ollama_model for model in models)
            if model_found:
                print(f"   ✅ Modelo '{ollama_model}' instalado")
            else:
                print(f"   ⚠️  Modelo '{ollama_model}' no encontrado")
                print("   💡 Instale el modelo: ollama pull " + ollama_model)

            return True
        else:
            print(f"   ❌ Error HTTP {response.status_code}")
            return False

    except requests.exceptions.RequestException as e:
        print(f"   ❌ Error de conexión: {e}")
        return False
    except Exception as e:
        print(f"   ❌ Error: {e}")
        return False

def check_environment():
    """Verificar variables de entorno."""
    print("\n⚙️  Configuración:")
    print("-" * 30)

    config_file = Path("config/.env")
    if config_file.exists():
        print("   ✅ Archivo de configuración encontrado")
    else:
        print("   ❌ Archivo de configuración no encontrado")
        return False

    # Verificar variables críticas
    critical_vars = {
        'MONGODB_URI': 'URI de MongoDB',
        'MONGODB_DATABASE': 'Base de datos',
        'MONGODB_COLLECTION': 'Colección',
        'OLLAMA_BASE_URL': 'URL de Ollama',
        'OLLAMA_MODEL': 'Modelo de Ollama'
    }

    all_vars_ok = True
    for var, description in critical_vars.items():
        value = os.getenv(var)
        if value:
            print(f"   ✅ {description}: {value}")
        else:
            print(f"   ❌ {description}: No definida")
            all_vars_ok = False

    return all_vars_ok

def check_dependencies():
    """Verificar dependencias."""
    print("\n📦 Dependencias:")
    print("-" * 30)

    dependencies = [
        ("pymongo", "PyMongo"),
        ("langchain", "LangChain"),
        ("langchain_ollama", "LangChain Ollama"),
        ("PySide6", "PySide6"),
        ("dotenv", "Python Dotenv"),
        ("torch", "PyTorch"),
        ("numpy", "NumPy")
    ]

    all_deps_ok = True
    for module, name in dependencies:
        try:
            __import__(module)
            print(f"   ✅ {name}")
        except ImportError:
            print(f"   ❌ {name}")
            all_deps_ok = False

    return all_deps_ok

def show_system_info():
    """Mostrar información del sistema."""
    print("\n💻 Información del Sistema:")
    print("-" * 30)

    try:
        import platform
        print(f"   🖥️  Sistema: {platform.system()} {platform.release()}")
        print(f"   🐍 Python: {platform.python_version()}")

        # Verificar CUDA
        try:
            import torch
            if torch.cuda.is_available():
                print(f"   🟢 CUDA: Disponible ({torch.cuda.get_device_name(0)})")
            else:
                print("   🟡 CUDA: No disponible (usando CPU)")
        except:
            print("   ⚪ CUDA: No se pudo verificar")

    except Exception as e:
        print(f"   ❌ Error al obtener info del sistema: {e}")

def main():
    """Función principal."""
    print("🔍 Estado de Búsqueda Semántica V2")
    print("=" * 50)

    load_configuration()

    # Verificaciones
    env_ok = check_environment()
    deps_ok = check_dependencies()
    mongodb_ok = check_mongodb_status()
    ollama_ok = check_ollama_status()
    show_system_info()

    # Resumen
    print("\n" + "=" * 50)
    print("📊 RESUMEN")
    print("=" * 50)

    status_items = [
        ("Variables de entorno", env_ok, "Verificar config/.env"),
        ("Dependencias", deps_ok, "Ejecutar: pip install -r requirements.txt"),
        ("MongoDB", mongodb_ok, "Ejecutar: python setup_mongodb.py"),
        ("Ollama", ollama_ok, "Ejecutar: ollama serve")
    ]

    all_ok = True
    for item, status, suggestion in status_items:
        if status:
            print(f"✅ {item}")
        else:
            print(f"❌ {item}")
            print(f"   💡 {suggestion}")
            all_ok = False

    print("\n" + "=" * 50)
    if all_ok:
        print("🎉 ¡Todos los componentes están funcionando!")
        print("\n🚀 Puede ejecutar la aplicación:")
        print("   python main.py")
    else:
        print("⚠️  Algunos componentes necesitan atención.")
        print("\n🔧 Revise los errores mostrados arriba.")

    return 0 if all_ok else 1

if __name__ == "__main__":
    sys.exit(main())