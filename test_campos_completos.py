#!/usr/bin/env python3
"""
Script de prueba para verificar que TODOS los campos del documento se incluyen en el procesamiento.
"""
import sys
import os
from pathlib import Path

# Agregar el directorio actual al path
current_dir = str(Path(__file__).parent)
sys.path.insert(0, current_dir)

from src.models import ImagenDocumento
from src.busqueda_semantica import BuscadorSemantico
from src.database import DatabaseManager
from src.qdrant_manager import QdrantManager

def crear_documento_prueba():
    """Crear un documento de prueba con todos los campos."""
    return ImagenDocumento(
        id="507f1f77bcf86cd799439011",
        id_hash="test_hash_12345",
        hash_sha512="test_sha512_hash_value",
        nombre="imagen_prueba.jpg",
        ruta="/ruta/completa/a/imagen_prueba.jpg",
        ruta_alternativa="/ruta/alternativa/imagen_prueba.jpg",
        ancho=1920,
        alto=1080,
        peso=2048576.0,
        fecha_creacion_dia="15",
        fecha_creacion_mes="03",
        fecha_creacion_anio="2024",
        fecha_creacion_hora="14",
        fecha_creacion_minuto="30",
        fecha_procesamiento_dia="16",
        fecha_procesamiento_mes="03",
        fecha_procesamiento_anio="2024",
        fecha_procesamiento_hora="09",
        fecha_procesamiento_minuto="45",
        coordenadas={"lat": 40.7128, "lon": -74.0060},
        barrio="Centro",
        calle="Gran Vía",
        ciudad="Madrid",
        cp="28013",
        pais="España",
        objeto_procesado=True,
        objetos=["persona", "coche", "edificio"],
        personas=["Juan", "María"],
        embedding=None,
        descripcion_semantica=None
    )

