#!/usr/bin/env python3
"""
Script de prueba para las funcionalidades de backup y restore de Qdrant.
"""
import os
import sys
import json
from datetime import datetime

# Añadir el directorio raíz al path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.qdrant_manager import QdrantManager

def test_backup_restore():
    """Probar las funcionalidades de backup y restore."""
    print("🧪 Probando funcionalidades de backup y restore de Qdrant...")

    try:
        # Inicializar QdrantManager
        qdrant = QdrantManager()
        print(f"✅ QdrantManager inicializado. Colección: {qdrant.collection_name}")

        # Obtener estadísticas iniciales
        stats = qdrant.obtener_estadisticas()
        print(f"📊 Estadísticas iniciales: {stats['total_vectors']} vectores")

        # Crear backup
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_file = f"test_backup_{timestamp}.json"

        print(f"💾 Creando backup en: {backup_file}")
        backup_result = qdrant.crear_backup_coleccion(backup_file)

        print("✅ Backup creado exitosamente:")
        print(f"   • Archivo: {backup_result['ruta_archivo']}")
        print(f"   • Vectores: {backup_result['total_vectores']}")
        print(f"   • Tamaño: {backup_result['tamano_archivo']} bytes")
        print(f"   • Hash: {backup_result['hash_sha256'][:16]}...")

        # Validar backup
        print(f"🔍 Validando backup: {backup_file}")
        validacion = qdrant.validar_backup(backup_file)

        if validacion["valido"]:
            print("✅ Backup válido:")
            print(f"   • Vectores: {validacion['total_vectores']}")
            print(f"   • Tamaño: {validacion['tamano_archivo']} bytes")
            print(f"   • Fecha: {validacion['fecha_backup']}")
        else:
            print(f"❌ Error de validación: {validacion['error']}")
            return False

        # Limpiar colección para probar restauración
        print("🧹 Limpiando colección para probar restauración...")
        qdrant.limpiar_coleccion()

        # Verificar que la colección esté vacía
        stats_vacia = qdrant.obtener_estadisticas()
        print(f"📊 Vectores después de limpiar: {stats_vacia['total_vectors']}")

        # Restaurar backup
        print(f"🔄 Restaurando backup desde: {backup_file}")
        restore_result = qdrant.restaurar_coleccion(backup_file, recrear_coleccion=False)

        print("✅ Restauración completada:")
        print(f"   • Vectores restaurados: {restore_result['total_vectores_restaurados']}")
        print(f"   • Vectores en colección: {restore_result['total_vectores_en_coleccion']}")

        # Verificar estadísticas finales
        stats_final = qdrant.obtener_estadisticas()
        print(f"📊 Estadísticas finales: {stats_final['total_vectors']} vectores")

        # Limpiar archivo de prueba
        if os.path.exists(backup_file):
            os.remove(backup_file)
            print(f"🗑️ Archivo de prueba eliminado: {backup_file}")

        print("🎉 Todas las pruebas pasaron exitosamente!")
        return True

    except Exception as e:
        print(f"❌ Error durante las pruebas: {str(e)}")
        return False

    finally:
        # Cerrar conexión
        if 'qdrant' in locals():
            qdrant.cerrar_conexion()

if __name__ == "__main__":
    success = test_backup_restore()
    sys.exit(0 if success else 1)