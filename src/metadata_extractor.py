"""
Módulo para extraer metadatos de imágenes y geocodificar coordenadas.
"""
import os
import sys
import logging
import hashlib
from typing import Dict, Any, Optional, Tuple, List
from datetime import datetime
from pathlib import Path

# Importar dependencias para extracción de metadatos
try:
    from PIL import Image
    from PIL.ExifTags import TAGS, GPSTAGS
    import requests
except ImportError as e:
    logging.error(f"Error al importar dependencias para extracción de metadatos: {e}")
    raise

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class MetadataExtractor:
    """Extractor de metadatos de imágenes."""

    def __init__(self):
        """Inicializar el extractor de metadatos."""
        self.logger = logging.getLogger(__name__)

    def extraer_metadatos_imagen(self, ruta_imagen: str) -> Dict[str, Any]:
        """
        Extraer todos los metadatos de una imagen.

        Args:
            ruta_imagen: Ruta completa a la imagen

        Returns:
            Diccionario con todos los metadatos extraídos
        """
        try:
            if not os.path.exists(ruta_imagen):
                self.logger.warning(f"Imagen no encontrada: {ruta_imagen}")
                return {}

            # Extraer información básica del archivo
            info_archivo = self._extraer_info_archivo(ruta_imagen)

            # Extraer metadatos EXIF
            metadatos_exif = self._extraer_exif(ruta_imagen)

            # Combinar toda la información
            metadatos = {**info_archivo, **metadatos_exif}

            self.logger.info(f"Metadatos extraídos para {ruta_imagen}")
            return metadatos

        except Exception as e:
            self.logger.error(f"Error al extraer metadatos de {ruta_imagen}: {e}")
            return {}

    def _extraer_info_archivo(self, ruta_imagen: str) -> Dict[str, Any]:
        """
        Extraer información básica del archivo.

        Args:
            ruta_imagen: Ruta a la imagen

        Returns:
            Diccionario con información del archivo
        """
        try:
            # Obtener estadísticas del archivo
            stat = os.stat(ruta_imagen)

            # Calcular hash SHA512
            hash_sha512 = self._calcular_hash_sha512(ruta_imagen)

            # Extraer información de la imagen con PIL
            with Image.open(ruta_imagen) as img:
                ancho, alto = img.size

            # Extraer fechas del archivo
            fecha_creacion = datetime.fromtimestamp(stat.st_ctime)
            fecha_modificacion = datetime.fromtimestamp(stat.st_mtime)

            return {
                "hash_sha512": hash_sha512,
                "ancho": ancho,
                "alto": alto,
                "peso": stat.st_size,
                "fecha_creacion_dia": str(fecha_creacion.day),
                "fecha_creacion_mes": str(fecha_creacion.month),
                "fecha_creacion_anio": str(fecha_creacion.year),
                "fecha_creacion_hora": str(fecha_creacion.hour),
                "fecha_creacion_minuto": str(fecha_creacion.minute),
                "fecha_modificacion": fecha_modificacion.isoformat()
            }

        except Exception as e:
            self.logger.error(f"Error al extraer información del archivo {ruta_imagen}: {e}")
            return {}

    def _extraer_exif(self, ruta_imagen: str) -> Dict[str, Any]:
        """
        Extraer metadatos EXIF de la imagen.

        Args:
            ruta_imagen: Ruta a la imagen

        Returns:
            Diccionario con metadatos EXIF
        """
        try:
            with Image.open(ruta_imagen) as img:
                exif_data = img.getexif()

                if not exif_data:
                    return {"coordenadas": None}

                # Extraer coordenadas GPS
                coordenadas = self._extraer_coordenadas_gps(exif_data)

                return {
                    "coordenadas": coordenadas
                }

        except Exception as e:
            self.logger.error(f"Error al extraer EXIF de {ruta_imagen}: {e}")
            return {"coordenadas": None}

    def _extraer_coordenadas_gps(self, exif_data) -> Optional[Dict[str, float]]:
        """
        Extraer coordenadas GPS de los metadatos EXIF.

        Args:
            exif_data: Datos EXIF de la imagen

        Returns:
            Diccionario con latitud y longitud, o None si no hay coordenadas
        """
        try:
            if not exif_data:
                return None

            # Buscar etiquetas GPS en EXIF
            gps_info = {}
            for tag_id, value in exif_data.items():
                tag = TAGS.get(tag_id, tag_id)
                if tag == "GPSInfo":
                    gps_data = value
                    for gps_tag_id in gps_data:
                        gps_tag = GPSTAGS.get(gps_tag_id, gps_tag_id)
                        gps_info[gps_tag] = gps_data[gps_tag_id]
                    break

            if not gps_info:
                return None

            # Convertir coordenadas GPS a formato decimal
            latitud = self._convertir_a_decimal(gps_info.get("GPSLatitude"), gps_info.get("GPSLatitudeRef"))
            longitud = self._convertir_a_decimal(gps_info.get("GPSLongitude"), gps_info.get("GPSLongitudeRef"))

            if latitud is not None and longitud is not None:
                return {
                    "lat": latitud,
                    "lon": longitud
                }

            return None

        except Exception as e:
            self.logger.error(f"Error al extraer coordenadas GPS: {e}")
            return None

    def _convertir_a_decimal(self, coordenada, referencia) -> Optional[float]:
        """
        Convertir coordenadas GPS de formato DMS a decimal.

        Args:
            coordenada: Coordenada en formato DMS (grados, minutos, segundos)
            referencia: Referencia N/S para latitud, E/W para longitud

        Returns:
            Coordenada en formato decimal
        """
        try:
            if not coordenada or not referencia:
                return None

            # Convertir a grados decimales
            grados = coordenada[0]
            minutos = coordenada[1] / 60.0
            segundos = coordenada[2] / 3600.0

            decimal = grados + minutos + segundos

            # Aplicar signo según referencia
            if referencia in ['S', 'W']:
                decimal = -decimal

            return round(decimal, 6)

        except Exception as e:
            self.logger.error(f"Error al convertir coordenada: {e}")
            return None

    def _calcular_hash_sha512(self, ruta_imagen: str) -> str:
        """
        Calcular hash SHA512 de un archivo.

        Args:
            ruta_imagen: Ruta al archivo

        Returns:
            Hash SHA512 en formato hexadecimal
        """
        try:
            hash_sha512 = hashlib.sha512()
            with open(ruta_imagen, "rb") as f:
                for chunk in iter(lambda: f.read(4096), b""):
                    hash_sha512.update(chunk)
            return hash_sha512.hexdigest()

        except Exception as e:
            self.logger.error(f"Error al calcular hash SHA512 de {ruta_imagen}: {e}")
            return ""


