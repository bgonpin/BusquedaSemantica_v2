#!/usr/bin/env python3
"""
Script para verificar que todas las importaciones funcionen correctamente.
"""
import sys
import os

def test_import(module_name, description):
    """Probar una importación específica."""
    try:
        __import__(module_name)
        print(f"✅ {description}")
        return True
    except ImportError as e:
        print(f"❌ {description}: {e}")
        return False

def main():
    """Verificar todas las importaciones necesarias."""
    print("🔍 Verificando importaciones...")

    imports_to_test = [
        ("pymongo", "PyMongo"),
        ("langchain", "LangChain"),
        ("langchain_ollama", "LangChain Ollama"),
        ("PySide6.QtWidgets", "PySide6"),
        ("dotenv", "Python Dotenv"),
        ("torch", "PyTorch"),
        ("numpy", "NumPy"),
        ("pydantic", "Pydantic"),
    ]

    failed_imports = []

    for module, description in imports_to_test:
        if not test_import(module, description):
            failed_imports.append(description)

    if failed_imports:
        print(f"\n❌ Importaciones fallidas: {', '.join(failed_imports)}")
        print("\n💡 Instala las dependencias faltantes:")
        print("pip install -r requirements.txt")
        return 1
    else:
        print("\n✅ Todas las importaciones funcionan correctamente")
        return 0

if __name__ == "__main__":
    sys.exit(main())