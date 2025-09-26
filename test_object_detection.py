#!/usr/bin/env python3
"""
Script de prueba para la funcionalidad de detección de objetos.
"""
import os
import sys
import logging
from pathlib import Path

# Configurar logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Agregar el directorio actual al path
current_dir = str(Path(__file__).parent)
sys.path.insert(0, current_dir)

def probar_detector_objetos():
    """Probar el detector de objetos."""
    try:
        logger.info("=== PRUEBA DEL DETECTOR DE OBJETOS ===")

        from src.object_detector import ObjectDetector

        # Inicializar detector
        logger.info("Inicializando detector de objetos...")
        detector = ObjectDetector()

        # Verificar que el detector se inicializó correctamente
        if detector.detector is None:
            logger.error("❌ Detector no se inicializó correctamente")
            return False

        logger.info("✅ Detector inicializado correctamente")

        # Probar con una imagen de prueba si existe
        test_image = "test_image.jpg"
        if os.path.exists(test_image):
            logger.info(f"Probando detección con imagen: {test_image}")
            objetos = detector.detectar_objetos(test_image, confianza_minima=0.3)

            if objetos:
                logger.info(f"✅ Objetos detectados: {objetos}")
            else:
                logger.warning("⚠️ No se detectaron objetos en la imagen de prueba")
        else:
            logger.warning(f"⚠️ Imagen de prueba no encontrada: {test_image}")

        # Probar generación de hash
        if os.path.exists(test_image):
            hash_imagen = detector.generar_hash_imagen(test_image)
            logger.info(f"✅ Hash de imagen generado: {hash_imagen[:16]}...")

        return True

    except Exception as e:
        logger.error(f"❌ Error en prueba del detector: {e}")
        return False

def probar_procesador_fondo():
    """Probar el procesador en segundo plano."""
    try:
        logger.info("\n=== PRUEBA DEL PROCESADOR EN SEGUNDO PLANO ===")

        from src.background_processor import ApplicationInitializer

        # Inicializar sistema
        logger.info("Inicializando sistema...")
        initializer = ApplicationInitializer()

        # Probar inicialización de componentes
        logger.info("Probando inicialización de base de datos...")
        db_ok = initializer.initialize_database()

        logger.info("Probando inicialización de detector...")
        detector_ok = initializer.initialize_object_detector()

        logger.info("Probando inicialización de procesador...")
        processor_ok = initializer.initialize_background_processor()

        if not (db_ok and detector_ok and processor_ok):
            logger.error("❌ Error en inicialización de componentes")
            return False

        # Probar inicialización completa
        logger.info("Probando inicialización completa...")
        all_ok = initializer.initialize_all()

        if not all_ok:
            logger.error("❌ Error en inicialización completa")
            return False

        logger.info("✅ Sistema inicializado correctamente")

        # Probar obtención de estado
        logger.info("Probando obtención de estado del sistema...")
        status = initializer.get_system_status()
        logger.info(f"✅ Estado del sistema: {status}")

        # Probar inicio del procesamiento
        logger.info("Probando inicio del procesamiento en segundo plano...")
        initializer.start_background_processing()
        logger.info("✅ Procesamiento en segundo plano iniciado")

        # Esperar un momento
        import time
        time.sleep(2)

        # Verificar que está procesando
        status = initializer.get_system_status()
        if status.get('running', False):
            logger.info("✅ Procesador en segundo plano ejecutándose")
        else:
            logger.warning("⚠️ Procesador en segundo plano no se inició")

        # Detener procesamiento
        logger.info("Deteniendo procesamiento...")
        initializer.stop_background_processing()
        logger.info("✅ Procesamiento detenido")

        return True

    except Exception as e:
        logger.error(f"❌ Error en prueba del procesador: {e}")
        return False

def probar_integracion_base_datos():
    """Probar integración con la base de datos."""
    try:
        logger.info("\n=== PRUEBA DE INTEGRACIÓN CON BASE DE DATOS ===")

        from src.database import DatabaseManager
        from src.object_detector import BackgroundObjectProcessor, ObjectDetector

        # Inicializar componentes
        logger.info("Inicializando gestor de base de datos...")
        db_manager = DatabaseManager()

        logger.info("Inicializando detector de objetos...")
        detector = ObjectDetector()

        logger.info("Inicializando procesador de objetos...")
        processor = BackgroundObjectProcessor(db_manager, detector)

        # Verificar estadísticas de la base de datos
        logger.info("Obteniendo estadísticas de la base de datos...")
        stats = db_manager.obtener_estadisticas()
        logger.info(f"✅ Estadísticas: {stats}")

        # Probar obtención de documentos pendientes
        logger.info("Verificando documentos pendientes...")
        documentos_pendientes = processor.procesar_imagenes_sin_objetos(batch_size=1)

        logger.info(f"✅ Procesamiento completado: {documentos_pendientes}")

        return True

    except Exception as e:
        logger.error(f"❌ Error en prueba de integración: {e}")
        return False

def main():
    """Función principal de pruebas."""
    logger.info("🚀 Iniciando pruebas de detección de objetos...")

    pruebas = [
        ("Detector de Objetos", probar_detector_objetos),
        ("Procesador en Segundo Plano", probar_procesador_fondo),
        ("Integración con Base de Datos", probar_integracion_base_datos)
    ]

    resultados = []

    for nombre_prueba, funcion_prueba in pruebas:
        logger.info(f"\n{'='*50}")
        logger.info(f"Ejecutando: {nombre_prueba}")
        logger.info('='*50)

        try:
            resultado = funcion_prueba()
            resultados.append((nombre_prueba, resultado))

            if resultado:
                logger.info(f"✅ {nombre_prueba}: PASÓ")
            else:
                logger.error(f"❌ {nombre_prueba}: FALLÓ")

        except Exception as e:
            logger.error(f"❌ {nombre_prueba}: ERROR - {e}")
            resultados.append((nombre_prueba, False))

    # Resumen final
    logger.info(f"\n{'='*60}")
    logger.info("RESUMEN DE PRUEBAS")
    logger.info('='*60)

    total_pruebas = len(resultados)
    pruebas_pasadas = sum(1 for _, resultado in resultados if resultado)

    for nombre_prueba, resultado in resultados:
        status = "✅ PASÓ" if resultado else "❌ FALLÓ"
        logger.info(f"{nombre_prueba}: {status}")

    logger.info(f"\nTotal: {pruebas_pasadas}/{total_pruebas} pruebas pasaron")

    if pruebas_pasadas == total_pruebas:
        logger.info("🎉 ¡Todas las pruebas pasaron exitosamente!")
        return 0
    else:
        logger.error("❌ Algunas pruebas fallaron")
        return 1

if __name__ == "__main__":
    sys.exit(main())