"""
Módulo para detectar objetos en imágenes usando modelos de IA.
"""
import os
import sys
import logging
from typing import List, Dict, Any, Optional
from pathlib import Path
import hashlib

# Importar dependencias para detección de objetos
try:
    from transformers import pipeline
    from PIL import Image
    import torch
    import numpy as np
except ImportError as e:
    logging.error(f"Error al importar dependencias para detección de objetos: {e}")
    raise

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ObjectDetector:
    """Detector de objetos en imágenes usando modelos de IA."""

    def __init__(self, model_name: str = None):
        """
        Inicializar el detector de objetos.

        Args:
            model_name: Nombre del modelo a usar para detección de objetos.
                       Si es None, se elegirá automáticamente el mejor modelo disponible.
        """
        # Elegir modelo automáticamente basado en disponibilidad de timm
        if model_name is None:
            try:
                import timm
                self.model_name = "facebook/detr-resnet-50"  # Modelo que requiere timm
                logger.info("Usando modelo DETR (requiere timm)")
            except ImportError:
                self.model_name = "hustvl/yolos-tiny"  # Modelo alternativo sin timm
                logger.info("Usando modelo YOLOS (no requiere timm)")
        else:
            self.model_name = model_name

        self.detector = None
        self._initialize_detector()

    def _initialize_detector(self):
        """Inicializar el pipeline de detección de objetos."""
        try:
            logger.info(f"Inicializando detector de objetos con modelo: {self.model_name}")

            # Configurar dispositivo (CPU para evitar problemas CUDA)
            device = "cpu"
            if torch.cuda.is_available():
                device = "cuda:0"
            elif torch.backends.mps.is_available():
                device = "mps"

            # Verificar si el modelo requiere timm y si está disponible
            if self.model_name == "facebook/detr-resnet-50":
                try:
                    import timm
                    logger.info("Librería timm disponible para modelo DETR")
                except ImportError:
                    logger.warning("Librería timm no disponible, cambiando a modelo alternativo")
                    self.model_name = "hustvl/yolos-tiny"

            # Inicializar el pipeline de detección de objetos
            model_kwargs = {"ignore_mismatched_sizes": True} if self.model_name == "facebook/detr-resnet-50" else {}

            self.detector = pipeline(
                "object-detection",
                model=self.model_name,
                device=device,
                model_kwargs=model_kwargs
            )

            logger.info(f"Detector de objetos inicializado correctamente en {device}")

        except Exception as e:
            logger.error(f"Error al inicializar detector de objetos: {e}")
            # Intentar con un modelo alternativo más ligero
            try:
                logger.info("Intentando con modelo alternativo...")
                self.model_name = "hustvl/yolos-tiny"
                self.detector = pipeline(
                    "object-detection",
                    model=self.model_name,
                    device="cpu"
                )
                logger.info("Detector alternativo inicializado correctamente")
            except Exception as e2:
                logger.error(f"Error al inicializar detector alternativo: {e2}")
                raise

    def detectar_objetos(self, imagen_path: str, confianza_minima: float = 0.5) -> List[str]:
        """
        Detectar objetos en una imagen.

        Args:
            imagen_path: Ruta a la imagen a analizar
            confianza_minima: Umbral mínimo de confianza para considerar un objeto

        Returns:
            Lista de nombres de objetos detectados
        """
        try:
            if not self.detector:
                raise Exception("Detector no inicializado")

            if not os.path.exists(imagen_path):
                logger.warning(f"Imagen no encontrada: {imagen_path}")
                return []

            # Cargar imagen
            imagen = Image.open(imagen_path)

            # Realizar detección de objetos
            resultados = self.detector(
                imagen,
                threshold=confianza_minima
            )

            # Extraer nombres de objetos únicos
            objetos_detectados = []
            for resultado in resultados:
                objeto = resultado.get("label", "").lower().strip()
                if objeto and objeto not in objetos_detectados:
                    objetos_detectados.append(objeto)

            logger.info(f"Detectados {len(objetos_detectados)} objetos en {imagen_path}: {objetos_detectados}")
            return objetos_detectados

        except Exception as e:
            logger.error(f"Error al detectar objetos en {imagen_path}: {e}")
            return []

    def generar_hash_imagen(self, imagen_path: str) -> str:
        """
        Generar hash único para una imagen.

        Args:
            imagen_path: Ruta a la imagen

        Returns:
            Hash SHA256 de la imagen
        """
        try:
            if not os.path.exists(imagen_path):
                return ""

            hash_sha256 = hashlib.sha256()
            with open(imagen_path, "rb") as f:
                for chunk in iter(lambda: f.read(4096), b""):
                    hash_sha256.update(chunk)
            return hash_sha256.hexdigest()

        except Exception as e:
            logger.error(f"Error al generar hash de imagen {imagen_path}: {e}")
            return ""


