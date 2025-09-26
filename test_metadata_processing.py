#!/usr/bin/env python3
"""
Script de prueba para verificar el procesamiento completo de metadatos de imágenes.
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

def probar_extraccion_metadatos():
    """Probar la extracción de metadatos de una imagen."""
    try:
        logger.info("=== PRUEBA DE EXTRACCIÓN DE METADATOS ===")

        from src.metadata_extractor import MetadataExtractor, Geocodificador, ImageProcessor

        # Inicializar componentes
        extractor = MetadataExtractor()
        geocodificador = Geocodificador()
        processor = ImageProcessor()

        # Buscar una imagen de prueba
        ruta_base = "/mnt/remoto/11/Datos"
        imagenes_prueba = list(Path(ruta_base).rglob("*.jpg"))[:1]  # Tomar solo la primera

        if not imagenes_prueba:
            logger.warning("No se encontraron imágenes de prueba")
            return True

        ruta_imagen = str(imagenes_prueba[0])
        logger.info(f"Probando con imagen: {ruta_imagen}")

        # Probar extracción individual
        metadatos = extractor.extraer_metadatos_imagen(ruta_imagen)
        logger.info(f"Metadatos extraídos: {len(metadatos)} campos")

        # Probar geocodificación si hay coordenadas
        if metadatos.get("coordenadas"):
            coords = metadatos["coordenadas"]
            ubicacion = geocodificador.geocodificar_coordenadas(coords["lat"], coords["lon"])
            logger.info(f"Ubicación geocodificada: {ubicacion}")

        # Probar procesamiento completo
        metadatos_completos = processor.procesar_imagen_completa(ruta_imagen)
        logger.info(f"Procesamiento completo: {len(metadatos_completos)} campos")

        logger.info("✅ Extracción de metadatos funciona correctamente")
        return True

    except Exception as e:
        logger.error(f"❌ Error en prueba de extracción de metadatos: {e}")
        return False

def probar_busqueda_imagenes_nuevas():
    """Probar la búsqueda de imágenes nuevas."""
    try:
        logger.info("=== PRUEBA DE BÚSQUEDA DE IMÁGENES NUEVAS ===")

        from src.metadata_extractor import ImageDiscovery
        from src.database import DatabaseManager

        # Inicializar componentes
        db_manager = DatabaseManager()
        image_discovery = ImageDiscovery()

        # Buscar imágenes nuevas
        imagenes_nuevas = image_discovery.buscar_imagenes_nuevas(db_manager)

        logger.info(f"Imágenes nuevas encontradas: {len(imagenes_nuevas)}")

        # Mostrar información de las primeras imágenes encontradas
        for i, metadatos in enumerate(imagenes_nuevas[:3]):
            logger.info(f"Imagen {i+1}: {metadatos.get('nombre', 'unknown')}")
            logger.info(f"  Hash: {metadatos.get('hash_sha512', 'unknown')[:16]}...")
            logger.info(f"  Dimensiones: {metadatos.get('ancho', 0)}x{metadatos.get('alto', 0)}")
            logger.info(f"  Coordenadas: {metadatos.get('coordenadas', 'None')}")

        logger.info("✅ Búsqueda de imágenes nuevas funciona correctamente")
        return True

    except Exception as e:
        logger.error(f"❌ Error en prueba de búsqueda de imágenes nuevas: {e}")
        return False

def probar_inicializacion_con_imagenes_nuevas():
    """Probar la inicialización con procesamiento de imágenes nuevas."""
    try:
        logger.info("=== PRUEBA DE INICIALIZACIÓN CON IMÁGENES NUEVAS ===")

        from src.background_processor import ApplicationInitializer

        # Inicializar aplicación
        initializer = ApplicationInitializer()

        # Inicializar todos los componentes
        if initializer.initialize_all():
            logger.info("✅ Inicialización con imágenes nuevas funciona correctamente")
            return True
        else:
            logger.error("❌ Error en inicialización con imágenes nuevas")
            return False

    except Exception as e:
        logger.error(f"❌ Error en prueba de inicialización: {e}")
        return False

def main():
    """Función principal de prueba."""
    logger.info("🚀 Probando procesamiento completo de metadatos...")

    pruebas = [
        probar_extraccion_metadatos,
        probar_busqueda_imagenes_nuevas,
        probar_inicializacion_con_imagenes_nuevas
    ]

    resultados = []
    for prueba in pruebas:
        try:
            resultado = prueba()
            resultados.append(resultado)
        except Exception as e:
            logger.error(f"Error en prueba {prueba.__name__}: {e}")
            resultados.append(False)

    # Resumen de resultados
    exitosas = sum(resultados)
    total = len(resultados)

    logger.info("=== RESUMEN DE PRUEBAS ===")
    logger.info(f"Pruebas exitosas: {exitosas}/{total}")

    if exitosas == total:
        logger.info("✅ ¡Todas las pruebas pasaron correctamente!")
        return 0
    else:
        logger.error("❌ Algunas pruebas fallaron")
        return 1

if __name__ == "__main__":
    sys.exit(main())