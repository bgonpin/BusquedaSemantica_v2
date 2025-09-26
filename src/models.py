"""
Modelos de datos para la aplicación de búsqueda semántica.
"""
from typing import List, Optional, Dict, Any, Union
from datetime import datetime
from pydantic import BaseModel, Field, field_validator


class ImagenDocumento(BaseModel):
    """Modelo que representa un documento de imagen en MongoDB."""

    # Campos principales
    id: Optional[str] = Field(default=None, alias="_id")
    id_hash: Optional[str] = Field(default=None, description="Hash único de identificación")
    hash_sha512: str = Field(..., description="Hash SHA512 del archivo")

    # Información del archivo
    nombre: str = Field(..., description="Nombre del archivo")
    ruta: str = Field(..., description="Ruta del archivo")
    ruta_alternativa: Optional[str] = Field(default=None, description="Ruta alternativa del archivo")

    # Dimensiones y peso
    ancho: int = Field(..., description="Ancho de la imagen en píxeles")
    alto: int = Field(..., description="Alto de la imagen en píxeles")
    peso: float = Field(..., description="Peso del archivo en bytes")

    # Fechas de creación
    fecha_creacion_dia: str = Field(..., description="Día de creación")
    fecha_creacion_mes: str = Field(..., description="Mes de creación")
    fecha_creacion_anio: str = Field(..., description="Año de creación")
    fecha_creacion_hora: str = Field(..., description="Hora de creación")
    fecha_creacion_minuto: str = Field(..., description="Minuto de creación")

    # Fechas de procesamiento
    fecha_procesamiento_dia: str = Field(..., description="Día de procesamiento")
    fecha_procesamiento_mes: str = Field(..., description="Mes de procesamiento")
    fecha_procesamiento_anio: str = Field(..., description="Año de procesamiento")
    fecha_procesamiento_hora: str = Field(..., description="Hora de procesamiento")
    fecha_procesamiento_minuto: str = Field(..., description="Minuto de procesamiento")

    # Ubicación geográfica
    coordenadas: Optional[Union[Dict[str, Any], List[float]]] = Field(default=None, description="Coordenadas geográficas")
    barrio: str = Field(default="", description="Barrio")
    calle: str = Field(default="", description="Calle")
    ciudad: str = Field(default="", description="Ciudad")
    cp: str = Field(default="", description="Código postal")
    pais: str = Field(default="", description="País")

    # Objetos detectados
    objeto_procesado: bool = Field(default=False, description="Indica si la imagen ha sido procesada")
    objetos: List[str] = Field(default_factory=list, description="Lista de objetos detectados en la imagen")
    personas: List[str] = Field(default_factory=list, description="Lista de personas detectadas en la imagen")

    # Campos para búsqueda semántica
    embedding: Optional[List[float]] = Field(default=None, description="Vector de embedding para búsqueda semántica")
    descripcion_semantica: Optional[str] = Field(default=None, description="Descripción semántica generada por IA")

    # Campo para indicar si el documento ya fue insertado en Qdrant
    qdrant: bool = Field(default=False, description="Indica si el documento ya fue insertado en Qdrant")

    @field_validator('coordenadas')
    @classmethod
    def validar_coordenadas(cls, v):
        """Convertir listas de coordenadas a diccionarios."""
        if v is None:
            return v
        elif isinstance(v, list) and len(v) >= 2:
            # Convertir lista [lat, lon] a diccionario {"lat": lat, "lon": lon}
            return {"lat": v[0], "lon": v[1]}
        elif isinstance(v, dict):
            return v
        else:
            # Si no es una lista válida o diccionario, devolver None
            return None


    class Config:
        """Configuración del modelo Pydantic."""
        validate_by_name = True
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }

    def get_fecha_creacion(self) -> str:
        """Retorna la fecha de creación formateada."""
        return f"{self.fecha_creacion_dia}/{self.fecha_creacion_mes}/{self.fecha_creacion_anio} {self.fecha_creacion_hora}:{self.fecha_creacion_minuto}"

    def get_fecha_procesamiento(self) -> str:
        """Retorna la fecha de procesamiento formateada."""
        return f"{self.fecha_procesamiento_dia}/{self.fecha_procesamiento_mes}/{self.fecha_procesamiento_anio} {self.fecha_procesamiento_hora}:{self.fecha_procesamiento_minuto}"

    @classmethod
    def generar_id_hash(cls, mongo_id: str) -> str:
        """Generar id_hash único basado en el _id de MongoDB."""
        import hashlib
        # Crear un hash SHA256 del _id de MongoDB para obtener un identificador único
        return hashlib.sha256(mongo_id.encode()).hexdigest()

    def ensure_id_hash(self) -> str:
        """Asegurar que el documento tenga un id_hash válido."""
        if not self.id_hash and self.id:
            self.id_hash = self.generar_id_hash(self.id)
        return self.id_hash

    def to_dict(self) -> Dict[str, Any]:
        """Convierte el modelo a diccionario para MongoDB."""
        data = self.model_dump(by_alias=True, exclude_unset=True)
        # Eliminar campos None para optimizar almacenamiento
        return {k: v for k, v in data.items() if v is not None}


class ConsultaBusqueda(BaseModel):
    """Modelo para consultas de búsqueda."""

    query: str = Field(..., description="Texto de la consulta de búsqueda")
    limite: int = Field(default=10, description="Número máximo de resultados")
    umbral_similitud: float = Field(default=0.7, description="Umbral de similitud para búsqueda semántica")
    filtros: Optional[Dict[str, Any]] = Field(default=None, description="Filtros adicionales para la búsqueda")


class ResultadoBusqueda(BaseModel):
    """Modelo para resultados de búsqueda."""

    documento: ImagenDocumento = Field(..., description="Documento encontrado")
    similitud: float = Field(..., description="Puntuación de similitud")
    tipo_busqueda: str = Field(..., description="Tipo de búsqueda realizada (texto, semántica, híbrida)")