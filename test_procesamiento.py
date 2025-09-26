#!/usr/bin/env python3
"""
Script de prueba para verificar que el procesamiento de documentos funciona correctamente
sin generar descripciones semánticas, solo embeddings de campos existentes.
"""
import os
import sys
from dotenv import load_dotenv
from pathlib import Path

# Añadir el directorio raíz al path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.models import ImagenDocumento
from src.busqueda_semantica import BuscadorSemantico
from src.database import DatabaseManager

def test_procesamiento_documentos():
    """Probar el procesamiento de documentos con campos existentes."""
    print("🧪 Probando procesamiento de documentos con campos existentes...")

    # Cargar configuración
    dotenv_path = Path('config/.env')
    load_dotenv(dotenv_path=dotenv_path)

    try:
        # Conectar a MongoDB
        db_manager = DatabaseManager()

        # Crear buscador semántico
        buscador = BuscadorSemantico(db_manager)

        # Buscar documentos problemáticos para probar
        ids_problematicos = [
            '63d29fcb8a2530bb344651357bc9fb59cb1d70327920213e13ef7dd76d7df715ff9a865fa53344635935de231a8b3ac7cd9e76a177727b29b5d10a5003bd55f5',
            '1ac094abc6d72bf3c6185acb82d2010482161fd0c37a5e1c8b04c5b762230ffbe49be1b81ecc22d5e31463cf77f493058f97be127a1eae6423e97a1bb5aa52ab',
            'bf495781063326ccda45e68c1f9d4f11428a7b112397351c5329f6689937e96697751aa12223b4b13cb9ed266d408c124732aa3e1bde2c153938af7c97870557'
        ]

        documentos_procesados = 0
        documentos_con_error = 0

        for doc_id in ids_problematicos:
            try:
                # Obtener documento de MongoDB
                doc_data = db_manager.collection.find_one({'_id': doc_id})
                if not doc_data:
                    print(f"❌ Documento {doc_id[:20]}... no encontrado")
                    documentos_con_error += 1
                    continue

                print(f"\n📄 Procesando documento {doc_id[:20]}...")

                # Crear objeto ImagenDocumento
                documento = ImagenDocumento(**doc_data)
                documento.ensure_id_hash()

                print(f"   📋 Nombre: {documento.nombre}")
                print(f"   📍 Ubicación: {documento.ciudad}, {documento.barrio}")
                print(f"   🏷️  Objetos: {', '.join(documento.objetos) if documento.objetos else 'Ninguno'}")
                print(f"   📅 Fecha: {documento.get_fecha_creacion()}")

                # Procesar documento (generar embedding)
                documento_procesado = buscador.procesar_documento(documento, None)

                print(f"   ✅ Procesamiento exitoso")
                print(f"   🔗 ID Hash: {documento_procesado.id_hash[:20]}...")
                print(f"   📊 Embedding: {len(documento_procesado.embedding)} dimensiones")
                print(f"   📝 Texto para embedding: {documento_procesado.descripcion_semantica[:50]}...")

                documentos_procesados += 1

            except Exception as e:
                print(f"❌ Error al procesar documento {doc_id[:20]}...: {e}")
                documentos_con_error += 1

        print("\n📊 RESULTADOS:")
        print(f"   ✅ Documentos procesados exitosamente: {documentos_procesados}")
        print(f"   ❌ Documentos con error: {documentos_con_error}")

        if documentos_con_error == 0:
            print("   🎉 ¡Todos los documentos se procesaron correctamente!")
            print("   🎉 ¡El sistema ahora genera embeddings solo de campos existentes!")
        else:
            print("   ⚠️  Algunos documentos tuvieron problemas")

        return documentos_con_error == 0

    except Exception as e:
        print(f"❌ Error al inicializar el sistema: {e}")
        return False

if __name__ == "__main__":
    success = test_procesamiento_documentos()
    sys.exit(0 if success else 1)