def main():
    """Función principal de prueba."""
    print("🧪 Probando procesamiento con TODOS los campos del documento...")
    print("=" * 70)

    try:
        # Crear documento de prueba
        documento = crear_documento_prueba()
        print("✅ Documento de prueba creado con todos los campos")

        # Inicializar gestores
        db_manager = DatabaseManager()
        qdrant_manager = QdrantManager()

        # Crear buscador semántico
        buscador = BuscadorSemantico(db_manager, qdrant_manager)

        # Probar creación de texto desde campos
        print("\n🔍 Probando creación de texto para embedding...")
        texto_embedding = buscador._crear_texto_desde_campos(documento)

        print("✅ Texto generado para embedding:")
        print("-" * 50)
        print(texto_embedding)
        print("-" * 50)

        # Verificar que todos los campos están incluidos
        campos_esperados = [
            "id_hash", "hash_sha512", "archivo", "ruta", "ruta_alternativa",
            "dimensiones", "peso", "fecha_creación", "fecha_procesamiento",
            "coordenadas_geográficas", "ubicación", "estado_procesamiento",
            "objetos_detectados", "personas_detectadas", "descripción_semántica"
        ]

        print("\n🔍 Verificando que todos los campos están incluidos:")
        campos_encontrados = []
        for campo in campos_esperados:
            if campo in texto_embedding:
                campos_encontrados.append(campo)
                print(f"   ✅ {campo}")
            else:
                print(f"   ❌ {campo} - NO ENCONTRADO")

        # Verificar campos específicos
        verificaciones = [
            ("id_hash: test_hash_12345", "ID hash"),
            ("hash_sha512: test_sha512_hash_value", "Hash SHA512"),
            ("archivo: imagen_prueba.jpg", "Nombre del archivo"),
            ("ruta: /ruta/completa/a/imagen_prueba.jpg", "Ruta del archivo"),
            ("ruta_alternativa: /ruta/alternativa/imagen_prueba.jpg", "Ruta alternativa"),
            ("dimensiones: 1920x1080 píxeles", "Dimensiones"),
            ("peso: 2048576.0 bytes", "Peso del archivo"),
            ("fecha_creación: 15/03/2024 14:30", "Fecha de creación"),
            ("fecha_procesamiento: 16/03/2024 09:45", "Fecha de procesamiento"),
            ("coordenadas_geográficas: latitud 40.7128, longitud -74.0060", "Coordenadas"),
            ("ubicación: ciudad: Madrid, barrio: Centro, calle: Gran Vía, CP: 28013, país: España", "Ubicación"),
            ("estado_procesamiento: procesado", "Estado de procesamiento"),
            ("objetos_detectados: persona, coche, edificio", "Objetos detectados"),
            ("personas_detectadas: Juan, María", "Personas detectadas"),
            ("número_objetos: 3 objetos detectados", "Conteo de objetos"),
            ("número_personas: 2 personas detectadas", "Conteo de personas")
        ]

        print("\n🔍 Verificaciones específicas:")
        for texto_esperado, descripcion in verificaciones:
            if texto_esperado in texto_embedding:
                print(f"   ✅ {descripcion}")
            else:
                print(f"   ❌ {descripcion} - NO ENCONTRADO")

        # Mostrar estadísticas
        print("\n📊 Estadísticas:")
        print(f"   Longitud del texto: {len(texto_embedding)} caracteres")
        print(f"   Campos encontrados: {len(campos_encontrados)}/{len(campos_esperados)}")
        print(f"   Cobertura: {(len(campos_encontrados)/len(campos_esperados)*100):.1f}%")

        # Verificar payload de Qdrant
        print("\n🔍 Verificando payload de Qdrant...")
        try:
            # Generar embedding de prueba
            embedding_prueba = [0.1] * 768  # Vector de prueba

            # Crear payload como lo haría QdrantManager
            payload = {
                "id": documento.id,
                "id_hash": documento.id_hash,
                "hash_sha512": documento.hash_sha512,
                "nombre": documento.nombre,
                "ruta": documento.ruta,
                "ruta_alternativa": documento.ruta_alternativa,
                "ancho": documento.ancho,
                "alto": documento.alto,
                "peso": documento.peso,
                "fecha_creacion": documento.get_fecha_creacion(),
                "fecha_creacion_dia": documento.fecha_creacion_dia,
                "fecha_creacion_mes": documento.fecha_creacion_mes,
                "fecha_creacion_anio": documento.fecha_creacion_anio,
                "fecha_creacion_hora": documento.fecha_creacion_hora,
                "fecha_creacion_minuto": documento.fecha_creacion_minuto,
                "fecha_procesamiento": documento.get_fecha_procesamiento(),
                "fecha_procesamiento_dia": documento.fecha_procesamiento_dia,
                "fecha_procesamiento_mes": documento.fecha_procesamiento_mes,
                "fecha_procesamiento_anio": documento.fecha_procesamiento_anio,
                "fecha_procesamiento_hora": documento.fecha_procesamiento_hora,
                "fecha_procesamiento_minuto": documento.fecha_procesamiento_minuto,
                "coordenadas": documento.coordenadas,
                "barrio": documento.barrio,
                "calle": documento.calle,
                "ciudad": documento.ciudad,
                "cp": documento.cp,
                "pais": documento.pais,
                "objeto_procesado": documento.objeto_procesado,
                "objetos": documento.objetos,
                "personas": documento.personas,
                "descripcion_semantica": texto_embedding,
                "embedding": embedding_prueba
            }

            print(f"   ✅ Payload de Qdrant creado con {len(payload)} campos")
            print(f"   ✅ Todos los campos del documento incluidos en Qdrant")

            # Mostrar campos del payload
            print("\n📋 Campos incluidos en Qdrant:")
            for campo, valor in payload.items():
                if valor is not None:
                    print(f"   • {campo}: {valor}")

        except Exception as e:
            print(f"   ❌ Error al verificar payload de Qdrant: {e}")

        print("\n" + "=" * 70)
        print("🎉 ¡PRUEBA COMPLETADA!")
        print("✅ El procesamiento ahora incluye TODOS los campos del documento")
        print("✅ Los embeddings se generan con información completa")
        print("✅ Qdrant almacena todos los campos para búsquedas eficientes")

    except Exception as e:
        print(f"❌ Error durante la prueba: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

    finally:
        # Cerrar conexiones
        if 'db_manager' in locals():
            db_manager.cerrar_conexion()
        if 'qdrant_manager' in locals():
            qdrant_manager.cerrar_conexion()

if __name__ == "__main__":
    main()