"""
Módulo para búsqueda semántica usando LangChain y Ollama.
"""
import os
import sys
import logging
from typing import List, Dict, Any, Optional, Tuple
from langchain_ollama import OllamaLLM, OllamaEmbeddings
from langchain.prompts import PromptTemplate
from langchain.chains import LLMChain
import numpy as np

# Añadir el directorio raíz al path para permitir importaciones absolutas
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.models import ImagenDocumento, ConsultaBusqueda, ResultadoBusqueda
from src.database import DatabaseManager
from src.qdrant_manager import QdrantManager

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class BuscadorSemantico:
    """Clase para realizar búsquedas semánticas en documentos de imágenes."""

    def __init__(self, db_manager: DatabaseManager, qdrant_manager: Optional[QdrantManager] = None):
        """
        Inicializar el buscador semántico.

        Args:
            db_manager: Gestor de base de datos MongoDB
            qdrant_manager: Gestor de base de datos Qdrant (opcional)
        """
        self.db_manager = db_manager
        self.qdrant_manager = qdrant_manager or QdrantManager()
        self.modelo_embedding = None
        self.modelo_llm = None
        self._inicializar_modelos()

    def _inicializar_modelos(self):
        """Inicializar modelos de embedding y LLM."""
        try:
            # Inicializar modelo de embeddings con Ollama
            ollama_base_url = os.getenv('OLLAMA_BASE_URL', 'http://localhost:11434')
            embedding_model = os.getenv('EMBEDDING_MODEL', 'embeddinggemma')

            self.modelo_embedding = OllamaEmbeddings(
                base_url=ollama_base_url,
                model=embedding_model
            )
            logger.info(f"Modelo de embeddings inicializado: {embedding_model} (Ollama)")

            # Inicializar modelo LLM con Ollama
            ollama_model = os.getenv('OLLAMA_MODEL', 'qwen3:14b_40K')

            self.modelo_llm = OllamaLLM(
                base_url=ollama_base_url,
                model=ollama_model,
                temperature=0.1
            )
            logger.info(f"Modelo LLM inicializado: {ollama_model}")

        except Exception as e:
            logger.error(f"Error al inicializar modelos: {e}")
            raise

    def generar_embedding(self, texto: str) -> List[float]:
        """
        Generar embedding para un texto dado.

        Args:
            texto: Texto para el que generar embedding

        Returns:
            Vector de embedding
        """
        try:
            embedding = self.modelo_embedding.embed_query(texto)
            return embedding
        except Exception as e:
            logger.error(f"Error al generar embedding: {e}")
            raise

    def _crear_texto_desde_campos(self, documento: ImagenDocumento) -> str:
        """
        Crear texto para embedding basado en TODOS los campos del documento.

        Args:
            documento: Documento de imagen

        Returns:
            Texto concatenado de TODOS los campos relevantes
        """
        campos_texto = []

        # Agregar identificadores únicos
        if documento.id_hash:
            campos_texto.append(f"id_hash: {documento.id_hash}")
        if documento.hash_sha512:
            campos_texto.append(f"hash_sha512: {documento.hash_sha512}")

        # Agregar información del archivo
        if documento.nombre:
            campos_texto.append(f"archivo: {documento.nombre}")
        if documento.ruta:
            campos_texto.append(f"ruta: {documento.ruta}")
        if documento.ruta_alternativa:
            campos_texto.append(f"ruta_alternativa: {documento.ruta_alternativa}")

        # Agregar dimensiones y peso
        if documento.ancho and documento.alto:
            campos_texto.append(f"dimensiones: {documento.ancho}x{documento.alto} píxeles")
        if documento.peso:
            campos_texto.append(f"peso: {documento.peso} bytes")

        # Agregar fechas de creación con formato mejorado
        fecha_creacion = documento.get_fecha_creacion()
        if fecha_creacion:
            campos_texto.append(f"fecha_creación: {fecha_creacion}")

        # Agregar fechas de procesamiento con formato mejorado
        fecha_procesamiento = documento.get_fecha_procesamiento()
        if fecha_procesamiento:
            campos_texto.append(f"fecha_procesamiento: {fecha_procesamiento}")

        # Agregar ubicación geográfica completa
        ubicacion_partes = []
        if documento.ciudad:
            ubicacion_partes.append(f"ciudad: {documento.ciudad}")
        if documento.barrio:
            ubicacion_partes.append(f"barrio: {documento.barrio}")
        if documento.calle:
            ubicacion_partes.append(f"calle: {documento.calle}")
        if documento.cp:
            ubicacion_partes.append(f"CP: {documento.cp}")
        if documento.pais:
            ubicacion_partes.append(f"país: {documento.pais}")

        if ubicacion_partes:
            campos_texto.append(f"ubicación: {', '.join(ubicacion_partes)}")

        # Agregar coordenadas geográficas con formato mejorado
        if documento.coordenadas:
            if isinstance(documento.coordenadas, dict):
                coords = documento.coordenadas
                if 'lat' in coords and 'lon' in coords:
                    lat = coords['lat']
                    lon = coords['lon']
                    campos_texto.append(f"coordenadas_geográficas: latitud {lat}, longitud {lon}")
                    # Agregar también como ubicación aproximada
                    if documento.ciudad:
                        campos_texto.append(f"ubicación_geográfica: {documento.ciudad} (lat: {lat}, lon: {lon})")
            elif isinstance(documento.coordenadas, list) and len(documento.coordenadas) >= 2:
                lat = documento.coordenadas[0]
                lon = documento.coordenadas[1]
                campos_texto.append(f"coordenadas_geográficas: latitud {lat}, longitud {lon}")
                # Agregar también como ubicación aproximada
                if documento.ciudad:
                    campos_texto.append(f"ubicación_geográfica: {documento.ciudad} (lat: {lat}, lon: {lon})")

        # Agregar estado de procesamiento con más contexto
        estado_procesamiento = 'procesado' if documento.objeto_procesado else 'pendiente de procesamiento'
        campos_texto.append(f"estado_procesamiento: {estado_procesamiento}")
        campos_texto.append(f"imagen_analizada: {'sí' if documento.objeto_procesado else 'no'}")

        # Agregar objetos detectados con mejor formato
        if documento.objetos:
            objetos_str = ', '.join(documento.objetos)
            campos_texto.append(f"objetos_detectados: {objetos_str}")
            campos_texto.append(f"contiene_objetos: {objetos_str}")
            # Agregar conteo de objetos
            campos_texto.append(f"número_objetos: {len(documento.objetos)} objetos detectados")

        # Agregar personas detectadas con mejor formato
        if documento.personas:
            personas_str = ', '.join(documento.personas)
            campos_texto.append(f"personas_detectadas: {personas_str}")
            campos_texto.append(f"contiene_personas: {personas_str}")
            # Agregar conteo de personas
            campos_texto.append(f"número_personas: {len(documento.personas)} personas detectadas")

        # Agregar información de embedding existente
        if documento.descripcion_semantica:
            campos_texto.append(f"descripción_semántica: {documento.descripcion_semantica}")

        # Concatenar todos los campos
        texto_final = " | ".join(campos_texto)

        logger.debug(f"Texto generado para embedding (incluye TODOS los campos): {texto_final}")
        return texto_final

    def generar_descripcion_semantica(self, documento: ImagenDocumento) -> str:
        """
        Generar una descripción semántica para un documento de imagen.

        Args:
            documento: Documento de imagen

        Returns:
            Descripción semántica generada
        """
        try:
            # Crear prompt para generar descripción
            template = """
            Analiza la siguiente información de una imagen y genera una descripción detallada y natural:

            Información de la imagen:
            - Nombre: {nombre}
            - Dimensiones: {ancho}x{alto} píxeles
            - Peso: {peso} bytes
            - Fecha de creación: {fecha_creacion}
            - Ubicación: {ubicacion}
            - Objetos detectados: {objetos}
            - Personas detectadas: {personas}

            Genera una descripción coherente y detallada de lo que podría verse en esta imagen.
            La descripción debe ser en español y sonar natural.
            """

            prompt = PromptTemplate(
                template=template,
                input_variables=["nombre", "ancho", "alto", "peso", "fecha_creacion", "ubicacion", "objetos", "personas"]
            )

            # Formatear información del documento
            ubicacion = ", ".join([
                documento.ciudad,
                documento.barrio,
                documento.calle
            ]).strip(", ")

            if not ubicacion:
                ubicacion = "Ubicación no especificada"

            objetos_str = ", ".join(documento.objetos) if documento.objetos else "Ninguno detectado"
            personas_str = ", ".join(documento.personas) if documento.personas else "Ninguna detectada"

            # Crear cadena LLM usando la nueva API
            chain = prompt | self.modelo_llm

            # Generar descripción
            descripcion = chain.invoke({
                "nombre": documento.nombre,
                "ancho": documento.ancho,
                "alto": documento.alto,
                "peso": documento.peso,
                "fecha_creacion": documento.get_fecha_creacion(),
                "ubicacion": ubicacion,
                "objetos": objetos_str,
                "personas": personas_str
            })

            logger.info(f"Descripción semántica generada para {documento.nombre}")
            return descripcion.strip()

        except Exception as e:
            logger.error(f"Error al generar descripción semántica: {e}")
            raise

    def buscar_semanticamente(self, consulta: ConsultaBusqueda) -> List[ResultadoBusqueda]:
        """
        Realizar búsqueda semántica usando Qdrant.

        Args:
            consulta: Consulta de búsqueda

        Returns:
            Lista de resultados ordenados por similitud
        """
        try:
            # Generar embedding para la consulta
            query_embedding = self.generar_embedding(consulta.query)

            # Preparar filtros para Qdrant
            filtros = {}
            if consulta.filtros:
                filtros.update(consulta.filtros)

            # Buscar en Qdrant
            resultados_qdrant = self.qdrant_manager.buscar_similares(
                embedding=query_embedding,
                limite=consulta.limite,
                umbral_similitud=consulta.umbral_similitud,
                filtros=filtros
            )

            # Convertir resultados a formato ResultadoBusqueda
            resultados = []
            for result in resultados_qdrant:
                try:
                    # Crear documento desde el payload de Qdrant
                    payload = result["payload"]
                    documento = ImagenDocumento(
                        id=payload.get("id_hash"),
                        id_hash=payload["id_hash"],
                        hash_sha512=payload["hash_sha512"],
                        nombre=payload["nombre"],
                        ruta=payload["ruta"],
                        ruta_alternativa=payload.get("ruta_alternativa"),
                        ancho=payload["ancho"],
                        alto=payload["alto"],
                        peso=payload["peso"],
                        fecha_creacion_dia=payload.get("fecha_creacion", "").split("/")[0] if payload.get("fecha_creacion") else "",
                        fecha_creacion_mes=payload.get("fecha_creacion", "").split("/")[1] if payload.get("fecha_creacion") and "/" in payload.get("fecha_creacion", "") else "",
                        fecha_creacion_anio=payload.get("fecha_creacion", "").split("/")[2].split()[0] if payload.get("fecha_creacion") else "",
                        fecha_creacion_hora=payload.get("fecha_creacion", "").split()[1].split(":")[0] if payload.get("fecha_creacion") and " " in payload.get("fecha_creacion", "") else "",
                        fecha_creacion_minuto=payload.get("fecha_creacion", "").split()[1].split(":")[1] if payload.get("fecha_creacion") and " " in payload.get("fecha_creacion", "") else "",
                        fecha_procesamiento_dia=payload.get("fecha_procesamiento", "").split("/")[0] if payload.get("fecha_procesamiento") else "",
                        fecha_procesamiento_mes=payload.get("fecha_procesamiento", "").split("/")[1] if payload.get("fecha_procesamiento") and "/" in payload.get("fecha_procesamiento", "") else "",
                        fecha_procesamiento_anio=payload.get("fecha_procesamiento", "").split("/")[2].split()[0] if payload.get("fecha_procesamiento") else "",
                        fecha_procesamiento_hora=payload.get("fecha_procesamiento", "").split()[1].split(":")[0] if payload.get("fecha_procesamiento") and " " in payload.get("fecha_procesamiento", "") else "",
                        fecha_procesamiento_minuto=payload.get("fecha_procesamiento", "").split()[1].split(":")[1] if payload.get("fecha_procesamiento") and " " in payload.get("fecha_procesamiento", "") else "",
                        coordenadas=payload.get("coordenadas"),
                        barrio=payload.get("barrio", ""),
                        calle=payload.get("calle", ""),
                        ciudad=payload.get("ciudad", ""),
                        cp=payload.get("cp", ""),
                        pais=payload.get("pais", ""),
                        objeto_procesado=payload.get("objeto_procesado", False),
                        objetos=payload.get("objetos", []),
                        personas=payload.get("personas", []),
                        embedding=None,  # No necesitamos el embedding en el resultado
                        descripcion_semantica=payload.get("descripcion_semantica")
                    )

                    resultado = ResultadoBusqueda(
                        documento=documento,
                        similitud=result["score"],
                        tipo_busqueda="semántica"
                    )
                    resultados.append(resultado)

                except Exception as e:
                    logger.warning(f"Error al procesar resultado de Qdrant: {e}")
                    continue

            logger.info(f"Búsqueda semántica completada. {len(resultados)} resultados encontrados.")
            return resultados

        except Exception as e:
            logger.error(f"Error en búsqueda semántica: {e}")
            raise

    def buscar_hibrida(self, consulta: ConsultaBusqueda) -> List[ResultadoBusqueda]:
        """
        Realizar búsqueda híbrida (texto + semántica).

        Args:
            consulta: Consulta de búsqueda

        Returns:
            Lista de resultados combinados
        """
        try:
            # Realizar búsqueda de texto
            resultados_texto = self.db_manager.buscar_por_texto(consulta)

            # Realizar búsqueda semántica
            resultados_semanticos = self.buscar_semanticamente(consulta)

            # Combinar y eliminar duplicados
            resultados_combinados = {}

            for resultado in resultados_texto + resultados_semanticos:
                doc_id = resultado.documento.id_hash
                if doc_id not in resultados_combinados:
                    resultados_combinados[doc_id] = resultado
                else:
                    # Si existe, mantener el de mayor similitud
                    if resultado.similitud > resultados_combinados[doc_id].similitud:
                        resultados_combinados[doc_id] = resultado

            # Convertir a lista y ordenar
            resultados_finales = list(resultados_combinados.values())
            resultados_finales.sort(key=lambda x: x.similitud, reverse=True)
            resultados_finales = resultados_finales[:consulta.limite]

            logger.info(f"Búsqueda híbrida completada. {len(resultados_finales)} resultados únicos encontrados.")
            return resultados_finales

        except Exception as e:
            logger.error(f"Error en búsqueda híbrida: {e}")
            raise

    def procesar_documento(self, documento: ImagenDocumento, cancel_callback=None) -> ImagenDocumento:
        """
        Procesar un documento para generar embedding basado en campos existentes.

        Args:
            documento: Documento a procesar
            cancel_callback: Callback para verificar si se debe cancelar

        Returns:
            Documento procesado con embedding
        """
        try:
            # Crear texto basado en campos existentes del documento
            texto_para_embedding = self._crear_texto_desde_campos(documento)

            # Verificar cancelación antes de generar embedding
            if cancel_callback and cancel_callback():
                logger.info(f"Procesamiento cancelado antes de generar embedding para: {documento.nombre}")
                raise Exception("Procesamiento cancelado por el usuario")

            # Generar embedding para el texto
            embedding = self.generar_embedding(texto_para_embedding)

            # Verificar cancelación antes de actualizar MongoDB
            if cancel_callback and cancel_callback():
                logger.info(f"Procesamiento cancelado antes de actualizar MongoDB para: {documento.nombre}")
                raise Exception("Procesamiento cancelado por el usuario")

            # Actualizar documento en MongoDB
            self.db_manager.actualizar_embedding(
                documento.id_hash,
                embedding,
                texto_para_embedding
            )

            # Verificar cancelación antes de Qdrant
            if cancel_callback and cancel_callback():
                logger.info(f"Procesamiento cancelado antes de Qdrant para: {documento.nombre}")
                raise Exception("Procesamiento cancelado por el usuario")

            # Insertar/actualizar en Qdrant
            try:
                # Verificar si ya existe en Qdrant
                doc_qdrant = self.qdrant_manager.obtener_por_id(documento.id_hash)

                if doc_qdrant:
                    # Actualizar en Qdrant
                    self.qdrant_manager.actualizar_vector(
                        documento.id_hash,
                        embedding,
                        texto_para_embedding
                    )
                else:
                    # Insertar en Qdrant
                    self.qdrant_manager.insertar_vector(
                        documento,
                        embedding,
                        texto_para_embedding
                    )
            except Exception as qdrant_error:
                logger.warning(f"Error al guardar en Qdrant (continuando): {qdrant_error}")

            # Actualizar objeto documento
            documento.descripcion_semantica = texto_para_embedding
            documento.embedding = embedding

            logger.info(f"Documento procesado: {documento.nombre}")
            return documento

        except Exception as e:
            logger.error(f"Error al procesar documento: {e}")
            raise

    def _calcular_similitud_coseno(self, vector1: np.ndarray, vector2: np.ndarray) -> float:
        """
        Calcular similitud coseno entre dos vectores.

        Args:
            vector1: Primer vector
            vector2: Segundo vector

        Returns:
            Similitud coseno (0-1)
        """
        try:
            dot_product = np.dot(vector1, vector2)
            norm1 = np.linalg.norm(vector1)
            norm2 = np.linalg.norm(vector2)

            if norm1 == 0 or norm2 == 0:
                return 0.0

            similitud = dot_product / (norm1 * norm2)
            return float(similitud)
        except Exception as e:
            logger.error(f"Error al calcular similitud coseno: {e}")
            return 0.0

    def obtener_sugerencias(self, consulta_parcial: str, limite: int = 5) -> List[str]:
        """
        Obtener sugerencias de búsqueda basadas en consulta parcial.

        Args:
            consulta_parcial: Texto parcial de la consulta
            limite: Número máximo de sugerencias

        Returns:
            Lista de sugerencias
        """
        try:
            sugerencias = []

            # Buscar en nombres de archivos
            documentos = list(self.db_manager.collection.find(
                {"nombre": {"$regex": consulta_parcial, "$options": "i"}},
                {"nombre": 1}
            ).limit(limite * 2))

            for doc in documentos:
                nombre = doc.get("nombre", "")
                if nombre and nombre not in sugerencias:
                    sugerencias.append(nombre)

            # Buscar en objetos detectados
            documentos = list(self.db_manager.collection.find(
                {"objetos": {"$regex": consulta_parcial, "$options": "i"}},
                {"objetos": 1}
            ).limit(limite * 2))

            for doc in documentos:
                objetos = doc.get("objetos", [])
                for objeto in objetos:
                    if objeto and consulta_parcial.lower() in objeto.lower() and objeto not in sugerencias:
                        sugerencias.append(objeto)

            # Buscar en ubicaciones (ciudad, barrio, calle)
            ubicaciones = ["ciudad", "barrio", "calle"]
            for ubicacion in ubicaciones:
                documentos = list(self.db_manager.collection.find(
                    {ubicacion: {"$regex": consulta_parcial, "$options": "i"}},
                    {ubicacion: 1}
                ).limit(limite * 2))

                for doc in documentos:
                    valor = doc.get(ubicacion, "")
                    if valor and valor not in sugerencias:
                        sugerencias.append(valor)

            return sugerencias[:limite]

        except Exception as e:
            logger.error(f"Error al obtener sugerencias: {e}")
            return []