#!/usr/bin/env python3
"""
Script de prueba para validar la funcionalidad de búsqueda semántica.
"""
import sys
import os
from pathlib import Path

# Agregar el directorio actual al path
sys.path.insert(0, str(Path(__file__).parent))

from src.busqueda_semantica import BuscadorSemantico
from src.database import DatabaseManager
from src.qdrant_manager import QdrantManager
from src.models import ConsultaBusqueda

def probar_conexion_ollama():
    """Probar conexión con Ollama."""
    print("🔍 Probando conexión con Ollama...")

    try:
        from langchain_ollama import OllamaLLM, OllamaEmbeddings

        # Inicializar modelos
        ollama_base_url = os.getenv('OLLAMA_BASE_URL', 'http://localhost:11434')
        embedding_model = os.getenv('EMBEDDING_MODEL', 'embeddinggemma')
        ollama_model = os.getenv('OLLAMA_MODEL', 'qwen3:14b_40K')

        # Probar embeddings
        embeddings = OllamaEmbeddings(
            base_url=ollama_base_url,
            model=embedding_model
        )

        # Probar LLM
        llm = OllamaLLM(
            base_url=ollama_base_url,
            model=ollama_model,
            temperature=0.1
        )

        # Generar embedding de prueba
        test_embedding = embeddings.embed_query("prueba de conexión")
        print(f"✅ Embeddings funcionando. Dimensión: {len(test_embedding)}")

        # Generar respuesta de prueba
        test_response = llm.invoke("Di 'Hola mundo' en español")
        print(f"✅ LLM funcionando. Respuesta: {test_response[:50]}...")

        return True

    except Exception as e:
        print(f"❌ Error con Ollama: {e}")
        return False

def probar_conexion_qdrant():
    """Probar conexión con Qdrant."""
    print("🔍 Probando conexión con Qdrant...")

    try:
        qdrant_manager = QdrantManager()
        stats = qdrant_manager.obtener_estadisticas()
        print(f"✅ Qdrant funcionando. Colección: {stats['collection_name']}")
        print(f"   Vectores: {stats['total_vectors']}, Dimensión: {stats['vector_size']}")
        return True

    except Exception as e:
        print(f"❌ Error con Qdrant: {e}")
        return False

def probar_conexion_mongodb():
    """Probar conexión con MongoDB."""
    print("🔍 Probando conexión con MongoDB...")

    try:
        db_manager = DatabaseManager()
        stats = db_manager.obtener_estadisticas()
        print(f"✅ MongoDB funcionando. Base de datos: {db_manager.database_name if hasattr(db_manager, 'database_name') else 'album'}")
        print(f"   Documentos totales: {stats['total_documentos']}")
        print(f"   Documentos procesados: {stats['documentos_procesados']}")
        return True

    except Exception as e:
        print(f"❌ Error con MongoDB: {e}")
        return False

def probar_busqueda_semantica():
    """Probar búsqueda semántica con consultas de ejemplo."""
    print("🔍 Probando búsqueda semántica...")

    try:
        # Inicializar gestores
        db_manager = DatabaseManager()
        qdrant_manager = QdrantManager()
        buscador = BuscadorSemantico(db_manager, qdrant_manager)

        # Consultas de prueba
        consultas_prueba = [
            "imágenes de personas",
            "fotos de paisajes",
            "imágenes con objetos tecnológicos",
            "fotos tomadas en la ciudad"
        ]

        for consulta_texto in consultas_prueba:
            print(f"\n   Probando consulta: '{consulta_texto}'")

            consulta = ConsultaBusqueda(
                query=consulta_texto,
                limite=5,
                umbral_similitud=0.7
            )

            try:
                resultados = buscador.buscar_semanticamente(consulta)

                if resultados:
                    print(f"   ✅ Encontrados {len(resultados)} resultados")
                    for i, resultado in enumerate(resultados[:3]):  # Mostrar primeros 3
                        print(f"      {i+1}. {resultado.documento.nombre} (similitud: {resultado.similitud:.3f})")
                else:
                    print("   ⚠️ No se encontraron resultados")

            except Exception as e:
                print(f"   ❌ Error en búsqueda: {e}")

        return True

    except Exception as e:
        print(f"❌ Error al probar búsqueda semántica: {e}")
        return False

def main():
    """Función principal de prueba."""
    print("🚀 Iniciando pruebas de búsqueda semántica...\n")

    # Verificar conexiones
    ollama_ok = probar_conexion_ollama()
    qdrant_ok = probar_conexion_qdrant()
    mongodb_ok = probar_conexion_mongodb()

    print("\n📊 Resultado de conexiones:")
    print(f"   Ollama: {'✅' if ollama_ok else '❌'}")
    print(f"   Qdrant: {'✅' if qdrant_ok else '❌'}")
    print(f"   MongoDB: {'✅' if mongodb_ok else '❌'}")

    if not all([ollama_ok, qdrant_ok, mongodb_ok]):
        print("\n❌ Algunas conexiones fallaron. Verifica que todos los servicios estén ejecutándose.")
        return False

    # Probar búsqueda semántica
    print("\n🔍 Probando funcionalidad de búsqueda semántica...")
    busqueda_ok = probar_busqueda_semantica()

    print("\n📊 Resultado final:")
    print(f"   Búsqueda semántica: {'✅' if busqueda_ok else '❌'}")

    if busqueda_ok:
        print("\n🎉 ¡Todas las pruebas pasaron exitosamente!")
        print("   El sistema de búsqueda semántica está funcionando correctamente.")
        print("   Puedes usar la interfaz gráfica para realizar búsquedas.")
    else:
        print("\n⚠️ Algunas pruebas de búsqueda fallaron.")
        print("   Revisa los logs para más detalles.")

    return busqueda_ok

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)