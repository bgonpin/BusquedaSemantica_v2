"""
Módulo para procesamiento en segundo plano de detección de objetos.
"""
import os
import sys
import logging
import threading
import time
from typing import Optional, Dict, Any
from datetime import datetime

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class BackgroundProcessor:
    """Procesador en segundo plano para detección de objetos."""

    def __init__(self, db_manager, object_detector, check_interval: int = 300):
        """
        Inicializar el procesador en segundo plano.

        Args:
            db_manager: Gestor de base de datos
            object_detector: Detector de objetos
            check_interval: Intervalo en segundos para verificar nuevas imágenes
        """
        self.db_manager = db_manager
        self.object_detector = object_detector
        self.check_interval = check_interval
        self.processor = None
        self.running = False
        self.logger = logging.getLogger(__name__)

    def start(self):
        """Iniciar el procesamiento en segundo plano."""
        if self.running:
            self.logger.warning("El procesador ya está ejecutándose")
            return

        self.running = True
        self.processor = threading.Thread(target=self._run_processor, daemon=True)
        self.processor.start()
        self.logger.info("Procesador en segundo plano iniciado")

    def stop(self):
        """Detener el procesamiento en segundo plano."""
        self.running = False
        if self.processor and self.processor.is_alive():
            self.processor.join(timeout=5)
        self.logger.info("Procesador en segundo plano detenido")

    def _run_processor(self):
        """Método principal del hilo de procesamiento."""
        self.logger.info("Iniciando ciclo de procesamiento en segundo plano")

        while self.running:
            try:
                # Verificar si hay imágenes sin procesar
                documentos_pendientes = self._obtener_documentos_pendientes()

                if documentos_pendientes > 0:
                    self.logger.info(f"Procesando {documentos_pendientes} imágenes pendientes...")

                    # Procesar TODA la colección (sin límite de batch_size)
                    estadisticas = self.object_detector.procesar_imagenes_sin_objetos(batch_size=documentos_pendientes)

                    if estadisticas["procesadas"] > 0:
                        self.logger.info(f"Procesadas {estadisticas['procesadas']} imágenes correctamente")

                    if estadisticas["errores"] > 0:
                        self.logger.warning(f"Errores en {estadisticas['errores']} imágenes")

                    # Si quedan más imágenes por procesar, continuar inmediatamente
                    documentos_restantes = self._obtener_documentos_pendientes()
                    if documentos_restantes > 0:
                        self.logger.info(f"Quedan {documentos_restantes} imágenes por procesar, continuando...")

                else:
                    self.logger.debug("No hay imágenes pendientes de procesar")

            except Exception as e:
                self.logger.error(f"Error en ciclo de procesamiento: {e}")

            # Si no hay más imágenes por procesar, esperar antes del siguiente ciclo
            documentos_restantes = self._obtener_documentos_pendientes()
            if documentos_restantes == 0:
                self.logger.info("Todas las imágenes procesadas, esperando próximo ciclo...")
                for _ in range(self.check_interval):
                    if not self.running:
                        break
                    time.sleep(1)

    def _obtener_documentos_pendientes(self) -> int:
        """
        Obtener número de documentos pendientes de procesar.

        Returns:
            Número de documentos sin procesar
        """
        try:
            query = {
                "$or": [
                    {"objetos": {"$exists": False}},
                    {"objetos": {"$size": 0}},
                    {"objeto_procesado": False}
                ]
            }

            return self.db_manager.collection.count_documents(query)

        except Exception as e:
            self.logger.error(f"Error al obtener documentos pendientes: {e}")
            return 0

    def get_status(self) -> Dict[str, Any]:
        """
        Obtener estado actual del procesador.

        Returns:
            Diccionario con información del estado
        """
        return {
            "running": self.running,
            "processor_alive": self.processor.is_alive() if self.processor else False,
            "documentos_pendientes": self._obtener_documentos_pendientes(),
            "check_interval": self.check_interval,
            "last_check": datetime.now().isoformat()
        }


