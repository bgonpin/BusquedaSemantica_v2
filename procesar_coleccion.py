#!/usr/bin/env python3
"""
Script para procesar toda la colección MongoDB y generar embeddings en Qdrant.

Uso:
    python procesar_coleccion.py [--batch-size N] [--max-docs N] [--verbose]

Opciones:
    --batch-size N    Tamaño del lote para procesamiento (default: 50)
    --max-docs N      Máximo de documentos a procesar (default: todos)
    --verbose         Mostrar información detallada
"""
import sys
import os
import argparse
from pathlib import Path

# Agregar el directorio actual al path
current_dir = str(Path(__file__).parent)
sys.path.insert(0, current_dir)

from src.database import DatabaseManager
from src.qdrant_manager import QdrantManager
from src.batch_processor import BatchProcessor


def main():
    """Función principal."""
    parser = argparse.ArgumentParser(description="Procesar colección MongoDB para generar embeddings en Qdrant")
    parser.add_argument("--batch-size", type=int, default=50, help="Tamaño del lote para procesamiento")
    parser.add_argument("--max-docs", type=int, default=None, help="Máximo de documentos a procesar")
    parser.add_argument("--verbose", action="store_true", help="Mostrar información detallada")

    args = parser.parse_args()

    print("🚀 Iniciando procesamiento de la colección MongoDB...")
    print(f"📊 Batch size: {args.batch_size}")
    print(f"📊 Max docs: {args.max_docs or 'Todos'}")
    print(f"📊 Verbose: {args.verbose}")
    print("-" * 60)

    try:
        # Inicializar componentes
        print("🔌 Conectando a MongoDB y Qdrant...")
        db_manager = DatabaseManager()
        qdrant_manager = QdrantManager()
        batch_processor = BatchProcessor(db_manager, qdrant_manager)

        # Mostrar estadísticas iniciales
        print("\n📈 Estadísticas iniciales:")
        stats = batch_processor.obtener_estadisticas_coleccion()

        print(f"   MongoDB: {stats['mongodb']['documentos_con_embedding']}/{stats['mongodb']['total_documentos']} documentos procesados")
        print(f"   Qdrant: {stats['qdrant']['total_vectores']} vectores")
        print(f"   Completitud: {stats['resumen']['completitud']:.1f}%")

        documentos_pendientes = stats['resumen']['documentos_pendientes']
        if documentos_pendientes == 0:
            print("\n✅ ¡La colección ya está completamente procesada!")
            return

        print(f"\n📝 Documentos pendientes de procesar: {documentos_pendientes}")

        # Confirmar procesamiento
        if not args.verbose:
            respuesta = input("\n¿Desea continuar con el procesamiento? (s/n): ")
            if respuesta.lower() not in ['s', 'si', 'yes']:
                print("❌ Procesamiento cancelado por el usuario")
                return

        # Procesar colección
        print("\n🔄 Iniciando procesamiento...")
        print(f"   Procesando en lotes de {args.batch_size} documentos")
        print("   (Esto puede tomar varios minutos dependiendo del tamaño de la colección)")
        print("-" * 60)

        resultado = batch_processor.procesar_coleccion_completa(
            batch_size=args.batch_size,
            max_documentos=args.max_docs
        )

        # Mostrar resultados
        print("\n✅ Procesamiento completado!")
        print("-" * 60)
        print("📊 RESULTADOS:")
        print(f"   Total procesados: {resultado['total_procesados']}")
        print(f"   Éxitos: {resultado['total_exitosos']}")
        print(f"   Errores: {resultado['total_errores']}")
        print(f"   Mensaje: {resultado['mensaje']}")

        # Mostrar estadísticas finales
        print("\n📈 Estadísticas finales:")
        stats_final = batch_processor.obtener_estadisticas_coleccion()
        print(f"   MongoDB: {stats_final['mongodb']['documentos_con_embedding']}/{stats_final['mongodb']['total_documentos']} documentos procesados")
        print(f"   Qdrant: {stats_final['qdrant']['total_vectores']} vectores")
        print(f"   Completitud: {stats_final['resumen']['completitud']:.1f}%")

        if stats_final['resumen']['sincronizado']:
            print("   ✅ MongoDB y Qdrant están sincronizados")
        else:
            print("   ⚠️  MongoDB y Qdrant no están completamente sincronizados")

        print("\n🎉 ¡Procesamiento completado exitosamente!")
        print("   Los embeddings están disponibles para búsquedas semánticas.")

    except KeyboardInterrupt:
        print("\n❌ Procesamiento interrumpido por el usuario")
    except Exception as e:
        print(f"\n❌ Error durante el procesamiento: {e}")
        if args.verbose:
            import traceback
            traceback.print_exc()
        sys.exit(1)

    finally:
        # Cerrar conexiones
        if 'db_manager' in locals():
            db_manager.cerrar_conexion()
        if 'qdrant_manager' in locals():
            qdrant_manager.cerrar_conexion()


if __name__ == "__main__":
    main()