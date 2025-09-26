#!/usr/bin/env python3
"""
Script para configurar índices en MongoDB para la aplicación de búsqueda semántica.

Este script crea los índices necesarios para optimizar las búsquedas:
- Índice de texto para búsquedas de texto completo
- Índice para embeddings vectoriales
- Índices compuestos para consultas frecuentes

Uso:
    python setup_mongodb.py

Autor: Búsqueda Semántica V2
"""
import os
from pymongo import MongoClient
from dotenv import load_dotenv
from pathlib import Path

def load_configuration():
    """Cargar configuración desde archivo .env."""
    dotenv_path = Path(__file__).parent / "config" / ".env"
    load_dotenv(dotenv_path=dotenv_path)

    return {
        'mongodb_uri': os.getenv('MONGODB_URI', 'mongodb://localhost:27017/'),
        'database_name': os.getenv('MONGODB_DATABASE', 'album'),
        'collection_name': os.getenv('MONGODB_COLLECTION', 'imagenes_2')
    }

def create_text_index(collection):
    """Crear índice de texto para búsquedas de texto completo."""
    print("📝 Creando índice de texto...")

    try:
        # Crear índice de texto en campos relevantes
        text_index = collection.create_index([
            ('nombre', 'text'),
            ('descripcion_semantica', 'text'),
            ('objetos', 'text'),
            ('personas', 'text'),
            ('barrio', 'text'),
            ('calle', 'text'),
            ('ciudad', 'text'),
            ('pais', 'text')
        ])

        print(f"   ✅ Índice de texto creado: {text_index}")
        return True

    except Exception as e:
        print(f"   ❌ Error al crear índice de texto: {e}")
        return False

def create_embedding_index(collection):
    """Crear índice para búsquedas vectoriales."""
    print("🔢 Creando índice para embeddings...")

    try:
        # Crear índice para el campo embedding
        embedding_index = collection.create_index('embedding')

        print(f"   ✅ Índice de embedding creado: {embedding_index}")
        return True

    except Exception as e:
        print(f"   ❌ Error al crear índice de embedding: {e}")
        return False

def create_compound_indexes(collection):
    """Crear índices compuestos para consultas frecuentes."""
    print("⚡ Creando índices compuestos...")

    indexes_created = []

    try:
        # Índice para consultas por ubicación
        location_index = collection.create_index([
            ('ciudad', 1),
            ('barrio', 1),
            ('calle', 1)
        ])
        indexes_created.append(f"ubicación: {location_index}")
        print(f"   ✅ Índice de ubicación creado: {location_index}")

        # Índice para consultas por fecha
        date_index = collection.create_index([
            ('fecha_creacion_anio', 1),
            ('fecha_creacion_mes', 1),
            ('fecha_creacion_dia', 1)
        ])
        indexes_created.append(f"fecha: {date_index}")
        print(f"   ✅ Índice de fecha creado: {date_index}")

        # Índice para consultas por objetos
        objects_index = collection.create_index('objetos')
        indexes_created.append(f"objetos: {objects_index}")
        print(f"   ✅ Índice de objetos creado: {objects_index}")

        # Índice para hash único
        hash_index = collection.create_index('id_hash', unique=True)
        indexes_created.append(f"hash único: {hash_index}")
        print(f"   ✅ Índice de hash único creado: {hash_index}")

        return indexes_created

    except Exception as e:
        print(f"   ❌ Error al crear índices compuestos: {e}")
        return indexes_created

def show_existing_indexes(collection):
    """Mostrar índices existentes en la colección."""
    print("📋 Índices existentes:")

    try:
        indexes = collection.list_indexes()
        for index in indexes:
            print(f"   - {index['name']}: {index['key']}")
    except Exception as e:
        print(f"   ❌ Error al listar índices: {e}")

def main():
    """Función principal para configurar MongoDB."""
    print("🍃 Configurando MongoDB para Búsqueda Semántica V2")
    print("=" * 60)

    # Cargar configuración
    config = load_configuration()
    print(f"📍 Conectando a: {config['database_name']}.{config['collection_name']}")

    try:
        # Conectar a MongoDB
        client = MongoClient(config['mongodb_uri'])
        db = client[config['database_name']]
        collection = db[config['collection_name']]

        # Verificar conexión
        client.admin.command('ping')
        print("   ✅ Conexión exitosa a MongoDB")

        # Mostrar índices existentes
        show_existing_indexes(collection)
        print()

        # Crear índices
        text_created = create_text_index(collection)
        embedding_created = create_embedding_index(collection)
        compound_indexes = create_compound_indexes(collection)

        print("\n" + "=" * 60)
        print("📊 RESUMEN DE CONFIGURACIÓN")
        print("=" * 60)

        print(f"✅ Índice de texto: {'Creado' if text_created else 'Error'}")
        print(f"✅ Índice de embedding: {'Creado' if embedding_created else 'Error'}")
        print(f"✅ Índices compuestos: {len(compound_indexes)} creados")

        if compound_indexes:
            for index in compound_indexes:
                print(f"   - {index}")

        print("\n🎉 ¡Configuración de MongoDB completada!")
        print("\n💡 Recomendaciones:")
        print("   - Los índices mejorarán el rendimiento de las búsquedas")
        print("   - El índice de texto permite búsquedas de texto completo")
        print("   - El índice de embedding optimiza las búsquedas semánticas")
        print("   - Los índices compuestos aceleran consultas específicas")

        client.close()

    except Exception as e:
        print(f"❌ Error al configurar MongoDB: {e}")
        print("\n💡 Soluciones posibles:")
        print("   - Verifica que MongoDB esté ejecutándose")
        print("   - Asegúrate de tener permisos para crear índices")
        print("   - Verifica la configuración de conexión en config/.env")
        return 1

    return 0

if __name__ == "__main__":
    exit(main())