class Geocodificador:
    """Geocodificador para obtener información de ubicación desde coordenadas."""

    def __init__(self, api_key: Optional[str] = None):
        """
        Inicializar el geocodificador.

        Args:
            api_key: Clave API para servicios de geocodificación (opcional)
        """
        self.api_key = api_key
        self.logger = logging.getLogger(__name__)

    def geocodificar_coordenadas(self, latitud: float, longitud: float) -> Dict[str, str]:
        """
        Geocodificar coordenadas para obtener información de ubicación.

        Args:
            latitud: Latitud en formato decimal
            longitud: Longitud en formato decimal

        Returns:
            Diccionario con información de ubicación
        """
        try:
            # Usar Nominatim (OpenStreetMap) como servicio gratuito
            url = "https://nominatim.openstreetmap.org/reverse"
            headers = {
                'User-Agent': 'BusquedaSemanticaV2/1.0'
            }
            params = {
                'format': 'json',
                'lat': latitud,
                'lon': longitud,
                'zoom': 18,
                'addressdetails': 1
            }

            response = requests.get(url, headers=headers, params=params, timeout=10)
            response.raise_for_status()

            data = response.json()

            if 'address' in data:
                address = data['address']
                return {
                    "barrio": address.get('suburb', address.get('neighbourhood', '')),
                    "calle": address.get('road', ''),
                    "ciudad": address.get('city', address.get('town', address.get('village', ''))),
                    "cp": address.get('postcode', ''),
                    "pais": address.get('country', '')
                }

            return {
                "barrio": "",
                "calle": "",
                "ciudad": "",
                "cp": "",
                "pais": ""
            }

        except Exception as e:
            self.logger.error(f"Error al geocodificar coordenadas ({latitud}, {longitud}): {e}")
            return {
                "barrio": "",
                "calle": "",
                "ciudad": "",
                "cp": "",
                "pais": ""
            }


class ImageProcessor:
    """Procesador completo de imágenes que integra extracción de metadatos y geocodificación."""

    def __init__(self):
        """Inicializar el procesador de imágenes."""
        self.metadata_extractor = MetadataExtractor()
        self.geocodificador = Geocodificador()
        self.logger = logging.getLogger(__name__)

    def procesar_imagen_completa(self, ruta_imagen: str) -> Dict[str, Any]:
        """
        Procesar una imagen completa extrayendo todos los metadatos.

        Args:
            ruta_imagen: Ruta a la imagen

        Returns:
            Diccionario con todos los datos procesados
        """
        try:
            # Extraer metadatos básicos
            metadatos = self.metadata_extractor.extraer_metadatos_imagen(ruta_imagen)

            if not metadatos:
                return {}

            # Extraer nombre del archivo
            nombre_archivo = Path(ruta_imagen).name
            metadatos["nombre"] = nombre_archivo

            # Extraer ruta
            metadatos["ruta"] = ruta_imagen

            # Generar ruta alternativa
            metadatos["ruta_alternativa"] = self._generar_ruta_alternativa(ruta_imagen)

            # Geocodificar si hay coordenadas
            if metadatos.get("coordenadas"):
                coords = metadatos["coordenadas"]
                ubicacion = self.geocodificador.geocodificar_coordenadas(coords["lat"], coords["lon"])
                metadatos.update(ubicacion)

            # Agregar fechas de procesamiento
            ahora = datetime.now()
            metadatos.update({
                "fecha_procesamiento_dia": str(ahora.day),
                "fecha_procesamiento_mes": str(ahora.month),
                "fecha_procesamiento_anio": str(ahora.year),
                "fecha_procesamiento_hora": str(ahora.hour),
                "fecha_procesamiento_minuto": str(ahora.minute),
                "objeto_procesado": False,
                "objetos": [],
                "personas": []
            })

            return metadatos

        except Exception as e:
            self.logger.error(f"Error al procesar imagen {ruta_imagen}: {e}")
            return {}

    def _generar_ruta_alternativa(self, ruta_original: str) -> str:
        """
        Generar ruta alternativa para la imagen.

        Args:
            ruta_original: Ruta original de la imagen

        Returns:
            Ruta alternativa generada
        """
        try:
            # Reemplazar la ruta base por la ruta alternativa
            ruta_base = "/mnt/remoto/11/Datos"
            ruta_alternativa_base = "/mnt/local/datos/PROYECTO_ALBUM/copiado"

            if ruta_original.startswith(ruta_base):
                return ruta_alternativa_base + ruta_original[len(ruta_base):]

            return ruta_original

        except Exception as e:
            self.logger.error(f"Error al generar ruta alternativa: {e}")
            return ruta_original


