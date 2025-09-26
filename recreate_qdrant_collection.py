#!/usr/bin/env python3
"""
Script para recrear la colección de Qdrant con la dimensionalidad correcta.
Este script elimina la colección existente y crea una nueva con 768 dimensiones
para ser compatible con el modelo embeddinggemma.
"""
import os
import sys
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams
from dotenv import load_dotenv
from pathlib import Path

def recreate_qdrant_collection():
    """Recrear la colección de Qdrant con la dimensionalidad correcta."""
    print("🔄 Recreando colección de Qdrant...")

    # Cargar configuración
    dotenv_path = Path('config/.env')
    load_dotenv(dotenv_path=dotenv_path)

    try:
        # Conectar a Qdrant
        qdrant_url = os.getenv('QDRANT_URL', 'http://localhost:6333')
        api_key = os.getenv('QDRANT_API_KEY', None)
        collection_name = os.getenv('QDRANT_COLLECTION', 'imagenes_semanticas')

        if api_key:
            client = QdrantClient(url=qdrant_url, api_key=api_key)
        else:
            client = QdrantClient(url=qdrant_url)

        print(f"🔗 Conectado a Qdrant: {qdrant_url}")
        print(f"📁 Colección: {collection_name}")

        # Verificar si la colección existe
        collections = client.get_collections()
        collection_exists = any(col.name == collection_name for col in collections.collections)

        if collection_exists:
            print(f"📂 Colección '{collection_name}' existe. Eliminando...")

            # Eliminar colección existente
            client.delete_collection(collection_name)
            print(f"✅ Colección '{collection_name}' eliminada")
        else:
            print(f"📂 Colección '{collection_name}' no existe")

        # Crear nueva colección con 768 dimensiones
        print("📏 Creando nueva colección con 768 dimensiones...")

        client.create_collection(
            collection_name=collection_name,
            vectors_config=VectorParams(size=768, distance=Distance.COSINE)
        )

        print(f"✅ Colección '{collection_name}' creada exitosamente")
        print("📊 Configuración:")
        print("   - Dimensiones: 768")
        print("   - Distancia: Coseno")
        print("   - Modelo: embeddinggemma")

        # Verificar la colección creada
        collection_info = client.get_collection(collection_name)
        print("\n🔍 Verificación:")
        print(f"   - Vectores totales: {collection_info.points_count}")
        print(f"   - Tamaño del vector: {collection_info.config.params.vectors.size}")
        print(f"   - Tipo de distancia: {collection_info.config.params.vectors.distance}")

        print("\n🎉 ¡Colección recreada exitosamente!")
        print("💡 Ahora puedes ejecutar el procesamiento de documentos sin errores de dimensionalidad")
        client.close()
        return True

    except Exception as e:
        print(f"❌ Error al recrear la colección: {e}")
        print("\n💡 Soluciones posibles:")
        print("   - Verifica que Qdrant esté ejecutándose")
        print("   - Asegúrate de tener permisos para crear/eliminar colecciones")
        print("   - Verifica la configuración de conexión en config/.env")
        return False

if __name__ == "__main__":
    success = recreate_qdrant_collection()
    sys.exit(0 if success else 1)