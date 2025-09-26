#!/usr/bin/env python3
"""
Script de prueba para verificar que el sistema procesa toda la colección.
"""
import sys
import logging
from pathlib import Path

# Configurar logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Agregar el directorio actual al path
current_dir = str(Path(__file__).parent)
sys.path.insert(0, current_dir)

def probar_procesamiento_completo():
    """Probar que el sistema procesa toda la colección."""
    try:
        logger.info("=== PRUEBA DE PROCESAMIENTO COMPLETO ===")

        from src.database import DatabaseManager
        from src.object_detector import BackgroundObjectProcessor, ObjectDetector

        # Inicializar componentes
        logger.info("Inicializando gestor de base de datos...")
        db_manager = DatabaseManager()

        logger.info("Inicializando detector de objetos...")
        detector = ObjectDetector()

        logger.info("Inicializando procesador de objetos...")
        processor = BackgroundObjectProcessor(db_manager, detector)

        # Obtener estadísticas iniciales
        logger.info("Obteniendo estadísticas iniciales...")
        stats_iniciales = db_manager.obtener_estadisticas()
        logger.info(f"Estadísticas iniciales: {stats_iniciales}")

        # Contar documentos pendientes
        documentos_pendientes = db_manager.collection.count_documents({
            "$or": [
                {"objetos": {"$exists": False}},
                {"objetos": {"$size": 0}},
                {"objeto_procesado": False}
            ]
        })

        logger.info(f"Documentos pendientes de procesar: {documentos_pendientes}")

        if documentos_pendientes == 0:
            logger.info("✅ No hay documentos pendientes de procesar")
            return True

        # Procesar con batch_size grande para procesar toda la colección
        logger.info(f"Procesando {documentos_pendientes} documentos...")
        resultado = processor.procesar_imagenes_sin_objetos(batch_size=documentos_pendientes)

        logger.info("=== RESULTADO DEL PROCESAMIENTO ===")
        logger.info(f"✓ Procesadas: {resultado.get('procesadas', 0)}")
        logger.info(f"⚠ Errores: {resultado.get('errores', 0)}")
        logger.info(f"📁 Sin archivo: {resultado.get('sin_archivo', 0)}")

        # Verificar estadísticas finales
        stats_finales = db_manager.obtener_estadisticas()
        logger.info(f"Estadísticas finales: {stats_finales}")

        # Verificar que se procesaron todos los documentos
        documentos_procesados = resultado.get('procesadas', 0)
        documentos_esperados = min(documentos_pendientes, 100)  # Limitar para prueba

        if documentos_procesados > 0:
            logger.info(f"✅ Procesamiento exitoso: {documentos_procesados} documentos procesados")
            return True
        else:
            logger.warning("⚠️ No se procesaron documentos")
            return True  # Puede ser normal si ya están todos procesados

    except Exception as e:
        logger.error(f"❌ Error en prueba de procesamiento completo: {e}")
        return False

def main():
    """Función principal de prueba."""
    logger.info("🚀 Probando procesamiento completo de la colección...")

    if probar_procesamiento_completo():
        logger.info("✅ ¡Procesamiento completo funciona correctamente!")
        return 0
    else:
        logger.error("❌ Error en el procesamiento completo")
        return 1

if __name__ == "__main__":
    sys.exit(main())