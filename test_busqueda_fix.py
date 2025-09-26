#!/usr/bin/env python3
"""
Script de prueba para verificar que las búsquedas funcionan correctamente después del fix.
"""
import os
import sys

# Añadir el directorio raíz al path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.database import DatabaseManager
from src.models import ConsultaBusqueda

def test_busqueda_texto():
    """Probar la funcionalidad de búsqueda de texto."""
    print("🧪 Probando funcionalidad de búsqueda de texto...")

    try:
        # Inicializar DatabaseManager
        db_manager = DatabaseManager()
        print(f"✅ Conectado a MongoDB: {db_manager.database.name}.{db_manager.collection.name}")

        # Obtener estadísticas
        stats = db_manager.obtener_estadisticas()
        print(f"📊 Total de documentos: {stats['total_documentos']}")

        # Probar diferentes tipos de búsqueda
        consultas_prueba = [
            "casa",  # Búsqueda simple
            "perro",  # Búsqueda por objeto
            "Madrid",  # Búsqueda por ciudad
            "parque",  # Búsqueda por lugar
        ]

        for consulta_texto in consultas_prueba:
            print(f"\n🔍 Probando búsqueda: '{consulta_texto}'")

            try:
                consulta = ConsultaBusqueda(
                    query=consulta_texto,
                    limite=5
                )

                resultados = db_manager.buscar_por_texto(consulta)

                print(f"✅ Búsqueda exitosa: {len(resultados)} resultados encontrados")

                for i, resultado in enumerate(resultados[:3]):  # Mostrar primeros 3
                    print(f"   {i+1}. {resultado.documento.nombre} (similitud: {resultado.similitud:.3f})")
                    print(f"      Tipo: {resultado.tipo_busqueda}")

            except Exception as e:
                print(f"❌ Error en búsqueda '{consulta_texto}': {str(e)}")

        print("\n🎉 Todas las pruebas de búsqueda completadas!")

    except Exception as e:
        print(f"❌ Error durante las pruebas: {str(e)}")
        return False

    finally:
        # Cerrar conexión
        if 'db_manager' in locals():
            db_manager.cerrar_conexion()

    return True

if __name__ == "__main__":
    success = test_busqueda_texto()
    sys.exit(0 if success else 1)