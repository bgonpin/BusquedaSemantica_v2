"""
Módulo para manejar la migración de datos de MongoDB a Qdrant.
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

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class MigracionManager:
    """Gestor de migración de datos de MongoDB a Qdrant."""

    def __init__(self, db_manager: DatabaseManager, qdrant_manager: QdrantManager):
        """
        Inicializar el gestor de migración.

        Args:
            db_manager: Gestor de MongoDB
            qdrant_manager: Gestor de Qdrant
        """
        self.db_manager = db_manager
        self.qdrant_manager = qdrant_manager

    def migrar_embeddings_existentes(self, batch_size: int = 100) -> Dict[str, Any]:
        """
        Migrar todos los embeddings existentes de MongoDB a Qdrant.

        Args:
            batch_size: Tamaño del lote para procesamiento por lotes

        Returns:
            Diccionario con estadísticas de la migración
        """
        try:
            logger.info("Iniciando migración de embeddings existentes...")

            # Obtener documentos con embeddings de MongoDB
            documentos_con_embedding = list(self.db_manager.collection.find(
                {"embedding": {"$exists": True, "$ne": None}},
                {"_id": 1, "embedding": 1, "descripcion_semantica": 1}
            ))

            total_documentos = len(documentos_con_embedding)
            logger.info(f"Encontrados {total_documentos} documentos con embeddings en MongoDB")

            if total_documentos == 0:
                return {
                    "total_migrados": 0,
                    "total_omitidos": 0,
                    "total_errores": 0,
                    "mensaje": "No hay documentos con embeddings para migrar"
                }

            # Procesar por lotes
            documentos_migrados = 0
            documentos_omitidos = 0
            documentos_errores = 0

            for i in range(0, total_documentos, batch_size):
                batch = documentos_con_embedding[i:i + batch_size]
                logger.info(f"Procesando lote {i//batch_size + 1}/{(total_documentos-1)//batch_size + 1}")

                for doc in tqdm(batch, desc=f"Migrando lote {i//batch_size + 1}"):
                    try:
                        # Obtener documento completo
                        doc_id = doc["_id"]
                        documento_completo = self.db_manager.obtener_documento_por_id(doc_id)

                        if not documento_completo:
                            logger.warning(f"Documento {doc_id} no encontrado en MongoDB")
                            documentos_omitidos += 1
                            continue

                        # Verificar que tenga embedding y descripción
                        if not doc.get("embedding") or not doc.get("descripcion_semantica"):
                            logger.warning(f"Documento {doc_id} no tiene embedding o descripción completa")
                            documentos_omitidos += 1
                            continue

                        # Migrar a Qdrant
                        self.qdrant_manager.insertar_vector(
                            documento_completo,
                            doc["embedding"],
                            doc["descripcion_semantica"]
                        )

                        documentos_migrados += 1

                    except Exception as e:
                        logger.error(f"Error al migrar documento {doc.get('_id', 'unknown')}: {e}")
                        documentos_errores += 1

                # Pequeña pausa entre lotes para no sobrecargar
                if i + batch_size < total_documentos:
                    time.sleep(1)

            logger.info("Migración completada")

            return {
                "total_migrados": documentos_migrados,
                "total_omitidos": documentos_omitidos,
                "total_errores": documentos_errores,
                "total_procesados": total_documentos,
                "mensaje": f"Migración completada: {documentos_migrados} migrados, {documentos_omitidos} omitidos, {documentos_errores} errores"
            }

        except Exception as e:
            logger.error(f"Error en migración: {e}")
            raise

    def verificar_migracion_completa(self) -> Dict[str, Any]:
        """
        Verificar que la migración se completó correctamente.

        Returns:
            Diccionario con estadísticas de verificación
        """
        try:
            # Obtener estadísticas de MongoDB
            stats_mongodb = self.db_manager.obtener_estadisticas()

            # Obtener estadísticas de Qdrant
            stats_qdrant = self.qdrant_manager.obtener_estadisticas()

            # Comparar
            documentos_con_embedding_mongo = stats_mongodb.get("documentos_con_embedding", 0)
            documentos_qdrant = stats_qdrant.get("total_vectors", 0)

            return {
                "documentos_mongodb": documentos_con_embedding_mongo,
                "documentos_qdrant": documentos_qdrant,
                "migracion_completa": documentos_qdrant >= documentos_con_embedding_mongo,
                "diferencia": documentos_con_embedding_mongo - documentos_qdrant,
                "mensaje": "Migración verificada correctamente" if documentos_qdrant >= documentos_con_embedding_mongo else "Migración incompleta"
            }

        except Exception as e:
            logger.error(f"Error al verificar migración: {e}")
            raise

    def limpiar_qdrant(self):
        """Limpiar completamente la colección de Qdrant."""
        try:
            logger.info("Limpiando colección de Qdrant...")
            self.qdrant_manager.limpiar_coleccion()
            logger.info("Colección de Qdrant limpiada")
        except Exception as e:
            logger.error(f"Error al limpiar Qdrant: {e}")
            raise

    def obtener_documentos_sin_embedding(self, limite: int = 100) -> List[ImagenDocumento]:
        """
        Obtener documentos que no tienen embedding para procesar.

        Args:
            limite: Número máximo de documentos a obtener

        Returns:
            Lista de documentos sin embedding
        """
        try:
            # Buscar documentos sin embedding
            documentos_sin_embedding = list(self.db_manager.collection.find(
                {"embedding": {"$exists": False}},
                {"_id": 1}
            ).limit(limite))

            resultados = []
            for doc in documentos_sin_embedding:
                documento_completo = self.db_manager.obtener_documento_por_id(doc["_id"])
                if documento_completo:
                    resultados.append(documento_completo)

            logger.info(f"Encontrados {len(resultados)} documentos sin embedding")
            return resultados

        except Exception as e:
            logger.error(f"Error al obtener documentos sin embedding: {e}")
            raise

    def sincronizar_documento(self, doc_id: str):
        """
        Sincronizar un documento específico entre MongoDB y Qdrant.

        Args:
            doc_id: ID del documento a sincronizar
        """
        try:
            # Obtener documento de MongoDB
            documento = self.db_manager.obtener_documento_por_id(doc_id)
            if not documento:
                logger.error(f"Documento {doc_id} no encontrado en MongoDB")
                return

            # Verificar si tiene embedding
            if not documento.embedding or not documento.descripcion_semantica:
                logger.warning(f"Documento {doc_id} no tiene embedding o descripción")
                return

            # Verificar si existe en Qdrant
            doc_qdrant = self.qdrant_manager.obtener_por_id(doc_id)

            if doc_qdrant:
                # Actualizar en Qdrant
                self.qdrant_manager.actualizar_vector(
                    doc_id,
                    documento.embedding,
                    documento.descripcion_semantica
                )
                logger.info(f"Documento {doc_id} actualizado en Qdrant")
            else:
                # Insertar en Qdrant
                self.qdrant_manager.insertar_vector(
                    documento,
                    documento.embedding,
                    documento.descripcion_semantica
                )
                logger.info(f"Documento {doc_id} insertado en Qdrant")

        except Exception as e:
            logger.error(f"Error al sincronizar documento {doc_id}: {e}")
            raise