class ImageDiscovery:
    """Descubridor de imágenes nuevas en el sistema."""

    def __init__(self, ruta_base: str = "/mnt/remoto/11/Datos"):
        """
        Inicializar el descubridor de imágenes.

        Args:
            ruta_base: Ruta base donde buscar imágenes
        """
        self.ruta_base = Path(ruta_base)
        self.logger = logging.getLogger(__name__)

        # Extensiones de imagen soportadas
        self.extensiones_imagen = {'.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff', '.webp'}

    def buscar_imagenes_nuevas(self, db_manager) -> List[Dict[str, Any]]:
        """
        Buscar imágenes nuevas que no estén en la base de datos.

        Args:
            db_manager: Gestor de base de datos

        Returns:
            Lista de metadatos de imágenes nuevas
        """
        try:
            self.logger.info(f"Buscando imágenes nuevas en {self.ruta_base}")

            # Obtener hashes de imágenes ya procesadas
            hashes_procesados = self._obtener_hashes_procesados(db_manager)

            # Buscar archivos de imagen
            archivos_imagen = self._buscar_archivos_imagen()

            # Filtrar imágenes nuevas
            imagenes_nuevas = []
            processor = ImageProcessor()

            for archivo in archivos_imagen:
                try:
                    # Calcular hash del archivo
                    hash_archivo = self._calcular_hash_archivo(str(archivo))

                    # Verificar si ya está procesado
                    if hash_archivo in hashes_procesados:
                        continue

                    # Procesar imagen completa
                    metadatos = processor.procesar_imagen_completa(str(archivo))

                    if metadatos:
                        # Agregar el hash como ID
                        metadatos["_id"] = hash_archivo
                        metadatos["id_hash"] = hash_archivo
                        imagenes_nuevas.append(metadatos)

                except Exception as e:
                    self.logger.error(f"Error al procesar archivo {archivo}: {e}")
                    continue

            self.logger.info(f"Encontradas {len(imagenes_nuevas)} imágenes nuevas")
            return imagenes_nuevas

        except Exception as e:
            self.logger.error(f"Error al buscar imágenes nuevas: {e}")
            return []

    def _obtener_hashes_procesados(self, db_manager) -> set:
        """
        Obtener conjunto de hashes de imágenes ya procesadas.

        Args:
            db_manager: Gestor de base de datos

        Returns:
            Conjunto de hashes procesados
        """
        try:
            # Buscar todos los documentos y extraer sus hashes
            documentos = list(db_manager.collection.find({}, {"hash_sha512": 1}))
            return {doc.get("hash_sha512") for doc in documentos if doc.get("hash_sha512")}

        except Exception as e:
            self.logger.error(f"Error al obtener hashes procesados: {e}")
            return set()

    def _buscar_archivos_imagen(self) -> List[Path]:
        """
        Buscar recursivamente archivos de imagen en la ruta base.

        Returns:
            Lista de rutas de archivos de imagen
        """
        try:
            archivos_imagen = []

            # Buscar recursivamente
            for archivo in self.ruta_base.rglob('*'):
                if archivo.is_file() and archivo.suffix.lower() in self.extensiones_imagen:
                    archivos_imagen.append(archivo)

            return archivos_imagen

        except Exception as e:
            self.logger.error(f"Error al buscar archivos de imagen: {e}")
            return []

    def _calcular_hash_archivo(self, ruta_archivo: str) -> str:
        """
        Calcular hash SHA512 de un archivo.

        Args:
            ruta_archivo: Ruta al archivo

        Returns:
            Hash SHA512 del archivo
        """
        try:
            hash_sha512 = hashlib.sha512()
            with open(ruta_archivo, "rb") as f:
                for chunk in iter(lambda: f.read(4096), b""):
                    hash_sha512.update(chunk)
            return hash_sha512.hexdigest()

        except Exception as e:
            self.logger.error(f"Error al calcular hash de {ruta_archivo}: {e}")
            return ""