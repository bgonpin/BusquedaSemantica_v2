#!/usr/bin/env python3
"""
Script para inicializar los índices de texto necesarios para búsquedas en MongoDB.
"""
import os
import sys
from dotenv import load_dotenv

# Añadir el directorio raíz al path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.database import DatabaseManager

def setup_text_indexes():
    """Configurar índices de texto para búsquedas."""
    print("🔧 Configurando índices de texto para búsquedas en MongoDB...")

    try:
        # Inicializar DatabaseManager
        db_manager = DatabaseManager()
        print(f"✅ Conectado a MongoDB: {db_manager.database.name}.{db_manager.collection.name}")

        # Forzar la creación de índices de texto
        db_manager._ensure_text_indexes()

        # Verificar que los índices se crearon correctamente
        indexes = list(db_manager.collection.list_indexes())
        text_indexes = [idx for idx in indexes if 'text_search_index' in idx.get('name', '')]

        if text_indexes:
            print("✅ Índice de texto creado exitosamente:")
            for idx in text_indexes:
                print(f"   • Nombre: {idx['name']}")
                print(f"   • Campos: {idx.get('key', {})}")
        else:
            print("⚠️ No se encontró el índice de texto")

        print("🎉 Configuración de índices completada!")
        print("💡 Ahora las búsquedas de texto deberían funcionar correctamente")

    except Exception as e:
        print(f"❌ Error al configurar índices: {str(e)}")
        return False

    finally:
        # Cerrar conexión
        if 'db_manager' in locals():
            db_manager.cerrar_conexion()

    return True

if __name__ == "__main__":
    success = setup_text_indexes()
    sys.exit(0 if success else 1)