class BackgroundObjectProcessor:
    """Procesador de objetos en segundo plano."""

    def __init__(self, db_manager, detector: ObjectDetector):
        """
        Inicializar el procesador en segundo plano.

        Args:
            db_manager: Gestor de base de datos
            detector: Detector de objetos
        """
        self.db_manager = db_manager
        self.detector = detector
        self.procesando = False
        self.logger = logging.getLogger(__name__)

    def procesar_imagenes_sin_objetos(self, batch_size: int = 10) -> Dict[str, Any]:
        """
        Procesar imágenes que no tienen objetos detectados.

        Args:
            batch_size: Tamaño del lote para procesamiento. Si es muy grande (>1000),
                       procesa toda la colección

        Returns:
            Diccionario con estadísticas del procesamiento
        """
        try:
            self.procesando = True
            self.logger.info("Iniciando procesamiento de imágenes sin objetos en segundo plano")

            # Buscar documentos sin objetos o con objetos vacíos
            query = {
                "$or": [
                    {"objetos": {"$exists": False}},
                    {"objetos": {"$size": 0}},
                    {"objeto_procesado": False}
                ]
            }

            # Si batch_size es muy grande (>1000), procesar toda la colección
            if batch_size > 1000:
                self.logger.info(f"Procesando toda la colección ({batch_size} documentos solicitados)")
                documentos_sin_procesar = list(self.db_manager.collection.find(query))
                max_docs = len(documentos_sin_procesar)
            else:
                # Procesar en lotes más pequeños para evitar sobrecarga de memoria
                documentos_sin_procesar = list(self.db_manager.collection.find(query).limit(batch_size))
                max_docs = batch_size

            if not documentos_sin_procesar:
                self.logger.info("No hay imágenes pendientes de procesar")
                return {
                    "procesadas": 0,
                    "errores": 0,
                    "sin_archivo": 0,
                    "mensaje": "No hay imágenes pendientes de procesar"
                }

            estadisticas = {
                "procesadas": 0,
                "errores": 0,
                "sin_archivo": 0
            }

            total_documentos = len(documentos_sin_procesar)
            self.logger.info(f"Procesando {total_documentos} imágenes...")

            for i, documento_data in enumerate(documentos_sin_procesar):
                try:
                    # Convertir a objeto ImagenDocumento
                    from src.models import ImagenDocumento
                    documento = ImagenDocumento(**documento_data)

                    # Verificar que la imagen existe
                    if not os.path.exists(documento.ruta):
                        self.logger.warning(f"Archivo no encontrado: {documento.ruta}")
                        estadisticas["sin_archivo"] += 1
                        continue

                    # Detectar objetos en la imagen
                    objetos_detectados = self.detector.detectar_objetos(documento.ruta)

                    if objetos_detectados:
                        # Actualizar documento con objetos detectados
                        self.db_manager.collection.update_one(
                            {"_id": documento.id},
                            {
                                "$set": {
                                    "objetos": objetos_detectados,
                                    "objeto_procesado": True
                                }
                            }
                        )
                        self.logger.info(f"✓ [{i+1}/{total_documentos}] Actualizada imagen {documento.nombre} con {len(objetos_detectados)} objetos")
                        estadisticas["procesadas"] += 1
                    else:
                        # Marcar como procesado aunque no se detectaron objetos
                        self.db_manager.collection.update_one(
                            {"_id": documento.id},
                            {"$set": {"objeto_procesado": True}}
                        )
                        self.logger.info(f"✓ [{i+1}/{total_documentos}] Procesada imagen {documento.nombre} (sin objetos detectados)")
                        estadisticas["procesadas"] += 1

                except Exception as e:
                    self.logger.error(f"✗ [{i+1}/{total_documentos}] Error al procesar documento {documento_data.get('_id', 'unknown')}: {e}")
                    estadisticas["errores"] += 1

            self.logger.info(f"Procesamiento completado: {estadisticas}")
            return estadisticas

        except Exception as e:
            self.logger.error(f"Error en procesamiento en segundo plano: {e}")
            return {
                "procesadas": 0,
                "errores": 1,
                "sin_archivo": 0,
                "mensaje": f"Error: {str(e)}"
            }
        finally:
            self.procesando = False

    def esta_procesando(self) -> bool:
        """Verificar si el procesador está activo."""
        return self.procesando

    def detener_procesamiento(self):
        """Detener el procesamiento actual."""
        self.procesando = False
        self.logger.info("Procesamiento detenido por el usuario")