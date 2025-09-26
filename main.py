#!/usr/bin/env python3
"""
Punto de entrada principal para la aplicación de búsqueda semántica V2.

Esta aplicación permite realizar búsquedas semánticas en una base de datos MongoDB
utilizando LangChain y Ollama, con una interfaz gráfica desarrollada en PySide6.

Requisitos:
- Entorno conda 'busqueda_semantica_v2' activado
- MongoDB ejecutándose
- Ollama ejecutándose con modelos instalados

Uso:
    python main.py

Autor: Búsqueda Semántica V2
Versión: 1.0.0
"""
import sys
import os
import logging
from pathlib import Path

# Agregar el directorio actual al path para importar módulos
current_dir = str(Path(__file__).parent)
sys.path.insert(0, current_dir)

from PySide6.QtWidgets import QApplication, QMessageBox
from PySide6.QtCore import Qt
from PySide6.QtGui import QIcon

from ui.main_window import MainWindow

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('busqueda_semantica.log'),
        logging.StreamHandler(sys.stdout)
    ]
)

# Suprimir advertencias específicas
import warnings
warnings.filterwarnings("ignore", message=".*CUDA.*")
warnings.filterwarnings("ignore", message=".*LangChainDeprecationWarning.*")
warnings.filterwarnings("ignore", message=".*Valid config keys have changed in V2.*")

logger = logging.getLogger(__name__)

# Cargar variables de entorno desde el archivo .env
dotenv_path = Path(__file__).parent / "config" / ".env"
from dotenv import load_dotenv
load_dotenv(dotenv_path=dotenv_path)

# Configurar variables de entorno para evitar problemas CUDA
os.environ['CUDA_VISIBLE_DEVICES'] = ''  # Deshabilitar CUDA
os.environ['TORCH_USE_CUDA_DSA'] = '0'  # Deshabilitar DSA


def verificar_dependencias():
    """Verificar que todas las dependencias estén disponibles."""
    dependencias_faltantes = []

    try:
        import pymongo
    except ImportError:
        dependencias_faltantes.append("pymongo")

    try:
        import langchain
    except ImportError:
        dependencias_faltantes.append("langchain")

    try:
        import langchain_ollama
        from langchain_ollama import OllamaEmbeddings
    except ImportError:
        dependencias_faltantes.append("langchain-ollama")

    try:
        from langchain_ollama import OllamaEmbeddings
    except ImportError:
        dependencias_faltantes.append("sentence-transformers")

    try:
        from PySide6.QtWidgets import QApplication
    except ImportError:
        dependencias_faltantes.append("PySide6")

    try:
        from dotenv import load_dotenv
    except ImportError:
        dependencias_faltantes.append("python-dotenv")

    if dependencias_faltantes:
        logger.error(f"Dependencias faltantes: {', '.join(dependencias_faltantes)}")
        return False, dependencias_faltantes

    return True, []


def verificar_entorno():
    """Verificar que el entorno esté configurado correctamente."""
    # Verificar archivo de configuración
    config_file = Path("config/.env")
    if not config_file.exists():
        logger.warning("Archivo de configuración no encontrado, usando valores por defecto")
        return True

    # Verificar variables de entorno críticas
    variables_criticas = [
        'MONGODB_URI',
        'MONGODB_DATABASE',
        'OLLAMA_BASE_URL'
    ]

    for var in variables_criticas:
        if not os.getenv(var):
            logger.warning(f"Variable de entorno {var} no definida")

    return True


def mostrar_informacion_sistema():
    """Mostrar información del sistema y dependencias."""
    logger.info("=== Búsqueda Semántica V2 ===")
    logger.info("Versión: 1.0.0")
    logger.info(f"Directorio de trabajo: {os.getcwd()}")

    # Mostrar versiones de dependencias
    try:
        import pymongo
        logger.info(f"PyMongo: {pymongo.version}")
    except ImportError:
        logger.warning("PyMongo no disponible")

    try:
        import langchain
        logger.info(f"LangChain: {langchain.__version__}")
    except ImportError:
        logger.warning("LangChain no disponible")

    try:
        from langchain_ollama import __version__ as ollama_version
        logger.info(f"LangChain Ollama: {ollama_version}")
    except ImportError:
        logger.warning("Sentence Transformers no disponible")

    try:
        from PySide6 import __version__ as qt_version
        logger.info(f"PySide6: {qt_version}")
    except ImportError:
        logger.warning("PySide6 no disponible")


def inicializar_sistema():
    """Inicializar el sistema de procesamiento en segundo plano."""
    try:
        logger.info("Inicializando sistema de detección de objetos...")

        # Importar componentes del sistema
        from src.background_processor import ApplicationInitializer

        # Crear inicializador
        initializer = ApplicationInitializer()

        # Inicializar todos los componentes
        if initializer.initialize_all():
            # Iniciar procesamiento en segundo plano
            initializer.start_background_processing()
            logger.info("Sistema de detección de objetos iniciado correctamente")
            return initializer
        else:
            logger.warning("No se pudo inicializar completamente el sistema de detección de objetos")
            return None

    except Exception as e:
        logger.error(f"Error al inicializar sistema de detección de objetos: {e}")
        return None


def main():
    """Función principal de la aplicación."""
    try:
        # Verificar dependencias
        logger.info("Verificando dependencias...")
        dependencias_ok, dependencias_faltantes = verificar_dependencias()

        if not dependencias_ok:
            error_msg = (
                "Faltan dependencias requeridas. Instale las siguientes dependencias:\n\n" +
                "\n".join(f"- {dep}" for dep in dependencias_faltantes) +
                "\n\nUse el comando:\n" +
                "conda activate busqueda_semantica_v2\n" +
                f"pip install {' '.join(dependencias_faltantes)}"
            )
            QMessageBox.critical(None, "Error de Dependencias", error_msg)
            sys.exit(1)

        # Verificar entorno
        logger.info("Verificando configuración...")
        verificar_entorno()

        # Mostrar información del sistema
        mostrar_informacion_sistema()

        # Crear aplicación Qt
        logger.info("Iniciando aplicación Qt...")
        app = QApplication(sys.argv)

        # Configurar propiedades de la aplicación
        app.setApplicationName("Búsqueda Semántica V2")
        app.setApplicationVersion("1.0.0")
        app.setOrganizationName("Búsqueda Semántica Project")

        # Configurar icono de la aplicación (si existe)
        icon_path = Path("resources/icon.png")
        if icon_path.exists():
            app.setWindowIcon(QIcon(str(icon_path)))

        # Configurar atributos de la aplicación
        app.setAttribute(Qt.AA_EnableHighDpiScaling, True)
        app.setAttribute(Qt.AA_UseHighDpiPixmaps, True)

        # Crear y mostrar ventana principal
        logger.info("Creando ventana principal...")
        main_window = MainWindow()
        main_window.show()

        # Sistema de detección de objetos DESHABILITADO - se activará manualmente
        logger.info("Sistema de detección de objetos deshabilitado (se activará manualmente)")
        system_initializer = None

        # Ejecutar aplicación
        logger.info("Ejecutando aplicación...")
        sys.exit(app.exec())

    except KeyboardInterrupt:
        logger.info("Aplicación interrumpida por el usuario")
        sys.exit(0)

    except Exception as e:
        logger.error(f"Error fatal en la aplicación: {e}", exc_info=True)
        QMessageBox.critical(
            None,
            "Error Fatal",
            f"Ha ocurrido un error fatal en la aplicación:\n\n{str(e)}\n\n"
            "Consulte el archivo de log para más detalles."
        )
        sys.exit(1)


if __name__ == "__main__":
    main()