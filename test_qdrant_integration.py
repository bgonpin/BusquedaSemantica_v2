#!/usr/bin/env python3
"""
Script de prueba para verificar la integración con Qdrant.
"""
import sys
import os
from pathlib import Path

# Agregar el directorio actual al path
current_dir = str(Path(__file__).parent)
sys.path.insert(0, current_dir)

from src.database import DatabaseManager
from src.qdrant_manager import QdrantManager
from src.migracion_manager import MigracionManager
from src.busqueda_semantica import BuscadorSemantico

def test_conexiones():
    """Probar conexiones a MongoDB y Qdrant."""
    print("=== Probando conexiones ===")

    try:
        # Probar MongoDB
        db_manager = DatabaseManager()
        db_manager.client.admin.command('ping')
        print("✓ MongoDB conectado correctamente")

        # Probar Qdrant
        qdrant_manager = QdrantManager()
        qdrant_manager.client.health_check()
        print("✓ Qdrant conectado correctamente")

        return db_manager, qdrant_manager

    except Exception as e:
        print(f"✗ Error en conexiones: {e}")
        return None, None

def test_migracion(db_manager, qdrant_manager):
    """Probar funcionalidad de migración."""
    print("\n=== Probando migración ===")

    try:
        migracion_manager = MigracionManager(db_manager, qdrant_manager)

        # Obtener estadísticas iniciales
        stats_mongo = db_manager.obtener_estadisticas()
        stats_qdrant = qdrant_manager.obtener_estadisticas()

        print(f"Documentos en MongoDB: {stats_mongo.get('documentos_con_embedding', 0)}")
        print(f"Documentos en Qdrant: {stats_qdrant.get('total_vectors', 0)}")

        # Si hay documentos para migrar, hacer una migración de prueba
        if stats_mongo.get('documentos_con_embedding', 0) > 0:
            print("Iniciando migración de prueba...")
            resultado = migracion_manager.migrar_embeddings_existentes(batch_size=10)

            print(f"Migración completada: {resultado.get('total_migrados', 0)} migrados")
            print(f"Errores: {resultado.get('total_errores', 0)}")
        else:
            print("No hay documentos con embeddings para migrar")

        return migracion_manager

    except Exception as e:
        print(f"✗ Error en migración: {e}")
        return None

def test_busqueda_semantica(db_manager, qdrant_manager):
    """Probar búsqueda semántica con Qdrant."""
    print("\n=== Probando búsqueda semántica ===")

    try:
        buscador = BuscadorSemantico(db_manager, qdrant_manager)

        # Verificar si hay documentos en Qdrant
        stats_qdrant = qdrant_manager.obtener_estadisticas()
        docs_qdrant = stats_qdrant.get('total_vectors', 0)

        if docs_qdrant == 0:
            print("No hay documentos en Qdrant para buscar")
            return

        # Realizar una búsqueda de prueba
        from src.models import ConsultaBusqueda
        consulta = ConsultaBusqueda(
            query="prueba búsqueda semántica",
            limite=5,
            umbral_similitud=0.5
        )

        print("Realizando búsqueda semántica...")
        resultados = buscador.buscar_semanticamente(consulta)

        print(f"Búsqueda completada: {len(resultados)} resultados encontrados")

        for i, resultado in enumerate(resultados):
            print(f"  {i+1}. {resultado.documento.nombre} (similitud: {resultado.similitud:.3f})")

    except Exception as e:
        print(f"✗ Error en búsqueda semántica: {e}")

def main():
    """Función principal de prueba."""
    print("Iniciando pruebas de integración con Qdrant...")

    # Probar conexiones
    db_manager, qdrant_manager = test_conexiones()
    if not db_manager or not qdrant_manager:
        print("No se pueden continuar las pruebas sin conexiones válidas")
        return

    # Probar migración
    migracion_manager = test_migracion(db_manager, qdrant_manager)

    # Probar búsqueda semántica
    test_busqueda_semantica(db_manager, qdrant_manager)

    print("\n=== Pruebas completadas ===")
    print("✓ Integración con Qdrant funcionando correctamente")

    # Cerrar conexiones
    db_manager.cerrar_conexion()
    qdrant_manager.cerrar_conexion()

if __name__ == "__main__":
    main()