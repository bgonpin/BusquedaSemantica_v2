"""
Módulo para manejar la conexión y operaciones con MongoDB.
"""
import os
import sys
import logging
import json
import hashlib
from datetime import datetime
from typing import List, Dict, Any, Optional
from pymongo import MongoClient
from pymongo.collection import Collection
from pymongo.database import Database
from dotenv import load_dotenv

# Añadir el directorio raíz al path para permitir importaciones absolutas
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.models import ImagenDocumento, ConsultaBusqueda, ResultadoBusqueda

# Cargar variables de entorno
load_dotenv()

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class DatabaseManager:
    """Gestor de conexión y operaciones con MongoDB."""

    def __init__(self):
        """Inicializar la conexión a MongoDB."""
        self.client: Optional[MongoClient] = None
        self.database: Optional[Database] = None
        self.collection: Optional[Collection] = None
        self._connect()

    def _connect(self):
        """Establecer conexión con MongoDB."""
        try:
            # Obtener configuración desde variables de entorno
            mongodb_uri = os.getenv('MONGODB_URI', 'mongodb://localhost:27017/')
            database_name = os.getenv('MONGODB_DATABASE', 'album')
            collection_name = os.getenv('MONGODB_COLLECTION', 'imagenes_2')

            # Crear cliente MongoDB
            self.client = MongoClient(mongodb_uri)
            self.database = self.client[database_name]
            self.collection = self.database[collection_name]

            # Verificar conexión
            self.client.admin.command('ping')
            logger.info(f"Conexión exitosa a MongoDB: {database_name}.{collection_name}")

            # Inicializar índices de texto
            self._ensure_text_indexes()

        except Exception as e:
            logger.error(f"Error al conectar a MongoDB: {e}")
            raise

    def _ensure_text_indexes(self):
        """Asegurar que existan los índices de texto necesarios para búsquedas."""
        try:
            # Verificar si ya existe un índice de texto
            existing_indexes = self.collection.list_indexes()
            text_index_exists = any(
                index.get('name') == 'text_search_index' for index in existing_indexes
            )

            if not text_index_exists:
                logger.info("Creando índice de texto para búsquedas...")

                # Crear índice de texto en campos relevantes para búsqueda
                self.collection.create_index([
                    ('nombre', 'text'),
                    ('descripcion_semantica', 'text'),
                    ('objetos', 'text'),
                    ('personas', 'text'),
                    ('barrio', 'text'),
                    ('calle', 'text'),
                    ('ciudad', 'text'),
                    ('pais', 'text')
                ], name='text_search_index')

                logger.info("Índice de texto creado exitosamente")
            else:
                logger.info("Índice de texto ya existe")

        except Exception as e:
            logger.warning(f"No se pudo crear el índice de texto: {e}")
            logger.info("Las búsquedas usarán expresiones regulares como alternativa")

    def verificar_ruta_existente(self, ruta_imagen: str) -> bool:
        """
        Verificar si una ruta de imagen ya existe en la colección.

        Args:
            ruta_imagen: Ruta de la imagen a verificar

        Returns:
            True si la ruta ya existe, False si no existe
        """
        try:
            # Buscar documentos con la misma ruta
            documento_existente = self.collection.find_one({"ruta": ruta_imagen})
            return documento_existente is not None
        except Exception as e:
            logger.error(f"Error al verificar ruta existente {ruta_imagen}: {e}")
            return False

    def insertar_documento(self, documento: ImagenDocumento) -> str:
        """
        Insertar un documento en la colección.

        Args:
            documento: Documento a insertar

        Returns:
            ID del documento insertado
        """
        try:
            # Verificar si la ruta ya existe antes de insertar
            if self.verificar_ruta_existente(documento.ruta):
                logger.warning(f"Imagen con ruta {documento.ruta} ya existe en la colección. Omitiendo inserción.")
                # Buscar el documento existente para obtener su ID
                documento_existente = self.collection.find_one({"ruta": documento.ruta})
                if documento_existente:
                    return str(documento_existente.get("_id"))
                else:
                    raise Exception(f"No se pudo encontrar el documento existente con ruta: {documento.ruta}")

            data = documento.to_dict()
            result = self.collection.insert_one(data)
            logger.info(f"Documento insertado con ID: {result.inserted_id}")
            return str(result.inserted_id)
        except Exception as e:
            logger.error(f"Error al insertar documento: {e}")
            raise

    def buscar_por_texto(self, consulta: ConsultaBusqueda) -> List[ResultadoBusqueda]:
        """
        Buscar documentos usando texto.

        Args:
            consulta: Consulta de búsqueda

        Returns:
            Lista de resultados de búsqueda
        """
        try:
            # Intentar búsqueda con índice de texto primero
            try:
                # Crear query de texto
                query = {
                    "$text": {"$search": consulta.query}
                }

                # Agregar filtros adicionales si existen
                if consulta.filtros:
                    query.update(consulta.filtros)

                # Ejecutar búsqueda
                documentos = list(self.collection.find(
                    query,
                    {"score": {"$meta": "textScore"}}
                ).sort([
                    ("score", {"$meta": "textScore"}),
                    ("_id", -1)
                ]).limit(consulta.limite))

                # Convertir a objetos ResultadoBusqueda
                resultados = []
                for doc in documentos:
                    imagen_doc = ImagenDocumento(**doc)
                    # Asegurar que el documento tenga id_hash
                    imagen_doc.ensure_id_hash()
                    similitud = doc.get("score", 0.0)
                    resultado = ResultadoBusqueda(
                        documento=imagen_doc,
                        similitud=similitud,
                        tipo_busqueda="texto"
                    )
                    resultados.append(resultado)

                logger.info(f"Búsqueda de texto completada. {len(resultados)} resultados encontrados.")
                return resultados

            except Exception as text_search_error:
                # Si falla la búsqueda de texto (por falta de índice), usar búsqueda alternativa
                logger.warning(f"Búsqueda de texto falló: {text_search_error}")
                logger.info("Usando búsqueda alternativa con expresiones regulares...")

                # Crear query con expresiones regulares en múltiples campos
                regex_query = {
                    "$or": [
                        {"nombre": {"$regex": consulta.query, "$options": "i"}},
                        {"descripcion_semantica": {"$regex": consulta.query, "$options": "i"}},
                        {"objetos": {"$regex": consulta.query, "$options": "i"}},
                        {"personas": {"$regex": consulta.query, "$options": "i"}},
                        {"barrio": {"$regex": consulta.query, "$options": "i"}},
                        {"calle": {"$regex": consulta.query, "$options": "i"}},
                        {"ciudad": {"$regex": consulta.query, "$options": "i"}},
                        {"pais": {"$regex": consulta.query, "$options": "i"}}
                    ]
                }

                # Agregar filtros adicionales si existen
                if consulta.filtros:
                    # Combinar con AND lógico
                    final_query = {"$and": [regex_query]}
                    if consulta.filtros:
                        final_query["$and"].append(consulta.filtros)
                else:
                    final_query = regex_query

                # Ejecutar búsqueda alternativa
                documentos = list(self.collection.find(final_query).limit(consulta.limite))

                # Convertir a objetos ResultadoBusqueda
                resultados = []
                for doc in documentos:
                    imagen_doc = ImagenDocumento(**doc)
                    # Asegurar que el documento tenga id_hash
                    imagen_doc.ensure_id_hash()
                    # Para búsqueda alternativa, usar una similitud basada en la relevancia del campo
                    similitud = self._calcular_similitud_regex(doc, consulta.query)
                    resultado = ResultadoBusqueda(
                        documento=imagen_doc,
                        similitud=similitud,
                        tipo_busqueda="texto_regex"
                    )
                    resultados.append(resultado)

                logger.info(f"Búsqueda alternativa completada. {len(resultados)} resultados encontrados.")
                return resultados

        except Exception as e:
            logger.error(f"Error en búsqueda de texto: {e}")
            raise

    def _calcular_similitud_regex(self, documento: Dict[str, Any], query: str) -> float:
        """
        Calcular similitud basada en expresiones regulares.

        Args:
            documento: Documento encontrado
            query: Consulta de búsqueda

        Returns:
            Puntuación de similitud (0.0 a 1.0)
        """
        try:
            query_lower = query.lower()
            similitud = 0.0

            # Ponderar diferentes campos
            campos_ponderados = {
                'nombre': 1.0,
                'descripcion_semantica': 0.9,
                'objetos': 0.8,
                'personas': 0.8,
                'ciudad': 0.7,
                'barrio': 0.6,
                'calle': 0.6,
                'pais': 0.5
            }

            for campo, ponderacion in campos_ponderados.items():
                if campo in documento and documento[campo]:
                    valor = str(documento[campo]).lower()

                    # Si la query está contenida en el campo, dar puntuación
                    if query_lower in valor:
                        similitud += ponderacion * 0.8  # 80% de la ponderación máxima

                    # Si el campo está contenido en la query, dar puntuación adicional
                    elif valor in query_lower:
                        similitud += ponderacion * 1.0  # 100% de la ponderación

            # Normalizar similitud (máximo 1.0)
            similitud = min(similitud, 1.0)

            # Si no hay similitud, dar un mínimo para que aparezca en resultados
            if similitud == 0.0:
                similitud = 0.1

            return similitud

        except Exception as e:
            logger.warning(f"Error al calcular similitud regex: {e}")
            return 0.1

    def buscar_por_objetos(self, objetos: List[str], limite: int = 10) -> List[ImagenDocumento]:
        """
        Buscar documentos que contengan objetos específicos.

        Args:
            objetos: Lista de objetos a buscar
            limite: Número máximo de resultados

        Returns:
            Lista de documentos que contienen los objetos
        """
        try:
            query = {
                "objetos": {"$in": objetos}
            }

            documentos = list(self.collection.find(query).limit(limite))

            resultados = []
            for doc in documentos:
                imagen_doc = ImagenDocumento(**doc)
                # Asegurar que el documento tenga id_hash
                imagen_doc.ensure_id_hash()
                resultados.append(imagen_doc)
            logger.info(f"Búsqueda por objetos completada. {len(resultados)} resultados encontrados.")
            return resultados

        except Exception as e:
            logger.error(f"Error en búsqueda por objetos: {e}")
            raise

    def buscar_por_ubicacion(self, ubicacion: Dict[str, str], limite: int = 10) -> List[ImagenDocumento]:
        """
        Buscar documentos por ubicación.

        Args:
            ubicacion: Diccionario con criterios de ubicación (ciudad, barrio, calle, etc.)
            limite: Número máximo de resultados

        Returns:
            Lista de documentos que coinciden con la ubicación
        """
        try:
            query = {}
            for campo, valor in ubicacion.items():
                if valor:
                    query[campo] = {"$regex": valor, "$options": "i"}

            documentos = list(self.collection.find(query).limit(limite))

            resultados = []
            for doc in documentos:
                imagen_doc = ImagenDocumento(**doc)
                # Asegurar que el documento tenga id_hash
                imagen_doc.ensure_id_hash()
                resultados.append(imagen_doc)
            logger.info(f"Búsqueda por ubicación completada. {len(resultados)} resultados encontrados.")
            return resultados

        except Exception as e:
            logger.error(f"Error en búsqueda por ubicación: {e}")
            raise

    def obtener_documento_por_id(self, doc_id: str) -> Optional[ImagenDocumento]:
        """
        Obtener un documento por su ID.

        Args:
            doc_id: ID del documento

        Returns:
            Documento encontrado o None
        """
        try:
            documento = self.collection.find_one({"_id": doc_id})
            if documento:
                imagen_doc = ImagenDocumento(**documento)
                # Asegurar que el documento tenga id_hash
                imagen_doc.ensure_id_hash()
                return imagen_doc
            return None
        except Exception as e:
            logger.error(f"Error al obtener documento por ID: {e}")
            raise

    def actualizar_embedding(self, doc_id: str, embedding: List[float], descripcion: str):
        """
        Actualizar el embedding y descripción semántica de un documento.

        Args:
            doc_id: ID del documento
            embedding: Vector de embedding
            descripcion: Descripción semántica generada
        """
        try:
            self.collection.update_one(
                {"_id": doc_id},
                {"$set": {
                    "embedding": embedding,
                    "descripcion_semantica": descripcion
                }}
            )
            logger.info(f"Embedding actualizado para documento {doc_id}")
        except Exception as e:
            logger.error(f"Error al actualizar embedding: {e}")
            raise

    def obtener_estadisticas(self) -> Dict[str, Any]:
        """
        Obtener estadísticas de la colección.

        Returns:
            Diccionario con estadísticas
        """
        try:
            total_documentos = self.collection.count_documents({})
            documentos_procesados = self.collection.count_documents({"objeto_procesado": True})
            documentos_con_embedding = self.collection.count_documents({"embedding": {"$exists": True}})

            return {
                "total_documentos": total_documentos,
                "documentos_procesados": documentos_procesados,
                "documentos_con_embedding": documentos_con_embedding,
                "tasa_procesamiento": (documentos_procesados / total_documentos * 100) if total_documentos > 0 else 0
            }
        except Exception as e:
            logger.error(f"Error al obtener estadísticas: {e}")
            raise

    def crear_backup_coleccion(self, ruta_backup: str) -> Dict[str, Any]:
        """
        Crear una copia de seguridad de toda la colección MongoDB.

        Args:
            ruta_backup: Ruta donde guardar el archivo de backup

        Returns:
            Diccionario con información del backup creado
        """
        try:
            logger.info(f"Iniciando backup de la colección '{self.collection.name}' en: {ruta_backup}")

            # Obtener información de la colección
            total_documentos = self.collection.count_documents({})

            # Crear estructura del backup
            backup_data = {
                "metadata": {
                    "collection_name": self.collection.name,
                    "database_name": self.database.name,
                    "backup_date": datetime.now().isoformat(),
                    "total_documents": total_documentos,
                    "mongodb_version": "1.0",  # Versión del formato de backup
                    "connection_info": {
                        "mongodb_uri": os.getenv('MONGODB_URI', 'mongodb://localhost:27017/'),
                        "database_name": self.database.name,
                        "collection_name": self.collection.name
                    }
                },
                "documents": []
            }

            # Obtener todos los documentos de la colección
            logger.info(f"Obteniendo {total_documentos} documentos de la colección...")

            # Procesar documentos en lotes para manejar grandes cantidades de datos
            batch_size = 1000
            processed_count = 0

            for documento in self.collection.find({}):
                # Convertir ObjectId a string para serialización JSON
                if '_id' in documento:
                    documento['_id'] = str(documento['_id'])

                backup_data["documents"].append(documento)
                processed_count += 1

                # Log de progreso cada 1000 documentos
                if processed_count % batch_size == 0:
                    logger.info(f"Procesados {processed_count}/{total_documentos} documentos")

            logger.info(f"Total de documentos obtenidos: {len(backup_data['documents'])}")

            # Guardar backup en archivo JSON
            with open(ruta_backup, 'w', encoding='utf-8') as f:
                json.dump(backup_data, f, indent=2, ensure_ascii=False, default=str)

            # Calcular hash del archivo para verificación
            sha256_hash = hashlib.sha256()
            with open(ruta_backup, 'rb') as f:
                for byte_block in iter(lambda: f.read(4096), b""):
                    sha256_hash.update(byte_block)

            backup_info = {
                "ruta_archivo": ruta_backup,
                "total_documentos": len(backup_data["documents"]),
                "tamano_archivo": os.path.getsize(ruta_backup),
                "hash_sha256": sha256_hash.hexdigest(),
                "fecha_backup": backup_data["metadata"]["backup_date"],
                "database_name": self.database.name,
                "collection_name": self.collection.name
            }

            logger.info(f"Backup creado exitosamente: {backup_info}")
            return backup_info

        except Exception as e:
            logger.error(f"Error al crear backup: {e}")
            raise

    def restaurar_coleccion(self, ruta_backup: str, eliminar_existente: bool = True) -> Dict[str, Any]:
        """
        Restaurar la colección desde un archivo de backup.

        Args:
            ruta_backup: Ruta del archivo de backup
            eliminar_existente: Si es True, elimina la colección existente antes de restaurar

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
            if "metadata" not in backup_data or "documents" not in backup_data:
                raise ValueError("Formato de backup inválido")

            metadata = backup_data["metadata"]
            documents_data = backup_data["documents"]

            logger.info(f"Backup metadata: {metadata}")
            logger.info(f"Total de documentos a restaurar: {len(documents_data)}")

            # Si se solicita eliminar la colección existente
            if eliminar_existente:
                logger.info("Eliminando colección existente...")
                collection_name = self.collection.name
                self.database.drop_collection(collection_name)
                # Recrear la colección (se hará automáticamente al insertar)
                self.collection = self.database[collection_name]
                logger.info("Colección eliminada y recreada")

            # Preparar documentos para inserción
            documents_to_insert = []
            for doc_data in documents_data:
                # Convertir string _id de vuelta a ObjectId si es necesario
                if '_id' in doc_data and isinstance(doc_data['_id'], str):
                    try:
                        from bson import ObjectId
                        doc_data['_id'] = ObjectId(doc_data['_id'])
                    except:
                        # Si no se puede convertir, dejar como string
                        pass

                documents_to_insert.append(doc_data)

            # Insertar documentos en lotes para mejor rendimiento
            batch_size = 100
            total_insertados = 0

            for i in range(0, len(documents_to_insert), batch_size):
                batch = documents_to_insert[i:i + batch_size]

                self.collection.insert_many(batch)
                total_insertados += len(batch)
                logger.info(f"Insertados {total_insertados}/{len(documents_to_insert)} documentos")

            # Verificar restauración
            total_actual = self.collection.count_documents({})

            restauracion_info = {
                "ruta_backup": ruta_backup,
                "total_documentos_restaurados": len(documents_to_insert),
                "total_documentos_en_coleccion": total_actual,
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
        Validar la integridad de un archivo de backup de MongoDB.

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
            if "metadata" not in backup_data or "documents" not in backup_data:
                return {
                    "valido": False,
                    "error": "Estructura de backup inválida",
                    "ruta": ruta_backup
                }

            metadata = backup_data["metadata"]
            documents_data = backup_data["documents"]

            # Validar campos requeridos en metadata
            campos_requeridos = ["collection_name", "database_name", "backup_date", "total_documents"]
            for campo in campos_requeridos:
                if campo not in metadata:
                    return {
                        "valido": False,
                        "error": f"Campo requerido faltante en metadata: {campo}",
                        "ruta": ruta_backup
                    }

            # Validar que el número de documentos coincida
            if len(documents_data) != metadata["total_documents"]:
                return {
                    "valido": False,
                    "error": f"Inconsistencia: metadata indica {metadata['total_documents']} documentos pero archivo contiene {len(documents_data)}",
                    "ruta": ruta_backup
                }

            # Validar estructura de documentos
            for i, doc in enumerate(documents_data):
                if not isinstance(doc, dict):
                    return {
                        "valido": False,
                        "error": f"Documento {i} no es un diccionario válido",
                        "ruta": ruta_backup
                    }

                # Verificar que tenga _id
                if '_id' not in doc:
                    return {
                        "valido": False,
                        "error": f"Documento {i} no tiene campo _id",
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
                "total_documentos": len(documents_data),
                "fecha_backup": metadata.get("backup_date", "Desconocida"),
                "database_name": metadata.get("database_name", "Desconocida"),
                "collection_name": metadata.get("collection_name", "Desconocida")
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
        """Cerrar la conexión a MongoDB."""
        if self.client:
            self.client.close()
            logger.info("Conexión a MongoDB cerrada")

    def __del__(self):
        """Destructor para asegurar que la conexión se cierre."""
        self.cerrar_conexion()