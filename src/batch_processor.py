"""
Procesador por lotes para generar embeddings de toda la colección MongoDB.
"""
import os
import sys
import logging
from typing import List, Dict, Any, Optional, Tuple
import time
from tqdm import tqdm

# Añadir el directorio raíz al path para permitir importaciones absolutas
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.models import ImagenDocumento
from src.database import DatabaseManager
from src.qdrant_manager import QdrantManager
from src.busqueda_semantica import BuscadorSemantico

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class BatchProcessor:
    """Procesador por lotes para generar embeddings de toda la colección."""

    def __init__(self, db_manager: DatabaseManager, qdrant_manager: QdrantManager):
        """
        Inicializar el procesador por lotes.

        Args:
            db_manager: Gestor de MongoDB
            qdrant_manager: Gestor de Qdrant
        """
        self.db_manager = db_manager
        self.qdrant_manager = qdrant_manager
        self.buscador = BuscadorSemantico(db_manager, qdrant_manager)


    def procesar_coleccion_completa(self, batch_size: int = 50, max_documentos: Optional[int] = None, cancel_callback=None) -> Dict[str, Any]:
        """
        Procesar toda la colección para generar embeddings.

        Args:
            batch_size: Tamaño del lote para procesamiento
            max_documentos: Límite máximo de documentos a procesar (None = todos)
            cancel_callback: Callback para verificar si se debe cancelar

        Returns:
            Diccionario con estadísticas del procesamiento
        """
        # Si no se proporciona callback, crear uno que siempre retorne False
        if cancel_callback is None:
            cancel_callback = lambda: False
        """
        Procesar toda la colección para generar embeddings.

        Args:
            batch_size: Tamaño del lote para procesamiento
            max_documentos: Límite máximo de documentos a procesar (None = todos)

        Returns:
            Diccionario con estadísticas del procesamiento
        """
        try:
            logger.info("Iniciando procesamiento completo de la colección...")

            # Obtener documentos sin procesar (que no están en Qdrant)
            documentos_sin_procesar = self._obtener_documentos_sin_embedding(max_documentos)

            total_documentos = len(documentos_sin_procesar)
            logger.info(f"Encontrados {total_documentos} documentos sin embedding")

            if total_documentos == 0:
                return {
                    "total_procesados": 0,
                    "total_exitosos": 0,
                    "total_errores": 0,
                    "mensaje": "No hay documentos para procesar"
                }

            # Procesar por lotes
            documentos_procesados = 0
            documentos_exitosos = 0
            documentos_errores = 0

            for i in range(0, total_documentos, batch_size):
                # Verificar cancelación antes de cada lote
                if cancel_callback and cancel_callback():
                    logger.info(f"🚫 CANCELACIÓN DETECTADA - Procesamiento cancelado por el usuario. Progreso: {documentos_exitosos}/{total_documentos} documentos procesados")
                    logger.info(f"🚫 CANCELACIÓN DETECTADA - Documentos procesados en este lote: {documentos_procesados}")
                    logger.info(f"🚫 CANCELACIÓN DETECTADA - Retornando resultado de cancelación")
                    return {
                        "total_procesados": documentos_procesados,
                        "total_exitosos": documentos_exitosos,
                        "total_errores": documentos_errores,
                        "cancelado": True,
                        "mensaje": f"Procesamiento cancelado: {documentos_exitosos} exitosos, {documentos_errores} errores"
                    }

                batch = documentos_sin_procesar[i:i + batch_size]
                logger.info(f"Procesando lote {i//batch_size + 1}/{(total_documentos-1)//batch_size + 1} - {len(batch)} documentos")

                for documento in tqdm(batch, desc=f"Procesando lote {i//batch_size + 1}"):
                    # Verificar cancelación antes de procesar cada documento
                    if cancel_callback and cancel_callback():
                        logger.info(f"🚫 CANCELACIÓN DETECTADA - Procesamiento cancelado durante procesamiento de documento: {documento.nombre}")
                        logger.info(f"🚫 CANCELACIÓN DETECTADA - Retornando resultado de cancelación")
                        return {
                            "total_procesados": documentos_procesados,
                            "total_exitosos": documentos_exitosos,
                            "total_errores": documentos_errores,
                            "cancelado": True,
                            "mensaje": f"Procesamiento cancelado: {documentos_exitosos} exitosos, {documentos_errores} errores"
                        }

                    try:
                        logger.debug(f"Procesando documento: {documento.nombre}")

                        # Procesar documento
                        logger.debug(f"Iniciando procesamiento de: {documento.nombre}")
                        documento_procesado = self.buscador.procesar_documento(documento, cancel_callback)
                        documentos_exitosos += 1
                        logger.debug(f"✓ Procesado: {documento.nombre}")

                        # Marcar como insertado en Qdrant
                        if documento_procesado:
                            try:
                                self.db_manager.collection.update_one(
                                    {"_id": documento.id},
                                    {"$set": {"qdrant": True}}
                                )
                                logger.debug(f"✓ Marcado como insertado en Qdrant: {documento.nombre}")
                            except Exception as e:
                                logger.warning(f"Error al marcar qdrant para documento {documento.id}: {e}")

                    except Exception as e:
                        logger.error(f"✗ Error procesando {documento.nombre}: {str(e)}")
                        documentos_errores += 1

                documentos_procesados += len(batch)

                # Pequeña pausa entre lotes para no sobrecargar
                if i + batch_size < total_documentos:
                    time.sleep(2)

            logger.info("Procesamiento completado")

            return {
                "total_procesados": documentos_procesados,
                "total_exitosos": documentos_exitosos,
                "total_errores": documentos_errores,
                "mensaje": f"Procesamiento completado: {documentos_exitosos} exitosos, {documentos_errores} errores"
            }

        except Exception as e:
            logger.error(f"Error en procesamiento por lotes: {e}")
            raise

    def _obtener_documentos_sin_embedding(self, limite: Optional[int] = None) -> List[ImagenDocumento]:
        """
        Obtener documentos que no tienen embedding.

        Args:
            limite: Límite de documentos a obtener

        Returns:
            Lista de documentos sin embedding
        """
        try:
            # Buscar documentos sin embedding o sin descripción semántica
            # y que no hayan sido insertados en Qdrant (qdrant != true)
            query = {
                "$and": [
                    {
                        "$or": [
                            {"embedding": {"$exists": False}},
                            {"descripcion_semantica": {"$exists": False}},
                            {"objeto_procesado": False}
                        ]
                    },
                    {
                        "$or": [
                            {"qdrant": {"$exists": False}},
                            {"qdrant": False}
                        ]
                    }
                ]
            }

            if limite:
                documentos = list(self.db_manager.collection.find(query).limit(limite))
            else:
                documentos = list(self.db_manager.collection.find(query))

            # Convertir a objetos ImagenDocumento
            resultados = []
            for doc_data in documentos:
                try:
                    documento = ImagenDocumento(**doc_data)
                    # Asegurar que el documento tenga id_hash
                    documento.ensure_id_hash()
                    resultados.append(documento)
                except Exception as e:
                    logger.warning(f"Error al convertir documento {doc_data.get('_id')}: {e}")
                    continue

            logger.info(f"Obtenidos {len(resultados)} documentos sin procesar")
            return resultados

        except Exception as e:
            logger.error(f"Error al obtener documentos sin embedding: {e}")
            raise

    def obtener_estadisticas_coleccion(self) -> Dict[str, Any]:
        """
        Obtener estadísticas completas de la colección.

        Returns:
            Diccionario con estadísticas
        """
        try:
            # Estadísticas de MongoDB
            stats_mongodb = self.db_manager.obtener_estadisticas()

            # Estadísticas de Qdrant
            stats_qdrant = self.qdrant_manager.obtener_estadisticas()

            # Calcular estadísticas adicionales
            documentos_totales = stats_mongodb.get('total_documentos', 0)
            documentos_con_embedding = stats_mongodb.get('documentos_con_embedding', 0)
            documentos_en_qdrant = stats_qdrant.get('total_vectors', 0)

            return {
                "mongodb": {
                    "total_documentos": documentos_totales,
                    "documentos_procesados": stats_mongodb.get('documentos_procesados', 0),
                    "documentos_con_embedding": documentos_con_embedding,
                    "tasa_procesamiento": stats_mongodb.get('tasa_procesamiento', 0)
                },
                "qdrant": {
                    "total_vectores": documentos_en_qdrant,
                    "collection_name": stats_qdrant.get('collection_name', 'imagenes_semanticas'),
                    "vector_size": stats_qdrant.get('vector_size', 384),
                    "distance": stats_qdrant.get('distance', 'Cosine')
                },
                "resumen": {
                    "documentos_pendientes": documentos_totales - documentos_con_embedding,
                    "sincronizado": documentos_con_embedding == documentos_en_qdrant,
                    "completitud": (documentos_con_embedding / documentos_totales * 100) if documentos_totales > 0 else 0
                }
            }

        except Exception as e:
            logger.error(f"Error al obtener estadísticas: {e}")
            raise

    def sincronizar_todo(self) -> Dict[str, Any]:
        """
        Sincronizar completamente MongoDB con Qdrant.

        Returns:
            Diccionario con resultado de la sincronización
        """
        try:
            logger.info("Iniciando sincronización completa...")

            # 1. Procesar documentos sin embedding
            logger.info("Paso 1: Procesando documentos sin embedding...")
            resultado_procesamiento = self.procesar_coleccion_completa()

            # 2. Migrar embeddings existentes que no estén en Qdrant
            logger.info("Paso 2: Migrando embeddings existentes...")
            from src.migracion_manager import MigracionManager
            migracion_manager = MigracionManager(self.db_manager, self.qdrant_manager)
            resultado_migracion = migracion_manager.migrar_embeddings_existentes(batch_size=100)

            # 3. Verificar sincronización
            logger.info("Paso 3: Verificando sincronización...")
            stats = self.obtener_estadisticas_coleccion()

            return {
                "procesamiento": resultado_procesamiento,
                "migracion": resultado_migracion,
                "estadisticas_finales": stats,
                "sincronizado": stats['resumen']['sincronizado']
            }

        except Exception as e:
            logger.error(f"Error en sincronización: {e}")
            raise
