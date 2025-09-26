#!/usr/bin/env python3
"""
Script de prueba para las funcionalidades de backup y restore de MongoDB.
"""
import os
import sys
import json
from datetime import datetime

# Añadir el directorio raíz al path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.database import DatabaseManager

def test_backup_restore_mongodb():
    """Probar las funcionalidades de backup y restore de MongoDB."""
    print("🧪 Probando funcionalidades de backup y restore de MongoDB...")

    try:
        # Inicializar DatabaseManager
        db_manager = DatabaseManager()
        print(f"✅ DatabaseManager inicializado. Base de datos: {db_manager.database.name}")
        print(f"✅ Colección: {db_manager.collection.name}")

        # Obtener estadísticas iniciales
        stats = db_manager.obtener_estadisticas()
        print(f"📊 Estadísticas iniciales: {stats['total_documentos']} documentos")

        # Crear backup
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_file = f"test_backup_mongodb_{timestamp}.json"

        print(f"💾 Creando backup en: {backup_file}")
        backup_result = db_manager.crear_backup_coleccion(backup_file)

        print("✅ Backup creado exitosamente:")
        print(f"   • Archivo: {backup_result['ruta_archivo']}")
        print(f"   • Documentos: {backup_result['total_documentos']}")
        print(f"   • Tamaño: {backup_result['tamano_archivo']} bytes")
        print(f"   • Hash: {backup_result['hash_sha256'][:16]}...")

        # Validar backup
        print(f"🔍 Validando backup: {backup_file}")
        validacion = db_manager.validar_backup(backup_file)

        if validacion["valido"]:
            print("✅ Backup válido:")
            print(f"   • Documentos: {validacion['total_documentos']}")
            print(f"   • Tamaño: {validacion['tamano_archivo']} bytes")
            print(f"   • Fecha: {validacion['fecha_backup']}")
            print(f"   • Base de datos: {validacion['database_name']}")
            print(f"   • Colección: {validacion['collection_name']}")
        else:
            print(f"❌ Error de validación: {validacion['error']}")
            return False

        # Limpiar colección para probar restauración
        print("🧹 Limpiando colección para probar restauración...")
        collection_name = db_manager.collection.name
        db_manager.database.drop_collection(collection_name)
        db_manager.collection = db_manager.database[collection_name]

        # Verificar que la colección esté vacía
        stats_vacia = db_manager.obtener_estadisticas()
        print(f"📊 Documentos después de limpiar: {stats_vacia['total_documentos']}")

        # Restaurar backup
        print(f"🔄 Restaurando backup desde: {backup_file}")
        restore_result = db_manager.restaurar_coleccion(backup_file, eliminar_existente=False)

        print("✅ Restauración completada:")
        print(f"   • Documentos restaurados: {restore_result['total_documentos_restaurados']}")
        print(f"   • Documentos en colección: {restore_result['total_documentos_en_coleccion']}")

        # Verificar estadísticas finales
        stats_final = db_manager.obtener_estadisticas()
        print(f"📊 Estadísticas finales: {stats_final['total_documentos']} documentos")

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
        if 'db_manager' in locals():
            db_manager.cerrar_conexion()

if __name__ == "__main__":
    success = test_backup_restore_mongodb()
    sys.exit(0 if success else 1)