class ApplicationInitializer:
    """Inicializador de la aplicación con procesamiento en segundo plano."""

    def __init__(self):
        """Inicializar el inicializador de la aplicación."""
        self.db_manager = None
        self.object_detector = None
        self.background_processor = None
        self.logger = logging.getLogger(__name__)

    def initialize_database(self):
        """Inicializar conexión a la base de datos."""
        try:
            from src.database import DatabaseManager
            self.db_manager = DatabaseManager()
            self.logger.info("Base de datos inicializada correctamente")
            return True
        except Exception as e:
            self.logger.error(f"Error al inicializar base de datos: {e}")
            return False

    def initialize_object_detector(self):
        """Inicializar detector de objetos."""
        try:
            from src.object_detector import ObjectDetector
            self.object_detector = ObjectDetector()
            self.logger.info("Detector de objetos inicializado correctamente")
            return True
        except Exception as e:
            self.logger.error(f"Error al inicializar detector de objetos: {e}")
            return False

    def initialize_background_processor(self):
        """Inicializar procesador en segundo plano."""
        try:
            if not self.db_manager or not self.object_detector:
                raise Exception("Base de datos y detector de objetos deben estar inicializados primero")

            from src.object_detector import BackgroundObjectProcessor
            self.background_processor = BackgroundProcessor(
                self.db_manager,
                BackgroundObjectProcessor(self.db_manager, self.object_detector)
            )

            self.logger.info("Procesador en segundo plano inicializado correctamente")
            return True
        except Exception as e:
            self.logger.error(f"Error al inicializar procesador en segundo plano: {e}")
            return False

    def start_background_processing(self):
        """Iniciar procesamiento en segundo plano."""
        if self.background_processor:
            self.background_processor.start()
            self.logger.info("Procesamiento en segundo plano iniciado")
            return True
        else:
            self.logger.error("Procesador en segundo plano no inicializado")
            return False

    def stop_background_processing(self):
        """Detener procesamiento en segundo plano."""
        if self.background_processor:
            self.background_processor.stop()
            self.logger.info("Procesamiento en segundo plano detenido")
            return True
        return False

    def get_system_status(self) -> Dict[str, Any]:
        """
        Obtener estado completo del sistema.

        Returns:
            Diccionario con información del estado del sistema
        """
        status = {
            "database_connected": self.db_manager is not None,
            "object_detector_ready": self.object_detector is not None,
            "background_processor_ready": self.background_processor is not None,
        }

        if self.background_processor:
            status.update(self.background_processor.get_status())

        if self.db_manager:
            try:
                stats = self.db_manager.obtener_estadisticas()
                status["database_stats"] = stats
            except Exception as e:
                self.logger.error(f"Error al obtener estadísticas de BD: {e}")

        return status

    def initialize_all(self) -> bool:
        """
        Inicializar todos los componentes del sistema.

        Returns:
            True si todos los componentes se inicializaron correctamente
        """
        self.logger.info("Iniciando inicialización completa del sistema...")

        success = True

        if not self.initialize_database():
            success = False

        if not self.initialize_object_detector():
            success = False

        if not self.initialize_background_processor():
            success = False

        # Buscar y procesar imágenes nuevas al iniciar
        if success:
            self._buscar_y_procesar_imagenes_nuevas()

        if success:
            self.logger.info("Sistema inicializado correctamente")
        else:
            self.logger.error("Error en la inicialización del sistema")

        return success

    def _buscar_y_procesar_imagenes_nuevas(self):
        """
        Buscar imágenes nuevas y procesarlas completamente.
        """
        try:
            self.logger.info("Buscando imágenes nuevas para procesar...")

            # Importar componentes necesarios
            from src.metadata_extractor import ImageDiscovery, ImageProcessor
            from src.object_detector import ObjectDetector

            # Inicializar componentes
            image_discovery = ImageDiscovery()
            image_processor = ImageProcessor()
            object_detector = ObjectDetector()

            # Buscar imágenes nuevas
            imagenes_nuevas = image_discovery.buscar_imagenes_nuevas(self.db_manager)

            if not imagenes_nuevas:
                self.logger.info("No se encontraron imágenes nuevas")
                return

            self.logger.info(f"Procesando {len(imagenes_nuevas)} imágenes nuevas...")

            # Procesar cada imagen nueva
            for i, metadatos in enumerate(imagenes_nuevas):
                try:
                    ruta_imagen = metadatos["ruta"]

                    # Verificar si la ruta ya existe en la colección antes de procesar
                    if self.db_manager.verificar_ruta_existente(ruta_imagen):
                        self.logger.warning(f"Imagen con ruta {ruta_imagen} ya existe en la colección. Omitiendo procesamiento.")
                        continue

                    # Detectar objetos en la imagen
                    objetos_detectados = object_detector.detectar_objetos(ruta_imagen)

                    # Actualizar metadatos con objetos detectados
                    metadatos["objetos"] = objetos_detectados
                    metadatos["objeto_procesado"] = True

                    # Insertar en la base de datos
                    from src.models import ImagenDocumento
                    documento = ImagenDocumento(**metadatos)
                    doc_id = self.db_manager.insertar_documento(documento)

                    self.logger.info(f"✓ [{i+1}/{len(imagenes_nuevas)}] Procesada imagen {metadatos['nombre']} con {len(objetos_detectados)} objetos")

                except Exception as e:
                    self.logger.error(f"Error al procesar imagen {metadatos.get('nombre', 'unknown')}: {e}")

            self.logger.info("Procesamiento de imágenes nuevas completado")

        except Exception as e:
            self.logger.error(f"Error al buscar y procesar imágenes nuevas: {e}")