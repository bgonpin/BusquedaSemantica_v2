"""
Módulo para manejar la conexión y operaciones con Qdrant.
"""
import os
import sys
import logging
import json
import hashlib
from datetime import datetime
from typing import List, Dict, Any, Optional, Tuple
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct, Filter, FieldCondition, MatchValue
from qdrant_client.http.exceptions import UnexpectedResponse

# Añadir el directorio raíz al path para permitir importaciones absolutas
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.models import ImagenDocumento, ConsultaBusqueda, ResultadoBusqueda

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class QdrantManager:
    """Gestor de conexión y operaciones con Qdrant."""

    def __init__(self):
        """Inicializar la conexión a Qdrant."""
        self.client: Optional[QdrantClient] = None
        self.collection_name: str = "imagenes_semanticas"
        self._connect()

    def _connect(self):
        """Establecer conexión con Qdrant."""
        try:
            # Obtener configuración desde variables de entorno
            qdrant_url = os.getenv('QDRANT_URL', 'http://localhost:6333')
            api_key = os.getenv('QDRANT_API_KEY', None)

            # Crear cliente Qdrant
            if api_key:
                self.client = QdrantClient(url=qdrant_url, api_key=api_key)
            else:
                self.client = QdrantClient(url=qdrant_url)

            # Verificar conexión
            try:
                # Intentar obtener información de colecciones para verificar conexión
                self.client.get_collections()
                logger.info(f"Conexión exitosa a Qdrant: {qdrant_url}")
            except Exception as conn_error:
                logger.warning(f"Error al verificar conexión con Qdrant: {conn_error}")
                # No lanzar error aquí, permitir que continúe

            # Crear colección si no existe
            self._ensure_collection()

        except Exception as e:
            logger.error(f"Error al conectar a Qdrant: {e}")
            raise

    def _ensure_collection(self):
        """Asegurar que la colección existe con la configuración correcta."""
        try:
            # Dimensiones del embedding (usando embeddinggemma que tiene 768 dimensiones)
            vector_size = 768

            # Verificar si la colección existe
            collections = self.client.get_collections()
            collection_exists = any(col.name == self.collection_name for col in collections.collections)

            if not collection_exists:
                # Crear colección
                self.client.create_collection(
                    collection_name=self.collection_name,
                    vectors_config=VectorParams(size=vector_size, distance=Distance.COSINE)
                )
                logger.info(f"Colección '{self.collection_name}' creada exitosamente con {vector_size} dimensiones")
            else:
                # Verificar si la colección existente tiene la dimensionalidad correcta
                try:
                    collection_info = self.client.get_collection(self.collection_name)
                    existing_size = collection_info.config.params.vectors.size

                    if existing_size != vector_size:
                        logger.warning(f"La colección existente tiene {existing_size} dimensiones, pero el modelo actual requiere {vector_size}")
                        logger.info("Recreando colección con la dimensionalidad correcta...")

                        # Eliminar y recrear la colección
                        self.client.delete_collection(self.collection_name)
                        self.client.create_collection(
                            collection_name=self.collection_name,
                            vectors_config=VectorParams(size=vector_size, distance=Distance.COSINE)
                        )
                        logger.info(f"Colección '{self.collection_name}' recreada con {vector_size} dimensiones")
                    else:
                        logger.info(f"Colección '{self.collection_name}' ya existe con {vector_size} dimensiones correctas")
                except Exception as e:
                    logger.warning(f"Error al verificar dimensionalidad de la colección: {e}")
                    logger.info("Continuando con la colección existente...")

        except Exception as e:
            logger.error(f"Error al verificar/crear colección: {e}")
            raise

    def insertar_vector(self, documento: ImagenDocumento, embedding: List[float], descripcion: str) -> str:
        """
        Insertar un vector en la colección de Qdrant.

        Args:
            documento: Documento de imagen
            embedding: Vector de embedding
            descripcion: Descripción semántica

        Returns:
            ID del punto insertado
        """
        try:
            # Crear ID numérico para Qdrant (basado en hash del id_hash)
            # Qdrant no acepta strings largos como IDs, usar solo primeros 8 caracteres del hash
            import hashlib
            hash_md5 = hashlib.md5(documento.id_hash.encode()).hexdigest()
            id_numerico = int(hash_md5[:8], 16)  # Usar solo primeros 8 caracteres (32 bits)

            # Crear payload con TODOS los campos del documento
            payload = {
                # Identificadores
                "id": documento.id,
                "id_hash": documento.id_hash,
                "hash_sha512": documento.hash_sha512,

                # Información del archivo
                "nombre": documento.nombre,
                "ruta": documento.ruta,
                "ruta_alternativa": documento.ruta_alternativa,

                # Dimensiones y peso
                "ancho": documento.ancho,
                "alto": documento.alto,
                "peso": documento.peso,

                # Fechas de creación (formato completo e individual)
                "fecha_creacion": documento.get_fecha_creacion(),
                "fecha_creacion_dia": documento.fecha_creacion_dia,
                "fecha_creacion_mes": documento.fecha_creacion_mes,
                "fecha_creacion_anio": documento.fecha_creacion_anio,
                "fecha_creacion_hora": documento.fecha_creacion_hora,
                "fecha_creacion_minuto": documento.fecha_creacion_minuto,

                # Fechas de procesamiento (formato completo e individual)
                "fecha_procesamiento": documento.get_fecha_procesamiento(),
                "fecha_procesamiento_dia": documento.fecha_procesamiento_dia,
                "fecha_procesamiento_mes": documento.fecha_procesamiento_mes,
                "fecha_procesamiento_anio": documento.fecha_procesamiento_anio,
                "fecha_procesamiento_hora": documento.fecha_procesamiento_hora,
                "fecha_procesamiento_minuto": documento.fecha_procesamiento_minuto,

                # Ubicación geográfica
                "coordenadas": documento.coordenadas,
                "barrio": documento.barrio,
                "calle": documento.calle,
                "ciudad": documento.ciudad,
                "cp": documento.cp,
                "pais": documento.pais,

                # Estado de procesamiento
                "objeto_procesado": documento.objeto_procesado,

                # Objetos y personas detectados
                "objetos": documento.objetos,
                "personas": documento.personas,

                # Información semántica
                "descripcion_semantica": descripcion,
                "embedding": embedding  # Incluir el embedding para referencia
            }

            # Crear punto
            point = PointStruct(
                id=id_numerico,
                vector=embedding,
                payload=payload
            )

            # Insertar punto
            result = self.client.upsert(
                collection_name=self.collection_name,
                points=[point]
            )

            logger.info(f"Vector insertado para documento {documento.id_hash} (ID: {id_numerico})")
            return str(id_numerico)

        except Exception as e:
            logger.error(f"Error al insertar vector: {e}")
            raise

    def buscar_similares(self, embedding: List[float], limite: int = 10,
                        umbral_similitud: float = 0.7, filtros: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """
        Buscar vectores similares en Qdrant.

        Args:
            embedding: Vector de consulta
            limite: Número máximo de resultados
            umbral_similitud: Umbral mínimo de similitud
            filtros: Filtros adicionales

        Returns:
            Lista de documentos similares con sus puntuaciones
        """
        try:
            # Crear filtros si existen
            qdrant_filter = None
            if filtros:
                conditions = []
                for campo, valor in filtros.items():
                    if isinstance(valor, str):
                        conditions.append(
                            FieldCondition(
                                key=campo,
                                match=MatchValue(value=valor)
                            )
                        )
                    elif isinstance(valor, list):
                        # Para campos como objetos o personas
                        for item in valor:
                            conditions.append(
                                FieldCondition(
                                    key=campo,
                                    match=MatchValue(value=item)
                                )
                            )

                if conditions:
                    qdrant_filter = Filter(should=conditions)

            # Realizar búsqueda
            search_result = self.client.search(
                collection_name=self.collection_name,
                query_vector=embedding,
                limit=limite,
                score_threshold=umbral_similitud,
                query_filter=qdrant_filter
            )

            # Convertir resultados
            resultados = []
            for point in search_result:
                resultado = {
                    "id": point.id,
                    "score": point.score,
                    "payload": point.payload
                }
                resultados.append(resultado)

            logger.info(f"Búsqueda completada. {len(resultados)} resultados encontrados.")
            return resultados

        except Exception as e:
            logger.error(f"Error en búsqueda: {e}")
            raise

    def obtener_por_id(self, doc_id: str) -> Optional[Dict[str, Any]]:
        """
        Obtener un documento por su ID.

        Args:
            doc_id: ID del documento (id_hash original)

        Returns:
            Documento encontrado o None
        """
        try:
            # Convertir id_hash a ID numérico
            import hashlib
            hash_md5 = hashlib.md5(doc_id.encode()).hexdigest()
            id_numerico = int(hash_md5[:8], 16)  # Usar solo primeros 8 caracteres (32 bits)

            points = self.client.retrieve(
                collection_name=self.collection_name,
                ids=[id_numerico]
            )

            if points:
                point = points[0]
                return {
                    "id": point.id,
                    "payload": point.payload
                }
            return None

        except Exception as e:
            logger.error(f"Error al obtener documento por ID: {e}")
            raise

    def actualizar_vector(self, doc_id: str, embedding: List[float], descripcion: str):
        """
        Actualizar un vector existente.

        Args:
            doc_id: ID del documento (id_hash original)
            embedding: Nuevo vector de embedding
            descripcion: Nueva descripción semántica
        """
        try:
            # Convertir id_hash a ID numérico
            import hashlib
            hash_md5 = hashlib.md5(doc_id.encode()).hexdigest()
            id_numerico = int(hash_md5[:8], 16)  # Usar solo primeros 8 caracteres (32 bits)

            # Crear nuevo punto con datos actualizados
            point = PointStruct(
                id=id_numerico,
                vector=embedding,
                payload={"descripcion_semantica": descripcion}
            )

            # Actualizar punto
            self.client.upsert(
                collection_name=self.collection_name,
                points=[point]
            )

            logger.info(f"Vector actualizado para documento {doc_id} (ID: {id_numerico})")

        except Exception as e:
            logger.error(f"Error al actualizar vector: {e}")
            raise

    def eliminar_vector(self, doc_id: str):
        """
        Eliminar un vector de la colección.

        Args:
            doc_id: ID del documento a eliminar (id_hash original)
        """
        try:
            # Convertir id_hash a ID numérico
            import hashlib
            id_numerico = int(hashlib.md5(doc_id.encode()).hexdigest(), 16)

            self.client.delete(
                collection_name=self.collection_name,
                points_selector=[id_numerico]
            )
            logger.info(f"Vector eliminado para documento {doc_id} (ID: {id_numerico})")

        except Exception as e:
            logger.error(f"Error al eliminar vector: {e}")
            raise

    def obtener_estadisticas(self) -> Dict[str, Any]:
        """
        Obtener estadísticas de la colección.

        Returns:
            Diccionario con estadísticas
        """
        try:
            # Obtener información de la colección
            collection_info = self.client.get_collection(self.collection_name)

            return {
                "total_vectors": collection_info.points_count,
                "collection_name": self.collection_name,
                "vector_size": collection_info.config.params.vectors.size,
                "distance": collection_info.config.params.vectors.distance
            }

        except Exception as e:
            logger.error(f"Error al obtener estadísticas: {e}")
            raise

    def limpiar_coleccion(self):
        """Eliminar todos los vectores de la colección."""
        try:
            self.client.delete_collection(self.collection_name)
            logger.info("Colección limpiada completamente")

            # Recreate collection
            self._ensure_collection()

        except Exception as e:
            logger.error(f"Error al limpiar colección: {e}")
            raise

    def crear_backup_coleccion(self, ruta_backup: str) -> Dict[str, Any]:
        """
        Crear una copia de seguridad de toda la colección.

        Args:
            ruta_backup: Ruta donde guardar el archivo de backup

        Returns:
            Diccionario con información del backup creado
        """
        try:
            logger.info(f"Iniciando backup de la colección '{self.collection_name}' en: {ruta_backup}")

            # Obtener información de la colección
            collection_info = self.client.get_collection(self.collection_name)

            # Obtener todos los puntos de la colección
            # Usar scroll para manejar grandes cantidades de datos
            all_points = []
            offset = None
            limit = 1000  # Procesar en lotes

            while True:
                response, offset = self.client.scroll(
                    collection_name=self.collection_name,
                    limit=limit,
                    offset=offset,
                    with_payload=True,
                    with_vectors=True
                )

                if not response:
                    break

                all_points.extend(response)

                # Si no hay más puntos, salir del bucle
                if offset is None:
                    break

            logger.info(f"Total de vectores obtenidos: {len(all_points)}")

            # Crear estructura del backup
            backup_data = {
                "metadata": {
                    "collection_name": self.collection_name,
                    "backup_date": datetime.now().isoformat(),
                    "total_vectors": len(all_points),
                    "vector_size": collection_info.config.params.vectors.size,
                    "distance": collection_info.config.params.vectors.distance,
                    "qdrant_version": "1.0"  # Versión del formato de backup
                },
                "vectors": []
            }

            # Procesar cada punto
            for point in all_points:
                vector_data = {
                    "id": point.id,
                    "vector": point.vector,
                    "payload": point.payload
                }
                backup_data["vectors"].append(vector_data)

            # Guardar backup en archivo JSON
            with open(ruta_backup, 'w', encoding='utf-8') as f:
                json.dump(backup_data, f, indent=2, ensure_ascii=False)

            # Calcular hash del archivo para verificación
            sha256_hash = hashlib.sha256()
            with open(ruta_backup, 'rb') as f:
                for byte_block in iter(lambda: f.read(4096), b""):
                    sha256_hash.update(byte_block)

            backup_info = {
                "ruta_archivo": ruta_backup,
                "total_vectores": len(all_points),
                "tamano_archivo": os.path.getsize(ruta_backup),
                "hash_sha256": sha256_hash.hexdigest(),
                "fecha_backup": backup_data["metadata"]["backup_date"]
            }

            logger.info(f"Backup creado exitosamente: {backup_info}")
            return backup_info

        except Exception as e:
            logger.error(f"Error al crear backup: {e}")
            raise

    def restaurar_coleccion(self, ruta_backup: str, recrear_coleccion: bool = True) -> Dict[str, Any]:
        """
        Restaurar la colección desde un archivo de backup.

        Args:
            ruta_backup: Ruta del archivo de backup
            recrear_coleccion: Si es True, elimina y recrea la colección antes de restaurar

        Returns:
            Diccionario con información de la restauración
        """
        try:
            logger.info(f"Iniciando restauración desde: {ruta_backup}")

            # Verificar que el archivo existe
            if not os.path.exists(ruta_backup):
                raise FileNotFoundError(f"Archivo de backup no encontrado: {ruta_backup}")

            # Leer archivo de backup
            with open(ruta_backup, 'r', encoding='utf-8') as f:
                backup_data = json.load(f)

            # Validar estructura del backup
            if "metadata" not in backup_data or "vectors" not in backup_data:
                raise ValueError("Formato de backup inválido")

            metadata = backup_data["metadata"]
            vectors_data = backup_data["vectors"]

            logger.info(f"Backup metadata: {metadata}")
            logger.info(f"Total de vectores a restaurar: {len(vectors_data)}")

            # Si se solicita recrear la colección
            if recrear_coleccion:
                logger.info("Recreando colección...")
                self.client.delete_collection(self.collection_name)
                self._ensure_collection()

            # Preparar puntos para inserción
            points = []
            for vector_data in vectors_data:
                point = PointStruct(
                    id=vector_data["id"],
                    vector=vector_data["vector"],
                    payload=vector_data["payload"]
                )
                points.append(point)

            # Insertar puntos en lotes para mejor rendimiento
            batch_size = 100
            total_insertados = 0

            for i in range(0, len(points), batch_size):
                batch = points[i:i + batch_size]

                self.client.upsert(
                    collection_name=self.collection_name,
                    points=batch
                )

                total_insertados += len(batch)
                logger.info(f"Insertados {total_insertados}/{len(points)} vectores")

            # Verificar restauración
            collection_info = self.client.get_collection(self.collection_name)

            restauracion_info = {
                "ruta_backup": ruta_backup,
                "total_vectores_restaurados": len(points),
                "total_vectores_en_coleccion": collection_info.points_count,
                "fecha_restauracion": datetime.now().isoformat(),
                "metadata_backup": metadata
            }

            logger.info(f"Restauración completada: {restauracion_info}")
            return restauracion_info

        except Exception as e:
            logger.error(f"Error al restaurar backup: {e}")
            raise

    def validar_backup(self, ruta_backup: str) -> Dict[str, Any]:
        """
        Validar la integridad de un archivo de backup.

        Args:
            ruta_backup: Ruta del archivo de backup

        Returns:
            Diccionario con información de validación
        """
        try:
            logger.info(f"Validando backup: {ruta_backup}")

            # Verificar que el archivo existe
            if not os.path.exists(ruta_backup):
                return {
                    "valido": False,
                    "error": "Archivo no encontrado",
                    "ruta": ruta_backup
                }

            # Leer y validar estructura JSON
            try:
                with open(ruta_backup, 'r', encoding='utf-8') as f:
                    backup_data = json.load(f)
            except json.JSONDecodeError as e:
                return {
                    "valido": False,
                    "error": f"Error de formato JSON: {str(e)}",
                    "ruta": ruta_backup
                }

            # Validar estructura requerida
            if "metadata" not in backup_data or "vectors" not in backup_data:
                return {
                    "valido": False,
                    "error": "Estructura de backup inválida",
                    "ruta": ruta_backup
                }

            metadata = backup_data["metadata"]
            vectors_data = backup_data["vectors"]

            # Validar campos requeridos en metadata
            campos_requeridos = ["collection_name", "backup_date", "total_vectors", "vector_size"]
            for campo in campos_requeridos:
                if campo not in metadata:
                    return {
                        "valido": False,
                        "error": f"Campo requerido faltante en metadata: {campo}",
                        "ruta": ruta_backup
                    }

            # Validar que el número de vectores coincida
            if len(vectors_data) != metadata["total_vectors"]:
                return {
                    "valido": False,
                    "error": f"Inconsistencia: metadata indica {metadata['total_vectors']} vectores pero archivo contiene {len(vectors_data)}",
                    "ruta": ruta_backup
                }

            # Calcular hash del archivo para verificación
            sha256_hash = hashlib.sha256()
            with open(ruta_backup, 'rb') as f:
                for byte_block in iter(lambda: f.read(4096), b""):
                    sha256_hash.update(byte_block)

            validacion_info = {
                "valido": True,
                "ruta": ruta_backup,
                "tamano_archivo": os.path.getsize(ruta_backup),
                "hash_sha256": sha256_hash.hexdigest(),
                "metadata": metadata,
                "total_vectores": len(vectors_data),
                "fecha_backup": metadata.get("backup_date", "Desconocida")
            }

            logger.info(f"Validación exitosa: {validacion_info}")
            return validacion_info

        except Exception as e:
            logger.error(f"Error al validar backup: {e}")
            return {
                "valido": False,
                "error": str(e),
                "ruta": ruta_backup
            }

    def cerrar_conexion(self):
        """Cerrar la conexión a Qdrant."""
        if self.client:
            self.client.close()
            logger.info("Conexión a Qdrant cerrada")

    def __del__(self):
        """Destructor para asegurar que la conexión se cierre."""
        self.cerrar_conexion()