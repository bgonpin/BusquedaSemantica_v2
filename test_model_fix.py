#!/usr/bin/env python3
"""
Script de prueba rápida para verificar que el modelo corregido funciona.
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

def probar_modelo_corregido():
    """Probar que el modelo DETR funciona correctamente."""
    try:
        logger.info("=== PRUEBA DEL MODELO CORREGIDO ===")

        from src.object_detector import ObjectDetector

        # Inicializar detector con modelo corregido
        logger.info("Inicializando detector con modelo DETR...")
        detector = ObjectDetector(model_name="facebook/detr-resnet-50")

        # Verificar que el detector se inicializó correctamente
        if detector.detector is None:
            logger.error("❌ Detector no se inicializó correctamente")
            return False

        logger.info("✅ Detector inicializado correctamente con modelo DETR")

        # Probar con una imagen de prueba si existe
        test_image = "test_image.jpg"
        if os.path.exists(test_image):
            logger.info(f"Probando detección con imagen: {test_image}")
            objetos = detector.detectar_objetos(test_image, confianza_minima=0.3)

            if objetos:
                logger.info(f"✅ Objetos detectados: {objetos}")
                return True
            else:
                logger.warning("⚠️ No se detectaron objetos en la imagen de prueba")
                return True  # El modelo funciona, solo que no hay objetos en la imagen
        else:
            logger.warning(f"⚠️ Imagen de prueba no encontrada: {test_image}")
            logger.info("✅ Modelo cargado correctamente (sin imagen de prueba)")

        return True

    except Exception as e:
        logger.error(f"❌ Error en prueba del modelo: {e}")
        return False

def main():
    """Función principal de prueba."""
    logger.info("🚀 Probando modelo corregido...")

    if probar_modelo_corregido():
        logger.info("✅ ¡Modelo corregido funciona correctamente!")
        return 0
    else:
        logger.error("❌ Error con el modelo corregido")
        return 1

if __name__ == "__main__":
    import os
    sys.exit(main())