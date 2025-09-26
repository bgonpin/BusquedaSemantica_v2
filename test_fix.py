#!/usr/bin/env python3
"""
Script de prueba para verificar que el error de validación de id_hash esté corregido.
"""
import os
import sys
from pymongo import MongoClient
from dotenv import load_dotenv
from pathlib import Path

# Añadir el directorio raíz al path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.models import ImagenDocumento

def test_document_conversion():
    """Probar la conversión de documentos sin id_hash."""
    print("🧪 Probando conversión de documentos...")

    # Cargar configuración
    dotenv_path = Path('config/.env')
    load_dotenv(dotenv_path=dotenv_path)

    # Conectar a MongoDB
    client = MongoClient(os.getenv('MONGODB_URI', 'mongodb://localhost:27017/'))
    db = client[os.getenv('MONGODB_DATABASE', 'album')]
    collection = db[os.getenv('MONGODB_COLLECTION', 'imagenes_2')]

    # Buscar documentos problemáticos
    ids_problematicos = [
        '63d29fcb8a2530bb344651357bc9fb59cb1d70327920213e13ef7dd76d7df715ff9a865fa53344635935de231a8b3ac7cd9e76a177727b29b5d10a5003bd55f5',
        '1ac094abc6d72bf3c6185acb82d2010482161fd0c37a5e1c8b04c5b762230ffbe49be1b81ecc22d5e31463cf77f493058f97be127a1eae6423e97a1bb5aa52ab',
        'bf495781063326ccda45e68c1f9d4f11428a7b112397351c5329f6689937e96697751aa12223b4b13cb9ed266d408c124732aa3e1bde2c153938af7c97870557'
    ]

    documentos_convertidos = 0
    documentos_con_error = 0

    for doc_id in ids_problematicos:
        try:
            doc = collection.find_one({'_id': doc_id})
            if doc:
                print(f"\n📄 Probando documento {doc_id[:20]}...")

                # Intentar convertir a ImagenDocumento
                imagen_doc = ImagenDocumento(**doc)
                print("   ✅ Conversión exitosa")

                # Verificar si tiene id_hash
                if imagen_doc.id_hash:
                    print(f"   ✅ Ya tiene id_hash: {imagen_doc.id_hash[:20]}...")
                else:
                    print("   ⚠️  No tiene id_hash, llamando ensure_id_hash()...")
                    imagen_doc.ensure_id_hash()
                    print(f"   ✅ id_hash generado: {imagen_doc.id_hash[:20]}...")

                documentos_convertidos += 1
            else:
                print(f"\n❌ Documento {doc_id[:20]}... no encontrado")
                documentos_con_error += 1

        except Exception as e:
            print(f"\n❌ Error al procesar documento {doc_id[:20]}...: {e}")
            documentos_con_error += 1

    print("\n📊 RESULTADOS:")
    print(f"   ✅ Documentos convertidos exitosamente: {documentos_convertidos}")
    print(f"   ❌ Documentos con error: {documentos_con_error}")

    if documentos_con_error == 0:
        print("   🎉 ¡Todos los documentos se convirtieron correctamente!")
        print("   🎉 ¡El error de validación de id_hash ha sido corregido!")
    else:
        print("   ⚠️  Algunos documentos aún tienen problemas")

    client.close()
    return documentos_con_error == 0

if __name__ == "__main__":
    success = test_document_conversion()
    sys.exit(0 if success else 1)