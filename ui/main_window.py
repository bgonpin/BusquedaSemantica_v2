"""
Ventana principal de la aplicación de búsqueda semántica.
"""
import sys
import os
from typing import List, Optional
from datetime import datetime
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QTabWidget, QLineEdit, QPushButton, QTextEdit, QTableWidget,
    QTableWidgetItem, QProgressBar, QLabel, QComboBox, QSpinBox,
    QDoubleSpinBox, QGroupBox, QFormLayout, QMessageBox, QSplitter,
    QFrame, QHeaderView, QAbstractItemView, QFileDialog, QCheckBox,
    QScrollArea, QSizePolicy
)
from PySide6.QtCore import Qt, QThread, Signal, QTimer
from PySide6.QtGui import QPixmap, QImage, QIcon, QFont

from src.database import DatabaseManager
from src.busqueda_semantica import BuscadorSemantico
from src.qdrant_manager import QdrantManager
from src.batch_processor import BatchProcessor
from src.models import ConsultaBusqueda, ResultadoBusqueda, ImagenDocumento


class WorkerThread(QThread):
    """Hilo de trabajo para operaciones que pueden tomar tiempo."""

    # Señales para comunicar resultados
    busqueda_completada = Signal(list)
    procesamiento_completado = Signal(object)
    error_ocurrido = Signal(str)
    progreso_actualizado = Signal(int, str)

    def __init__(self, funcion, *args, cancel_callback=None):
        super().__init__()
        self.funcion = funcion
        self.args = args
        self.cancel_callback = cancel_callback

    def run(self):
        """Ejecutar la función en un hilo separado."""
        try:
            if self.funcion == "buscar":
                resultados = self.args[0].buscar_hibrida(self.args[1])
                self.busqueda_completada.emit(resultados)
            elif self.funcion == "procesar":
                documento = self.args[0].procesar_documento(self.args[1], self.cancel_callback)
                self.procesamiento_completado.emit(documento)

            elif self.funcion == "procesar_coleccion":
                batch_processor = self.args[0]
                batch_size = self.args[1]
                max_docs = self.args[2]

                # Simular progreso inicial
                self.progreso_actualizado.emit(5, "Analizando colección...")

                # Verificar cancelación antes de empezar
                if self.cancel_callback and self.cancel_callback():
                    print("🚫 CANCELACIÓN DETECTADA ANTES DE EMPEZAR - WorkerThread")
                    self.progreso_actualizado.emit(0, "Procesamiento cancelado")
                    return

                # Ejecutar procesamiento con verificación de cancelación
                resultado = batch_processor.procesar_coleccion_completa(batch_size, max_docs, self.cancel_callback)

                # El BatchProcessor ya maneja la cancelación internamente
                # Si fue cancelado, el resultado contendrá 'cancelado': True
                self.progreso_actualizado.emit(100, "Procesamiento completado")
                self.procesamiento_completado.emit(resultado)

            elif self.funcion == "backup":
                qdrant_manager = self.args[0]
                ruta_backup = self.args[1]

                # Simular progreso inicial
                self.progreso_actualizado.emit(10, "Obteniendo información de la colección...")

                # Ejecutar backup
                resultado = qdrant_manager.crear_backup_coleccion(ruta_backup)

                self.progreso_actualizado.emit(100, "Backup completado")
                self.procesamiento_completado.emit(resultado)

            elif self.funcion == "backup_mongodb":
                db_manager = self.args[0]
                ruta_backup = self.args[1]

                # Simular progreso inicial
                self.progreso_actualizado.emit(10, "Obteniendo información de la colección...")

                # Ejecutar backup
                resultado = db_manager.crear_backup_coleccion(ruta_backup)

                self.progreso_actualizado.emit(100, "Backup completado")
                self.procesamiento_completado.emit(resultado)

            elif self.funcion == "restore":
                qdrant_manager = self.args[0]
                ruta_backup = self.args[1]
                recrear_coleccion = self.args[2]

                # Simular progreso inicial
                self.progreso_actualizado.emit(10, "Validando archivo de backup...")

                # Ejecutar restauración
                resultado = qdrant_manager.restaurar_coleccion(ruta_backup, recrear_coleccion)

                self.progreso_actualizado.emit(100, "Restauración completada")
                self.procesamiento_completado.emit(resultado)

            elif self.funcion == "restore_mongodb":
                db_manager = self.args[0]
                ruta_backup = self.args[1]
                eliminar_existente = self.args[2]

                # Simular progreso inicial
                self.progreso_actualizado.emit(10, "Validando archivo de backup...")

                # Ejecutar restauración
                resultado = db_manager.restaurar_coleccion(ruta_backup, eliminar_existente)

                self.progreso_actualizado.emit(100, "Restauración completada")
                self.procesamiento_completado.emit(resultado)

            elif self.funcion == "buscar_imagenes":
                directorio = self.args[0]
                busqueda_recursiva = self.args[1]
                solo_nuevas = self.args[2]
                db_manager = self.args[3]
                cancel_callback = self.args[4] if len(self.args) > 4 else None

                # Simular progreso inicial
                self.progreso_actualizado.emit(10, "Analizando directorio...")

                # Verificar cancelación antes de empezar
                if cancel_callback and cancel_callback():
                    print("🚫 CANCELACIÓN DETECTADA ANTES DE EMPEZAR - Buscar Imágenes")
                    self.progreso_actualizado.emit(0, "Búsqueda cancelada")
                    return

                # Ejecutar búsqueda de imágenes con verificación de cancelación
                resultado = self._buscar_imagenes_en_directorio(directorio, busqueda_recursiva, solo_nuevas, db_manager, cancel_callback)

                self.progreso_actualizado.emit(100, "Búsqueda completada")
                self.procesamiento_completado.emit(resultado)

            elif self.funcion == "procesar_imagenes":
                imagenes = self.args[0]
                db_manager = self.args[1]

                # Simular progreso inicial
                self.progreso_actualizado.emit(5, "Preparando procesamiento...")

                # Ejecutar procesamiento de imágenes
                resultado = self._procesar_imagenes_batch(imagenes, db_manager)

                self.progreso_actualizado.emit(100, "Procesamiento completado")
                self.procesamiento_completado.emit(resultado)

        except Exception as e:
            self.error_ocurrido.emit(str(e))

    def _buscar_imagenes_en_directorio(self, directorio: str, busqueda_recursiva: bool, solo_nuevas: bool, db_manager, cancel_callback=None):
        """Buscar imágenes en un directorio."""
        import hashlib
        import os
        from datetime import datetime
        from PIL import Image

        # Importar piexif de forma opcional
        try:
            import piexif
            piexif_disponible = True
        except ImportError:
            piexif_disponible = False

        resultado = {
            'total_encontradas': 0,
            'ya_procesadas': 0,
            'omitidas_por_ruta': 0,
            'omitidas_por_hash': 0,
            'errores': 0,
            'imagenes': [],
            'cancelado': False
        }

        try:
            # Verificar cancelación antes de empezar
            if cancel_callback and cancel_callback():
                print("🚫 CANCELACIÓN DETECTADA ANTES DE EMPEZAR - Buscar Imágenes")
                resultado['cancelado'] = True
                self.progreso_actualizado.emit(0, "Búsqueda cancelada")
                return resultado
            # Extensiones de imagen soportadas
            extensiones_soportadas = {'.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff', '.tif'}

            # Log de estado de piexif
            if piexif_disponible:
                self.progreso_actualizado.emit(5, "Procesamiento EXIF habilitado")
            else:
                self.progreso_actualizado.emit(5, "Procesamiento EXIF no disponible (piexif no instalado)")

            # Obtener lista de archivos de imagen
            archivos_imagen = []
            if busqueda_recursiva:
                for root, dirs, files in os.walk(directorio):
                    for file in files:
                        if any(file.lower().endswith(ext) for ext in extensiones_soportadas):
                            archivos_imagen.append(os.path.join(root, file))
            else:
                for file in os.listdir(directorio):
                    if any(file.lower().endswith(ext) for ext in extensiones_soportadas):
                        archivos_imagen.append(os.path.join(directorio, file))

            resultado['total_encontradas'] = len(archivos_imagen)
            self.progreso_actualizado.emit(30, f"Encontradas {len(archivos_imagen)} imágenes")

            # Verificar cancelación después de encontrar archivos
            if cancel_callback and cancel_callback():
                print("🚫 CANCELACIÓN DETECTADA - Buscar Imágenes")
                resultado['cancelado'] = True
                self.progreso_actualizado.emit(30, "Búsqueda cancelada")
                return resultado

            # Procesar cada imagen
            for i, ruta_imagen in enumerate(archivos_imagen):
                # Verificar cancelación antes de procesar cada imagen
                if cancel_callback and cancel_callback():
                    print("🚫 CANCELACIÓN DETECTADA - Buscar Imágenes")
                    resultado['total_encontradas'] = i  # Actualizar con las procesadas hasta ahora
                    resultado['cancelado'] = True
                    self.progreso_actualizado.emit(progreso, "Búsqueda cancelada")
                    return resultado

                try:
                    # Calcular hash SHA512
                    hash_sha512 = self._calcular_hash_imagen(ruta_imagen)

                    # Verificar si ya existe en la base de datos (por hash o por ruta)
                    if solo_nuevas:
                        # Verificar primero por ruta exacta (más rápido)
                        documento_por_ruta = db_manager.collection.find_one({"ruta": ruta_imagen})
                        if documento_por_ruta:
                            resultado['ya_procesadas'] += 1
                            resultado['omitidas_por_ruta'] += 1
                            self.progreso_actualizado.emit(progreso, f"Imagen ya procesada (ruta): {nombre_archivo}")
                            continue

                        # Verificar también por hash SHA512 (por si la imagen se movió)
                        documento_por_hash = db_manager.collection.find_one({"hash_sha512": hash_sha512})
                        if documento_por_hash:
                            resultado['ya_procesadas'] += 1
                            resultado['omitidas_por_hash'] += 1
                            self.progreso_actualizado.emit(progreso, f"Imagen ya procesada (hash): {nombre_archivo}")
                            continue

                    # Extraer metadatos básicos
                    try:
                        with Image.open(ruta_imagen) as img:
                            ancho, alto = img.size
                            peso = os.path.getsize(ruta_imagen)

                            # Extraer metadatos EXIF (solo si piexif está disponible)
                            metadatos_exif = {}
                            coordenadas_gps = None

                            if piexif_disponible:
                                try:
                                    exif_dict = piexif.load(ruta_imagen)
                                    if exif_dict:
                                        # Extraer fecha de creación si existe
                                        if piexif.ExifIFD.DateTimeOriginal in exif_dict['Exif']:
                                            fecha_original = exif_dict['Exif'][piexif.ExifIFD.DateTimeOriginal].decode('utf-8')
                                            try:
                                                fecha_dt = datetime.strptime(fecha_original, '%Y:%m:%d %H:%M:%S')
                                                metadatos_exif['fecha_creacion'] = fecha_dt
                                            except ValueError:
                                                pass

                                        # Extraer coordenadas GPS si existen
                                        if piexif.GPSIFD.GPSLatitude in exif_dict['GPS'] and piexif.GPSIFD.GPSLongitude in exif_dict['GPS']:
                                            try:
                                                lat = self._convertir_gps_a_decimal(exif_dict['GPS'][piexif.GPSIFD.GPSLatitude], exif_dict['GPS'][piexif.GPSIFD.GPSLatitudeRef])
                                                lon = self._convertir_gps_a_decimal(exif_dict['GPS'][piexif.GPSIFD.GPSLongitude], exif_dict['GPS'][piexif.GPSIFD.GPSLongitudeRef])
                                                coordenadas_gps = [lon, lat]  # [longitud, latitud]
                                            except:
                                                pass
                                except Exception as e:
                                    # Si hay error con EXIF, continuar sin él
                                    pass

                            # Crear documento para la imagen
                            nombre_archivo = os.path.basename(ruta_imagen)
                            ruta_relativa = os.path.relpath(ruta_imagen, directorio)

                            # Extraer fecha actual para timestamps de procesamiento
                            ahora = datetime.now()

                            documento = {
                                "_id": hash_sha512,
                                "id_hash": hash_sha512[:16],  # Primeros 16 caracteres del hash
                                "hash_sha512": hash_sha512,
                                "nombre": nombre_archivo,
                                "ruta": ruta_imagen,
                                "ruta_alternativa": "",  # Se puede dejar vacío por ahora
                                "ancho": ancho,
                                "alto": alto,
                                "peso": peso,
                                "fecha_creacion_dia": metadatos_exif.get('fecha_creacion', ahora).day if 'fecha_creacion' in metadatos_exif else ahora.day,
                                "fecha_creacion_mes": metadatos_exif.get('fecha_creacion', ahora).month if 'fecha_creacion' in metadatos_exif else ahora.month,
                                "fecha_creacion_anio": metadatos_exif.get('fecha_creacion', ahora).year if 'fecha_creacion' in metadatos_exif else ahora.year,
                                "fecha_creacion_hora": metadatos_exif.get('fecha_creacion', ahora).hour if 'fecha_creacion' in metadatos_exif else ahora.hour,
                                "fecha_creacion_minuto": metadatos_exif.get('fecha_creacion', ahora).minute if 'fecha_creacion' in metadatos_exif else ahora.minute,
                                "fecha_procesamiento_dia": ahora.day,
                                "fecha_procesamiento_mes": ahora.month,
                                "fecha_procesamiento_anio": ahora.year,
                                "fecha_procesamiento_hora": ahora.hour,
                                "fecha_procesamiento_minuto": ahora.minute,
                                "coordenadas": coordenadas_gps,
                                "barrio": "",  # Se procesará después si hay coordenadas
                                "calle": "",
                                "ciudad": "",
                                "cp": "",
                                "pais": "",
                                "objeto_procesado": False,
                                "objetos": [],
                                "personas": [],
                                "embedding": [],  # Se generará después
                                "descripcion_semantica": ""  # Se generará después
                            }

                            resultado['imagenes'].append(documento)

                    except Exception as e:
                        resultado['errores'] += 1
                        continue

                except Exception as e:
                    resultado['errores'] += 1
                    continue

                # Actualizar progreso
                progreso = 30 + int((i + 1) / len(archivos_imagen) * 60)
                self.progreso_actualizado.emit(progreso, f"Procesando imagen {i + 1}/{len(archivos_imagen)}")

            self.progreso_actualizado.emit(90, "Finalizando búsqueda...")

        except Exception as e:
            resultado['errores'] += 1

        return resultado

    def _procesar_imagenes_batch(self, imagenes: list, db_manager):
        """Procesar un lote de imágenes."""
        import hashlib
        from datetime import datetime

        resultado = {
            'procesadas': 0,
            'errores': 0,
            'insertadas': 0
        }

        try:
            total_imagenes = len(imagenes)

            for i, imagen in enumerate(imagenes):
                try:
                    # Verificar si la ruta ya existe antes de insertar
                    ruta_imagen = imagen.get('ruta')
                    if db_manager.verificar_ruta_existente(ruta_imagen):
                        self.progreso_actualizado.emit(progreso, f"Imagen ya existe (ruta): {imagen.get('nombre', 'unknown')}")
                        continue

                    # Insertar documento en MongoDB
                    db_manager.collection.insert_one(imagen)
                    resultado['insertadas'] += 1
                    resultado['procesadas'] += 1

                except Exception as e:
                    resultado['errores'] += 1
                    continue

                # Actualizar progreso
                progreso = 10 + int((i + 1) / total_imagenes * 80)
                self.progreso_actualizado.emit(progreso, f"Procesando imagen {i + 1}/{total_imagenes}")

            self.progreso_actualizado.emit(90, "Finalizando procesamiento...")

        except Exception as e:
            resultado['errores'] += 1

        return resultado

    def _calcular_hash_imagen(self, ruta_imagen: str) -> str:
        """Calcular hash SHA512 de una imagen."""
        import hashlib

        hash_sha512 = hashlib.sha512()

        with open(ruta_imagen, "rb") as f:
            # Leer el archivo en bloques para archivos grandes
            for bloque in iter(lambda: f.read(4096), b""):
                hash_sha512.update(bloque)

        return hash_sha512.hexdigest()

    def _convertir_gps_a_decimal(self, coordenadas, referencia):
        """Convertir coordenadas GPS a formato decimal."""
        try:
            # Convertir grados, minutos, segundos a decimal
            grados = coordenadas[0][0] / coordenadas[0][1]
            minutos = coordenadas[1][0] / coordenadas[1][1]
            segundos = coordenadas[2][0] / coordenadas[2][1]

            decimal = grados + (minutos / 60.0) + (segundos / 3600.0)

            # Aplicar signo según la referencia
            if referencia in ['S', 'W']:
                decimal = -decimal

            return decimal
        except:
            return None


class MainWindow(QMainWindow):
    """Ventana principal de la aplicación."""

    def __init__(self):
        super().__init__()
        self.db_manager = None
        self.buscador = None
        self.worker_thread = None
        self.system_initializer = None
        self.cancelar_procesamiento_flag = False
        self.cancelar_busqueda_flag = False

        self.setWindowTitle("Búsqueda Semántica V2")
        self.setGeometry(100, 100, 1200, 800)

        # Inicializar componentes
        self._inicializar_componentes()
        self._crear_interfaz()
        self._conectar_senales()

    def _inicializar_componentes(self):
        """Inicializar componentes principales."""
        try:
            self.db_manager = DatabaseManager()
            self.qdrant_manager = QdrantManager()
            self.batch_processor = BatchProcessor(self.db_manager, self.qdrant_manager)
            self.buscador = BuscadorSemantico(self.db_manager, self.qdrant_manager)

        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error al inicializar el sistema: {str(e)}")

    def _crear_interfaz(self):
        """Crear la interfaz de usuario."""
        # Widget central
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        # Layout principal
        layout = QVBoxLayout(central_widget)

        # Crear pestañas
        self.tab_widget = QTabWidget()
        self.tab_widget.setStyleSheet("""
            QTabWidget::pane {
                border: 3px solid #5A6578;
                border-radius: 15px;
                background: #0F0F0F;
                padding: 8px;
            }
            QTabBar::tab {
                background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1,
                              stop: 0 #3D4758, stop: 1 #2A303C);
                color: #FFFFFF;
                padding: 15px 25px;
                margin-right: 3px;
                border: 3px solid #5A6578;
                border-bottom: none;
                border-radius: 12px 12px 0 0;
                font-size: 14px;
                font-weight: bold;
            }
            QTabBar::tab:selected {
                background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1,
                              stop: 0 #5A6578, stop: 1 #3D4758);
                color: #FFFFFF;
                border: 3px solid #5A6578;
                border-bottom: 3px solid #5A6578;
            }
            QTabBar::tab:hover {
                background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1,
                              stop: 0 #8190A6, stop: 1 #5A6578);
                color: #FFFFFF;
                border: 3px solid #8190A6;
            }
        """)

        # Pestaña de búsqueda
        self.tab_busqueda = self._crear_pestana_busqueda()
        self.tab_widget.addTab(self.tab_busqueda, "Búsqueda")

        # Pestaña de estadísticas
        self.tab_estadisticas = self._crear_pestana_estadisticas()
        self.tab_widget.addTab(self.tab_estadisticas, "Estadísticas")

        # Pestaña de configuración
        self.tab_configuracion = self._crear_pestana_configuracion()
        self.tab_widget.addTab(self.tab_configuracion, "Configuración")

        # Pestaña de procesamiento por lotes
        self.tab_procesamiento = self._crear_pestana_procesamiento()
        self.tab_widget.addTab(self.tab_procesamiento, "Procesar Colección")

        # Pestaña de detección de objetos
        self.tab_deteccion = self._crear_pestana_deteccion_objetos()
        self.tab_widget.addTab(self.tab_deteccion, "Detección de Objetos")

        # Pestaña de backup/restore
        self.tab_backup = self._crear_pestana_backup_restore()
        self.tab_widget.addTab(self.tab_backup, "Backup/Restore")

        # Pestaña de búsqueda de imágenes
        self.tab_buscar_imagenes = self._crear_pestana_buscar_imagenes()
        self.tab_widget.addTab(self.tab_buscar_imagenes, "Buscar Imágenes")

        layout.addWidget(self.tab_widget)

        # Barra de progreso
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                border: 3px solid #5A6578;
                border-radius: 12px;
                background: #0F0F0F;
                color: #FFFFFF;
                font-size: 13px;
                font-weight: bold;
                text-align: center;
                padding: 2px;
            }
            QProgressBar::chunk {
                background: qlineargradient(x1: 0, y1: 0, x2: 1, y2: 1,
                              stop: 0 #8190A6, stop: 1 #5A6578);
                border-radius: 10px;
            }
        """)
        layout.addWidget(self.progress_bar)

        # Actualizar estado inicial de backup después de crear todas las pestañas
        # Se actualizará automáticamente cuando se cambie el tipo de backup

    def _crear_pestana_busqueda(self) -> QWidget:
        """Crear pestaña de búsqueda."""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        # Panel de búsqueda
        grupo_busqueda = QGroupBox("Búsqueda")
        grupo_busqueda.setStyleSheet("""
            QGroupBox {
                font-size: 18px;
                font-weight: bold;
                color: #FFFFFF;
                border: 3px solid #5A6578;
                border-radius: 18px;
                margin-top: 1ex;
                padding: 20px;
                background: #0F0F0F;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 12px;
                padding: 0 15px 0 15px;
                color: #FFFFFF;
                background: #0F0F0F;
                border-radius: 10px;
                margin: 0 5px;
            }
        """)
        layout_busqueda = QFormLayout(grupo_busqueda)

        # Campo de consulta
        self.consulta_input = QLineEdit()
        self.consulta_input.setPlaceholderText("Ingrese su consulta de búsqueda...")
        self.consulta_input.setStyleSheet("""
            QLineEdit {
                background: #0F0F0F;
                color: #FFFFFF;
                font-size: 16px;
                padding: 15px 18px;
                border: 3px solid #5A6578;
                border-radius: 15px;
                selection-background-color: #5A6578;
                selection-color: #FFFFFF;
            }
            QLineEdit:focus {
                border: 3px solid #8190A6;
                background: #0F0F0F;
            }
            QLineEdit:hover {
                border: 3px solid #8190A6;
            }
        """)
        layout_busqueda.addRow("Consulta:", self.consulta_input)

        # Opciones de búsqueda
        opciones_layout = QHBoxLayout()

        # Tipo de búsqueda
        self.tipo_busqueda_combo = QComboBox()
        self.tipo_busqueda_combo.addItems(["Híbrida", "Texto", "Semántica"])
        self.tipo_busqueda_combo.setStyleSheet("""
            QComboBox {
                background: #0F0F0F;
                color: #FFFFFF;
                font-size: 16px;
                padding: 12px 15px;
                border: 3px solid #5A6578;
                border-radius: 12px;
                selection-background-color: #5A6578;
                selection-color: #FFFFFF;
            }
            QComboBox:hover {
                border: 3px solid #8190A6;
            }
            QComboBox::drop-down {
                border: none;
                background: #0F0F0F;
            }
            QComboBox::down-arrow {
                image: none;
                border: none;
            }
            QComboBox QAbstractItemView {
                background: #0F0F0F;
                color: #FFFFFF;
                border: 3px solid #5A6578;
                border-radius: 12px;
                selection-background-color: #5A6578;
                selection-color: #FFFFFF;
            }
        """)
        opciones_layout.addWidget(QLabel("Tipo:"))
        opciones_layout.addWidget(self.tipo_busqueda_combo)

        # Límite de resultados
        self.limite_spin = QSpinBox()
        self.limite_spin.setRange(1, 100)
        self.limite_spin.setValue(10)
        self.limite_spin.setStyleSheet("""
            QSpinBox {
                background: #0F0F0F;
                color: #FFFFFF;
                font-size: 16px;
                padding: 12px 15px;
                border: 3px solid #5A6578;
                border-radius: 12px;
                selection-background-color: #5A6578;
                selection-color: #FFFFFF;
            }
            QSpinBox:hover {
                border: 3px solid #8190A6;
            }
            QSpinBox::up-button, QSpinBox::down-button {
                background: #0F0F0F;
                border: none;
                border-radius: 6px;
            }
            QSpinBox::up-button:hover, QSpinBox::down-button:hover {
                background: #5A6578;
            }
        """)
        opciones_layout.addWidget(QLabel("Límite:"))
        opciones_layout.addWidget(self.limite_spin)

        # Umbral de similitud
        self.umbral_spin = QDoubleSpinBox()
        self.umbral_spin.setRange(0.0, 1.0)
        self.umbral_spin.setSingleStep(0.1)
        self.umbral_spin.setValue(0.7)
        self.umbral_spin.setStyleSheet("""
            QDoubleSpinBox {
                background: #0F0F0F;
                color: #FFFFFF;
                font-size: 16px;
                padding: 12px 15px;
                border: 3px solid #5A6578;
                border-radius: 12px;
                selection-background-color: #5A6578;
                selection-color: #FFFFFF;
            }
            QDoubleSpinBox:hover {
                border: 3px solid #8190A6;
            }
            QDoubleSpinBox::up-button, QDoubleSpinBox::down-button {
                background: #0F0F0F;
                border: none;
                border-radius: 6px;
            }
            QDoubleSpinBox::up-button:hover, QDoubleSpinBox::down-button:hover {
                background: #5A6578;
            }
        """)
        opciones_layout.addWidget(QLabel("Umbral:"))
        opciones_layout.addWidget(self.umbral_spin)

        layout_busqueda.addRow(opciones_layout)

        # Botones de acción
        botones_layout = QHBoxLayout()

        self.buscar_btn = QPushButton("🔍 BÚSQUEDA MANUAL - BUSCAR IMÁGENES")
        self.buscar_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1: 0, y1: 0, x2: 1, y2: 1,
                              stop: 0 #5A6578, stop: 1 #3D4758);
                color: #FFFFFF;
                font-weight: bold;
                font-size: 18px;
                padding: 18px 35px;
                border-radius: 30px;
                min-width: 220px;
                min-height: 55px;
                border: 4px solid #5A6578;
                text-align: center;
            }
            QPushButton:hover {
                background: qlineargradient(x1: 0, y1: 0, x2: 1, y2: 1,
                              stop: 0 #8190A6, stop: 1 #5A6578);
                border: 4px solid #8190A6;
            }
            QPushButton:pressed {
                background: qlineargradient(x1: 0, y1: 0, x2: 1, y2: 1,
                              stop: 0 #3D4758, stop: 1 #2A303C);
                border: 4px solid #5A6578;
            }
            QPushButton:disabled {
                background: #0F0F0F;
                color: #FFFFFF;
                border: 4px solid #5A6578;
            }
        """)
        self.buscar_btn.clicked.connect(self._realizar_busqueda)
        botones_layout.addWidget(self.buscar_btn)

        self.limpiar_btn = QPushButton("Limpiar")
        self.limpiar_btn.clicked.connect(self._limpiar_resultados)
        self.limpiar_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1: 0, y1: 0, x2: 1, y2: 1,
                              stop: 0 #8190A6, stop: 1 #5A6578);
                color: #FFFFFF;
                font-weight: bold;
                font-size: 16px;
                padding: 15px 30px;
                border-radius: 25px;
                border: 4px solid #8190A6;
            }
            QPushButton:hover {
                background: qlineargradient(x1: 0, y1: 0, x2: 1, y2: 1,
                              stop: 0 #5A6578, stop: 1 #3D4758);
                border: 4px solid #5A6578;
            }
            QPushButton:pressed {
                background: qlineargradient(x1: 0, y1: 0, x2: 1, y2: 1,
                              stop: 0 #3D4758, stop: 1 #2A303C);
                border: 4px solid #3D4758;
            }
        """)
        botones_layout.addWidget(self.limpiar_btn)

        layout_busqueda.addRow(botones_layout)

        layout.addWidget(grupo_busqueda)

        # Splitter horizontal para dividir tabla y previsualización
        splitter = QSplitter(Qt.Horizontal)

        # Área de resultados (izquierda)
        grupo_resultados = QGroupBox("Resultados")
        grupo_resultados.setStyleSheet("""
            QGroupBox {
                font-size: 16px;
                font-weight: bold;
                color: #FFFFFF;
                border: 3px solid #5A6578;
                border-radius: 18px;
                margin-top: 1ex;
                padding: 20px;
                background: #0F0F0F;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 12px;
                padding: 0 15px 0 15px;
                color: #FFFFFF;
                background: #0F0F0F;
                border-radius: 10px;
                margin: 0 5px;
            }
        """)
        layout_resultados = QVBoxLayout(grupo_resultados)

        # Tabla de resultados
        self.resultados_table = QTableWidget(0, 5)
        self.resultados_table.setHorizontalHeaderLabels([
            "Nombre", "Ubicación", "Objetos", "Similitud", "Tipo"
        ])
        self.resultados_table.horizontalHeader().setStretchLastSection(True)
        self.resultados_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.resultados_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.resultados_table.doubleClicked.connect(self._mostrar_detalle_imagen)
        self.resultados_table.setStyleSheet("""
            QTableWidget {
                background: #0F0F0F;
                color: #FFFFFF;
                gridline-color: #5A6578;
                border: 3px solid #5A6578;
                border-radius: 15px;
                selection-background-color: #5A6578;
                selection-color: #FFFFFF;
                font-size: 13px;
            }
            QTableWidget::item {
                border: none;
                padding: 10px;
            }
            QTableWidget::item:selected {
                background: #5A6578;
                color: #FFFFFF;
            }
            QHeaderView::section {
                background: qlineargradient(x1: 0, y1: 0, x2: 1, y2: 1,
                              stop: 0 #5A6578, stop: 1 #3D4758);
                color: #FFFFFF;
                font-weight: bold;
                border: none;
                padding: 12px;
                border-radius: 10px;
                margin: 3px;
            }
            QTableWidget QTableCornerButton::section {
                background: qlineargradient(x1: 0, y1: 0, x2: 1, y2: 1,
                              stop: 0 #5A6578, stop: 1 #3D4758);
                border: none;
            }
        """)

        layout_resultados.addWidget(self.resultados_table)
        splitter.addWidget(grupo_resultados)

        # Área de previsualización (derecha)
        grupo_preview = QGroupBox("Previsualización de Imagen")
        grupo_preview.setStyleSheet("""
            QGroupBox {
                font-size: 16px;
                font-weight: bold;
                color: #FFFFFF;
                border: 3px solid #5A6578;
                border-radius: 18px;
                margin-top: 1ex;
                padding: 20px;
                background: #0F0F0F;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 12px;
                padding: 0 15px 0 15px;
                color: #FFFFFF;
                background: #0F0F0F;
                border-radius: 10px;
                margin: 0 5px;
            }
        """)
        layout_preview = QVBoxLayout(grupo_preview)

        # Crear un widget contenedor para centrar ambos elementos
        contenedor_centrado = QWidget()
        layout_centrado = QVBoxLayout(contenedor_centrado)
        layout_centrado.setAlignment(Qt.AlignCenter)

        # Contenedor de la imagen (centrado)
        contenedor_imagen = QWidget()
        layout_imagen = QVBoxLayout(contenedor_imagen)
        layout_imagen.setAlignment(Qt.AlignCenter)

        self.imagen_preview = QLabel()
        self.imagen_preview.setMinimumWidth(320)
        self.imagen_preview.setMaximumWidth(320)
        self.imagen_preview.setMinimumHeight(200)
        self.imagen_preview.setAlignment(Qt.AlignCenter)
        self.imagen_preview.setStyleSheet("""
            QLabel {
                border: 4px dashed #5A6578;
                background: #0F0F0F;
                border-radius: 18px;
            }
        """)
        self.imagen_preview.setText("Selecciona una imagen para previsualizar")
        self.imagen_preview.setStyleSheet("""
            QLabel {
                border: 4px dashed #5A6578;
                background: #0F0F0F;
                color: #FFFFFF;
                font-size: 16px;
                padding: 30px;
                font-weight: 600;
                border-radius: 18px;
            }
        """)
        layout_imagen.addWidget(self.imagen_preview)
        layout_centrado.addWidget(contenedor_imagen)

        # Contenedor de la información (centrado)
        contenedor_info = QWidget()
        layout_info = QVBoxLayout(contenedor_info)
        layout_info.setAlignment(Qt.AlignCenter)

        self.info_imagen = QLabel("Sin información")
        self.info_imagen.setWordWrap(True)
        self.info_imagen.setMinimumHeight(100)
        self.info_imagen.setMaximumHeight(200)
        size_policy = self.info_imagen.sizePolicy()
        size_policy.setHorizontalPolicy(QSizePolicy.Expanding)
        size_policy.setVerticalPolicy(QSizePolicy.Minimum)
        self.info_imagen.setSizePolicy(size_policy)
        self.info_imagen.setAlignment(Qt.AlignCenter)
        self.info_imagen.setStyleSheet("""
            QLabel {
                border: 3px solid #5A6578;
                padding: 18px;
                background: #0F0F0F;
                border-radius: 15px;
                qproperty-alignment: AlignCenter;
                color: #FFFFFF;
                font-size: 14px;
                line-height: 1.6;
                font-weight: 500;
            }
        """)

        # Crear scroll area para la información
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        scroll_area.setWidget(self.info_imagen)
        scroll_area.setMinimumHeight(100)
        scroll_area.setMaximumHeight(200)
        scroll_area.setMinimumWidth(320)
        scroll_area.setMaximumWidth(320)
        scroll_area.setStyleSheet("""
            QScrollArea {
                border: 3px solid #5A6578;
                border-radius: 15px;
                background: #0F0F0F;
            }
            QScrollBar:vertical {
                border: 2px solid #5A6578;
                background: #0F0F0F;
                width: 20px;
                margin: 4px;
                border-radius: 10px;
            }
            QScrollBar::handle:vertical {
                background: #5A6578;
                border-radius: 10px;
                min-height: 25px;
                border: 2px solid #8190A6;
            }
            QScrollBar::handle:vertical:hover {
                background: #8190A6;
                border: 2px solid #5A6578;
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                border: none;
                background: transparent;
                height: 0px;
            }
            QScrollBar:horizontal {
                border: 2px solid #5A6578;
                background: #0F0F0F;
                height: 20px;
                margin: 4px;
                border-radius: 10px;
            }
            QScrollBar::handle:horizontal {
                background: #5A6578;
                border-radius: 10px;
                min-width: 25px;
                border: 2px solid #8190A6;
            }
            QScrollBar::handle:horizontal:hover {
                background: #8190A6;
                border: 2px solid #5A6578;
            }
        """)

        layout_info.addWidget(scroll_area)
        layout_centrado.addWidget(contenedor_info)

        layout_preview.addWidget(contenedor_centrado)

        splitter.addWidget(grupo_preview)

        # Configurar proporciones del splitter (70% tabla, 30% preview)
        splitter.setSizes([700, 320])

        layout.addWidget(splitter)

        return widget

    def _crear_pestana_estadisticas(self) -> QWidget:
        """Crear pestaña de estadísticas."""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        # Información general
        grupo_general = QGroupBox("Información General")
        layout_general = QFormLayout(grupo_general)

        self.total_docs_label = QLabel("0")
        layout_general.addRow("Total de documentos:", self.total_docs_label)

        self.docs_procesados_label = QLabel("0")
        layout_general.addRow("Documentos procesados:", self.docs_procesados_label)

        self.docs_con_embedding_label = QLabel("0")
        layout_general.addRow("Documentos con embedding:", self.docs_con_embedding_label)

        self.tasa_procesamiento_label = QLabel("0%")
        layout_general.addRow("Tasa de procesamiento:", self.tasa_procesamiento_label)

        layout.addWidget(grupo_general)

        # Botones de acción
        botones_layout = QHBoxLayout()

        self.actualizar_stats_btn = QPushButton("Actualizar Estadísticas")
        self.actualizar_stats_btn.clicked.connect(self._actualizar_estadisticas)
        self.actualizar_stats_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1: 0, y1: 0, x2: 1, y2: 1,
                              stop: 0 #4A5568, stop: 1 #2D3748);
                color: #FFFFFF;
                font-weight: bold;
                font-size: 14px;
                padding: 12px 24px;
                border-radius: 20px;
                border: 3px solid #4A5568;
            }
            QPushButton:hover {
                background: qlineargradient(x1: 0, y1: 0, x2: 1, y2: 1,
                              stop: 0 #718096, stop: 1 #4A5568);
                border: 3px solid #718096;
            }
            QPushButton:pressed {
                background: qlineargradient(x1: 0, y1: 0, x2: 1, y2: 1,
                              stop: 0 #2D3748, stop: 1 #1A202C);
                border: 3px solid #2D3748;
            }
        """)
        botones_layout.addWidget(self.actualizar_stats_btn)

        self.procesar_docs_btn = QPushButton("Procesar Documentos Pendientes")
        self.procesar_docs_btn.clicked.connect(self._procesar_documentos_pendientes)
        self.procesar_docs_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1: 0, y1: 0, x2: 1, y2: 1,
                              stop: 0 #4A5568, stop: 1 #2D3748);
                color: #FFFFFF;
                font-weight: bold;
                font-size: 14px;
                padding: 12px 24px;
                border-radius: 20px;
                border: 3px solid #4A5568;
            }
            QPushButton:hover {
                background: qlineargradient(x1: 0, y1: 0, x2: 1, y2: 1,
                              stop: 0 #718096, stop: 1 #4A5568);
                border: 3px solid #718096;
            }
            QPushButton:pressed {
                background: qlineargradient(x1: 0, y1: 0, x2: 1, y2: 1,
                              stop: 0 #2D3748, stop: 1 #1A202C);
                border: 3px solid #2D3748;
            }
        """)
        botones_layout.addWidget(self.procesar_docs_btn)

        layout.addLayout(botones_layout)

        # Área de log
        grupo_log = QGroupBox("Log de Procesamiento")
        layout_log = QVBoxLayout(grupo_log)

        self.log_text = QTextEdit()
        self.log_text.setMaximumHeight(200)
        self.log_text.setStyleSheet("""
            QTextEdit {
                background: #0F0F0F;
                color: #FFFFFF;
                font-size: 13px;
                font-family: 'Consolas', 'Monaco', 'Courier New', monospace;
                border: 3px solid #5A6578;
                border-radius: 15px;
                padding: 12px;
                selection-background-color: #5A6578;
                selection-color: #FFFFFF;
            }
            QTextEdit:focus {
                border: 3px solid #8190A6;
                background: #0F0F0F;
            }
            QTextEdit:hover {
                border: 3px solid #8190A6;
            }
        """)
        layout_log.addWidget(self.log_text)

        layout.addWidget(grupo_log)

        return widget

    def _crear_pestana_configuracion(self) -> QWidget:
        """Crear pestaña de configuración."""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        # Configuración de MongoDB
        grupo_mongodb = QGroupBox("MongoDB")
        layout_mongodb = QFormLayout(grupo_mongodb)

        self.mongodb_uri_input = QLineEdit(os.getenv('MONGODB_URI', 'mongodb://localhost:27017/'))
        self.mongodb_uri_input.setStyleSheet("""
            QLineEdit {
                background: #0F0F0F;
                color: #FFFFFF;
                font-size: 16px;
                padding: 15px 18px;
                border: 3px solid #5A6578;
                border-radius: 15px;
                selection-background-color: #5A6578;
                selection-color: #FFFFFF;
            }
            QLineEdit:focus {
                border: 3px solid #8190A6;
                background: #0F0F0F;
            }
            QLineEdit:hover {
                border: 3px solid #8190A6;
            }
        """)
        layout_mongodb.addRow("URI:", self.mongodb_uri_input)

        self.mongodb_db_input = QLineEdit(os.getenv('MONGODB_DATABASE', 'album'))
        self.mongodb_db_input.setStyleSheet("""
            QLineEdit {
                background: #1A1A1A;
                color: #FFFFFF;
                font-size: 14px;
                padding: 12px 15px;
                border: 2px solid #4A5568;
                border-radius: 12px;
                selection-background-color: #4A5568;
                selection-color: #FFFFFF;
            }
            QLineEdit:focus {
                border: 2px solid #718096;
                background: #1A1A1A;
            }
            QLineEdit:hover {
                border: 2px solid #718096;
            }
        """)
        layout_mongodb.addRow("Base de datos:", self.mongodb_db_input)

        self.mongodb_collection_input = QLineEdit(os.getenv('MONGODB_COLLECTION', 'imagenes_2'))
        self.mongodb_collection_input.setStyleSheet("""
            QLineEdit {
                background: #1A1A1A;
                color: #FFFFFF;
                font-size: 14px;
                padding: 12px 15px;
                border: 2px solid #4A5568;
                border-radius: 12px;
                selection-background-color: #4A5568;
                selection-color: #FFFFFF;
            }
            QLineEdit:focus {
                border: 2px solid #718096;
                background: #1A1A1A;
            }
            QLineEdit:hover {
                border: 2px solid #718096;
            }
        """)
        layout_mongodb.addRow("Colección:", self.mongodb_collection_input)

        layout.addWidget(grupo_mongodb)

        # Configuración de Ollama
        grupo_ollama = QGroupBox("Ollama")
        layout_ollama = QFormLayout(grupo_ollama)

        self.ollama_url_input = QLineEdit(os.getenv('OLLAMA_BASE_URL', 'http://localhost:11434'))
        self.ollama_url_input.setStyleSheet("""
            QLineEdit {
                background: #1A1A1A;
                color: #FFFFFF;
                font-size: 14px;
                padding: 12px 15px;
                border: 2px solid #4A5568;
                border-radius: 12px;
                selection-background-color: #4A5568;
                selection-color: #FFFFFF;
            }
            QLineEdit:focus {
                border: 2px solid #718096;
                background: #1A1A1A;
            }
            QLineEdit:hover {
                border: 2px solid #718096;
            }
        """)
        layout_ollama.addRow("URL base:", self.ollama_url_input)

        self.ollama_model_input = QLineEdit(os.getenv('OLLAMA_MODEL', 'qwen3:14b_40K'))
        self.ollama_model_input.setStyleSheet("""
            QLineEdit {
                background: #1A1A1A;
                color: #FFFFFF;
                font-size: 14px;
                padding: 12px 15px;
                border: 2px solid #4A5568;
                border-radius: 12px;
                selection-background-color: #4A5568;
                selection-color: #FFFFFF;
            }
            QLineEdit:focus {
                border: 2px solid #718096;
                background: #1A1A1A;
            }
            QLineEdit:hover {
                border: 2px solid #718096;
            }
        """)
        layout_ollama.addRow("Modelo:", self.ollama_model_input)

        layout.addWidget(grupo_ollama)

        # Botones de acción
        botones_layout = QHBoxLayout()

        self.guardar_config_btn = QPushButton("Guardar Configuración")
        self.guardar_config_btn.clicked.connect(self._guardar_configuracion)
        self.guardar_config_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1: 0, y1: 0, x2: 1, y2: 1,
                              stop: 0 #4A5568, stop: 1 #2D3748);
                color: #FFFFFF;
                font-weight: bold;
                font-size: 14px;
                padding: 12px 24px;
                border-radius: 20px;
                border: 3px solid #4A5568;
            }
            QPushButton:hover {
                background: qlineargradient(x1: 0, y1: 0, x2: 1, y2: 1,
                              stop: 0 #718096, stop: 1 #4A5568);
                border: 3px solid #718096;
            }
            QPushButton:pressed {
                background: qlineargradient(x1: 0, y1: 0, x2: 1, y2: 1,
                              stop: 0 #2D3748, stop: 1 #1A202C);
                border: 3px solid #2D3748;
            }
        """)
        botones_layout.addWidget(self.guardar_config_btn)

        self.probar_conexion_btn = QPushButton("Probar Conexiones")
        self.probar_conexion_btn.clicked.connect(self._probar_conexiones)
        self.probar_conexion_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1: 0, y1: 0, x2: 1, y2: 1,
                              stop: 0 #4A5568, stop: 1 #2D3748);
                color: #FFFFFF;
                font-weight: bold;
                font-size: 14px;
                padding: 12px 24px;
                border-radius: 20px;
                border: 3px solid #4A5568;
            }
            QPushButton:hover {
                background: qlineargradient(x1: 0, y1: 0, x2: 1, y2: 1,
                              stop: 0 #718096, stop: 1 #4A5568);
                border: 3px solid #718096;
            }
            QPushButton:pressed {
                background: qlineargradient(x1: 0, y1: 0, x2: 1, y2: 1,
                              stop: 0 #2D3748, stop: 1 #1A202C);
                border: 3px solid #2D3748;
            }
        """)
        botones_layout.addWidget(self.probar_conexion_btn)

        layout.addLayout(botones_layout)

        return widget


    def _crear_pestana_procesamiento(self) -> QWidget:
        """Crear pestaña de procesamiento por lotes."""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        # Información del procesamiento
        grupo_info = QGroupBox("Procesamiento de Colección Completa")
        layout_info = QVBoxLayout(grupo_info)

        info_text = QLabel(
            "Esta sección permite procesar TODA la colección 'imagenes_2' de MongoDB "
            "para generar embeddings y guardarlos en Qdrant.\n\n"
            "El proceso incluye:\n"
            "• Análisis de documentos sin embedding\n"
            "• Generación de descripciones semánticas con IA\n"
            "• Creación de vectores de embedding (384 dimensiones)\n"
            "• Almacenamiento en MongoDB y Qdrant\n"
            "• Procesamiento por lotes para eficiencia"
        )
        info_text.setWordWrap(True)
        layout_info.addWidget(info_text)

        layout.addWidget(grupo_info)

        # Estadísticas de la colección
        grupo_stats = QGroupBox("Estadísticas de la Colección")
        layout_stats = QFormLayout(grupo_stats)

        self.total_docs_label = QLabel("0")
        layout_stats.addRow("Total documentos:", self.total_docs_label)

        self.docs_sin_procesar_label = QLabel("0")
        layout_stats.addRow("Sin procesar:", self.docs_sin_procesar_label)

        self.docs_procesados_label = QLabel("0")
        layout_stats.addRow("Procesados:", self.docs_procesados_label)

        self.docs_en_qdrant_label = QLabel("0")
        layout_stats.addRow("En Qdrant:", self.docs_en_qdrant_label)

        self.completitud_label = QLabel("0%")
        layout_stats.addRow("Completitud:", self.completitud_label)

        layout.addWidget(grupo_stats)

        # Configuración del procesamiento
        grupo_config = QGroupBox("Configuración del Procesamiento")
        layout_config = QFormLayout(grupo_config)

        self.batch_size_spin = QSpinBox()
        self.batch_size_spin.setRange(10, 200)
        self.batch_size_spin.setValue(50)
        self.batch_size_spin.setToolTip("Número de documentos a procesar por lote")
        self.batch_size_spin.setStyleSheet("""
            QSpinBox {
                background: #1A1A1A;
                color: #FFFFFF;
                font-size: 14px;
                padding: 8px 12px;
                border: 2px solid #4A5568;
                border-radius: 10px;
                selection-background-color: #4A5568;
                selection-color: #FFFFFF;
            }
            QSpinBox:hover {
                border: 2px solid #718096;
            }
            QSpinBox::up-button, QSpinBox::down-button {
                background: #1A1A1A;
                border: none;
                border-radius: 5px;
            }
            QSpinBox::up-button:hover, QSpinBox::down-button:hover {
                background: #4A5568;
            }
        """)
        layout_config.addRow("Tamaño del lote:", self.batch_size_spin)

        self.max_docs_spin = QSpinBox()
        self.max_docs_spin.setRange(0, 10000)
        self.max_docs_spin.setValue(1000)
        self.max_docs_spin.setSpecialValueText("Todos los documentos")
        self.max_docs_spin.setToolTip("Máximo de documentos a procesar (0 = todos los documentos)")
        self.max_docs_spin.setStyleSheet("""
            QSpinBox {
                background: #1A1A1A;
                color: #FFFFFF;
                font-size: 14px;
                padding: 8px 12px;
                border: 2px solid #4A5568;
                border-radius: 10px;
                selection-background-color: #4A5568;
                selection-color: #FFFFFF;
            }
            QSpinBox:hover {
                border: 2px solid #718096;
            }
            QSpinBox::up-button, QSpinBox::down-button {
                background: #1A1A1A;
                border: none;
                border-radius: 5px;
            }
            QSpinBox::up-button:hover, QSpinBox::down-button:hover {
                background: #4A5568;
            }
        """)
        layout_config.addRow("Máximo documentos:", self.max_docs_spin)

        layout.addWidget(grupo_config)

        # Botones de acción
        botones_layout = QHBoxLayout()

        self.actualizar_stats_btn = QPushButton("Actualizar Estadísticas")
        self.actualizar_stats_btn.clicked.connect(self._actualizar_estadisticas_procesamiento)
        self.actualizar_stats_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1: 0, y1: 0, x2: 1, y2: 1,
                              stop: 0 #4A5568, stop: 1 #2D3748);
                color: #FFFFFF;
                font-weight: bold;
                font-size: 14px;
                padding: 12px 24px;
                border-radius: 20px;
                border: 3px solid #4A5568;
            }
            QPushButton:hover {
                background: qlineargradient(x1: 0, y1: 0, x2: 1, y2: 1,
                              stop: 0 #718096, stop: 1 #4A5568);
                border: 3px solid #718096;
            }
            QPushButton:pressed {
                background: qlineargradient(x1: 0, y1: 0, x2: 1, y2: 1,
                              stop: 0 #2D3748, stop: 1 #1A202C);
                border: 3px solid #2D3748;
            }
        """)
        botones_layout.addWidget(self.actualizar_stats_btn)

        self.procesar_btn = QPushButton("Procesar Colección Completa")
        self.procesar_btn.clicked.connect(self._procesar_coleccion_completa)
        self.procesar_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1: 0, y1: 0, x2: 1, y2: 1,
                              stop: 0 #4A5568, stop: 1 #2D3748);
                color: #FFFFFF;
                font-weight: bold;
                font-size: 14px;
                padding: 12px 24px;
                border-radius: 20px;
                border: 3px solid #4A5568;
            }
            QPushButton:hover {
                background: qlineargradient(x1: 0, y1: 0, x2: 1, y2: 1,
                              stop: 0 #718096, stop: 1 #4A5568);
                border: 3px solid #718096;
            }
            QPushButton:pressed {
                background: qlineargradient(x1: 0, y1: 0, x2: 1, y2: 1,
                              stop: 0 #2D3748, stop: 1 #1A202C);
                border: 3px solid #2D3748;
            }
        """)
        botones_layout.addWidget(self.procesar_btn)

        self.cancelar_btn = QPushButton("Cancelar Procesamiento")
        self.cancelar_btn.clicked.connect(self._cancelar_procesamiento)
        self.cancelar_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1: 0, y1: 0, x2: 1, y2: 1,
                              stop: 0 #4A5568, stop: 1 #2D3748);
                color: #FFFFFF;
                font-weight: bold;
                font-size: 14px;
                padding: 12px 24px;
                border-radius: 20px;
                border: 3px solid #4A5568;
            }
            QPushButton:hover {
                background: qlineargradient(x1: 0, y1: 0, x2: 1, y2: 1,
                              stop: 0 #718096, stop: 1 #4A5568);
                border: 3px solid #718096;
            }
            QPushButton:pressed {
                background: qlineargradient(x1: 0, y1: 0, x2: 1, y2: 1,
                              stop: 0 #2D3748, stop: 1 #1A202C);
                border: 3px solid #2D3748;
            }
        """)
        self.cancelar_btn.setEnabled(False)  # Inicialmente deshabilitado
        botones_layout.addWidget(self.cancelar_btn)

        layout.addLayout(botones_layout)

        # Área de progreso
        grupo_progreso = QGroupBox("Progreso del Procesamiento")
        layout_progreso = QVBoxLayout(grupo_progreso)

        self.progreso_bar = QProgressBar()
        self.progreso_bar.setVisible(False)
        self.progreso_bar.setStyleSheet("""
            QProgressBar {
                border: 2px solid #4A5568;
                border-radius: 10px;
                background: #1A1A1A;
                color: #FFFFFF;
                font-size: 12px;
                font-weight: bold;
                text-align: center;
            }
            QProgressBar::chunk {
                background: qlineargradient(x1: 0, y1: 0, x2: 1, y2: 1,
                              stop: 0 #718096, stop: 1 #4A5568);
                border-radius: 8px;
            }
        """)
        layout_progreso.addWidget(self.progreso_bar)

        self.progreso_label = QLabel("Listo para procesar")
        self.progreso_label.setAlignment(Qt.AlignCenter)
        layout_progreso.addWidget(self.progreso_label)

        layout.addWidget(grupo_progreso)

        # Área de log
        grupo_log = QGroupBox("Log de Procesamiento")
        layout_log = QVBoxLayout(grupo_log)

        self.procesamiento_log = QTextEdit()
        self.procesamiento_log.setMaximumHeight(200)
        self.procesamiento_log.setPlaceholderText("Los mensajes de procesamiento aparecerán aquí...")
        self.procesamiento_log.setStyleSheet("""
            QTextEdit {
                background: #0F0F0F;
                color: #FFFFFF;
                font-size: 13px;
                font-family: 'Consolas', 'Monaco', 'Courier New', monospace;
                border: 3px solid #5A6578;
                border-radius: 15px;
                padding: 12px;
                selection-background-color: #5A6578;
                selection-color: #FFFFFF;
            }
            QTextEdit:focus {
                border: 3px solid #8190A6;
                background: #0F0F0F;
            }
            QTextEdit:hover {
                border: 3px solid #8190A6;
            }
        """)
        layout_log.addWidget(self.procesamiento_log)

        layout.addWidget(grupo_log)

        return widget

    def _crear_pestana_deteccion_objetos(self) -> QWidget:
        """Crear pestaña de detección de objetos en segundo plano."""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        # Información del sistema de detección
        grupo_info = QGroupBox("Sistema de Detección de Objetos")
        layout_info = QVBoxLayout(grupo_info)

        info_text = QLabel(
            "⚠️ <b>SISTEMA DE DETECCIÓN DESHABILITADO</b>\n\n"
            "El sistema de detección automática de objetos ha sido deshabilitado. "
            "Ahora debe usar los botones de control manual para procesar las imágenes.\n\n"
            f"📁 <b>Directorio de búsqueda:</b> /mnt/remoto/11/Datos\n\n"
            "💡 <b>Para usar el sistema:</b>\n"
            "• Use 'Procesar Ahora' para analizar imágenes manualmente\n"
            "• Use 'Actualizar Estado' para ver el estado actual\n"
            "• Use 'Detener Procesamiento' para cancelar operaciones\n\n"
            "Características disponibles:\n"
            "• Detección manual de objetos en imágenes\n"
            "• Procesamiento controlado por el usuario\n"
            "• Evita procesar imágenes ya analizadas\n"
            "• Actualización de la base de datos\n"
            "• Modelos de IA para reconocimiento de objetos"
        )
        info_text.setWordWrap(True)
        layout_info.addWidget(info_text)

        layout.addWidget(grupo_info)

        # Estado del sistema
        grupo_estado = QGroupBox("Estado del Sistema")
        layout_estado = QFormLayout(grupo_estado)

        self.deteccion_status_label = QLabel("No inicializado")
        layout_estado.addRow("Estado:", self.deteccion_status_label)

        self.deteccion_documentos_pendientes_label = QLabel("0")
        layout_estado.addRow("Imágenes pendientes:", self.deteccion_documentos_pendientes_label)

        self.deteccion_procesando_label = QLabel("No")
        layout_estado.addRow("Procesando:", self.deteccion_procesando_label)

        self.deteccion_ultima_verificacion_label = QLabel("Nunca")
        layout_estado.addRow("Última verificación:", self.deteccion_ultima_verificacion_label)

        layout.addWidget(grupo_estado)

        # Botones de control
        botones_layout = QHBoxLayout()

        self.actualizar_estado_btn = QPushButton("Actualizar Estado")
        self.actualizar_estado_btn.clicked.connect(self._actualizar_estado_deteccion)
        self.actualizar_estado_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1: 0, y1: 0, x2: 1, y2: 1,
                              stop: 0 #4A5568, stop: 1 #2D3748);
                color: #FFFFFF;
                font-weight: bold;
                font-size: 14px;
                padding: 12px 24px;
                border-radius: 20px;
                border: 3px solid #4A5568;
            }
            QPushButton:hover {
                background: qlineargradient(x1: 0, y1: 0, x2: 1, y2: 1,
                              stop: 0 #718096, stop: 1 #4A5568);
                border: 3px solid #718096;
            }
            QPushButton:pressed {
                background: qlineargradient(x1: 0, y1: 0, x2: 1, y2: 1,
                              stop: 0 #2D3748, stop: 1 #1A202C);
                border: 3px solid #2D3748;
            }
        """)
        botones_layout.addWidget(self.actualizar_estado_btn)

        self.procesar_manual_btn = QPushButton("Procesar Ahora")
        self.procesar_manual_btn.clicked.connect(self._procesar_objetos_manual)
        self.procesar_manual_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1: 0, y1: 0, x2: 1, y2: 1,
                              stop: 0 #4A5568, stop: 1 #2D3748);
                color: #FFFFFF;
                font-weight: bold;
                font-size: 14px;
                padding: 12px 24px;
                border-radius: 20px;
                border: 3px solid #4A5568;
            }
            QPushButton:hover {
                background: qlineargradient(x1: 0, y1: 0, x2: 1, y2: 1,
                              stop: 0 #718096, stop: 1 #4A5568);
                border: 3px solid #718096;
            }
            QPushButton:pressed {
                background: qlineargradient(x1: 0, y1: 0, x2: 1, y2: 1,
                              stop: 0 #2D3748, stop: 1 #1A202C);
                border: 3px solid #2D3748;
            }
        """)
        botones_layout.addWidget(self.procesar_manual_btn)

        self.detener_procesamiento_btn = QPushButton("Detener Procesamiento")
        self.detener_procesamiento_btn.clicked.connect(self._detener_procesamiento)
        self.detener_procesamiento_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1: 0, y1: 0, x2: 1, y2: 1,
                              stop: 0 #4A5568, stop: 1 #2D3748);
                color: #FFFFFF;
                font-weight: bold;
                font-size: 14px;
                padding: 12px 24px;
                border-radius: 20px;
                border: 3px solid #4A5568;
            }
            QPushButton:hover {
                background: qlineargradient(x1: 0, y1: 0, x2: 1, y2: 1,
                              stop: 0 #718096, stop: 1 #4A5568);
                border: 3px solid #718096;
            }
            QPushButton:pressed {
                background: qlineargradient(x1: 0, y1: 0, x2: 1, y2: 1,
                              stop: 0 #2D3748, stop: 1 #1A202C);
                border: 3px solid #2D3748;
            }
        """)
        botones_layout.addWidget(self.detener_procesamiento_btn)

        layout.addLayout(botones_layout)

        # Área de log
        grupo_log = QGroupBox("Log de Detección de Objetos")
        layout_log = QVBoxLayout(grupo_log)

        self.deteccion_log = QTextEdit()
        self.deteccion_log.setMaximumHeight(200)
        self.deteccion_log.setPlaceholderText("Los mensajes de detección de objetos aparecerán aquí...")
        self.deteccion_log.setStyleSheet("""
            QTextEdit {
                background: #1A1A1A;
                color: #FFFFFF;
                font-size: 12px;
                font-family: 'Consolas', 'Monaco', 'Courier New', monospace;
                border: 2px solid #4A5568;
                border-radius: 12px;
                padding: 10px;
                selection-background-color: #4A5568;
                selection-color: #FFFFFF;
            }
            QTextEdit:focus {
                border: 2px solid #718096;
                background: #1A1A1A;
            }
            QTextEdit:hover {
                border: 2px solid #718096;
            }
        """)
        layout_log.addWidget(self.deteccion_log)

        layout.addWidget(grupo_log)

        return widget

    def _crear_pestana_backup_restore(self) -> QWidget:
        """Crear pestaña de backup y restore para Qdrant y MongoDB."""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        # Selector de tipo de backup
        grupo_selector = QGroupBox("Tipo de Backup")
        layout_selector = QVBoxLayout(grupo_selector)

        selector_layout = QHBoxLayout()

        self.backup_tipo_combo = QComboBox()
        self.backup_tipo_combo.addItems(["Qdrant", "MongoDB"])
        self.backup_tipo_combo.setCurrentText("Qdrant")  # Por defecto Qdrant
        self.backup_tipo_combo.currentTextChanged.connect(self._cambiar_tipo_backup)
        self.backup_tipo_combo.setStyleSheet("""
            QComboBox {
                background: #0F0F0F;
                color: #FFFFFF;
                font-size: 16px;
                padding: 12px 15px;
                border: 3px solid #5A6578;
                border-radius: 12px;
                selection-background-color: #5A6578;
                selection-color: #FFFFFF;
            }
            QComboBox:hover {
                border: 3px solid #8190A6;
            }
            QComboBox::drop-down {
                border: none;
                background: #0F0F0F;
            }
            QComboBox::down-arrow {
                image: none;
                border: none;
            }
            QComboBox QAbstractItemView {
                background: #0F0F0F;
                color: #FFFFFF;
                border: 3px solid #5A6578;
                border-radius: 12px;
                selection-background-color: #5A6578;
                selection-color: #FFFFFF;
            }
        """)
        selector_layout.addWidget(QLabel("Sistema:"))
        selector_layout.addWidget(self.backup_tipo_combo)
        selector_layout.addStretch()

        layout_selector.addLayout(selector_layout)
        layout.addWidget(grupo_selector)

        # Información del sistema de backup
        grupo_info = QGroupBox("Sistema de Backup/Restore")
        layout_info = QVBoxLayout(grupo_info)

        # Información para Qdrant
        self.info_qdrant = QLabel(
            "💾 <b>SISTEMA DE COPIAS DE SEGURIDAD - QDRANT</b>\n\n"
            "Este sistema permite crear copias de seguridad completas de la colección "
            "'imagenes_semanticas' de Qdrant y restaurarlas cuando sea necesario.\n\n"
            "Características:\n"
            "• Backup completo de todos los vectores y metadatos\n"
            "• Formato JSON legible y portable\n"
            "• Validación de integridad de archivos\n"
            "• Restauración con opción de recrear colección\n"
            "• Información detallada de operaciones realizadas"
        )

        # Información para MongoDB
        self.info_mongodb = QLabel(
            "💾 <b>SISTEMA DE COPIAS DE SEGURIDAD - MONGODB</b>\n\n"
            "Este sistema permite crear copias de seguridad completas de la colección "
            "'imagenes_2' de MongoDB y restaurarlas cuando sea necesario.\n\n"
            "Características:\n"
            "• Backup completo de todos los documentos y metadatos\n"
            "• Formato JSON legible y portable\n"
            "• Validación de integridad de archivos\n"
            "• Restauración con opción de eliminar colección existente\n"
            "• Información detallada de operaciones realizadas"
        )

        self.info_qdrant.setWordWrap(True)
        self.info_mongodb.setWordWrap(True)
        self.info_qdrant.setVisible(True)
        self.info_mongodb.setVisible(False)

        layout_info.addWidget(self.info_qdrant)
        layout_info.addWidget(self.info_mongodb)

        layout.addWidget(grupo_info)

        # Información de la colección actual
        grupo_coleccion = QGroupBox("Estado de la Colección")
        layout_coleccion = QFormLayout(grupo_coleccion)

        # Labels para Qdrant
        self.backup_total_vectores_label = QLabel("0")
        layout_coleccion.addRow("Total de vectores:", self.backup_total_vectores_label)

        self.backup_tamano_vector_label = QLabel("0")
        layout_coleccion.addRow("Tamaño del vector:", self.backup_tamano_vector_label)

        # Labels para MongoDB
        self.backup_total_documentos_label = QLabel("0")
        layout_coleccion.addRow("Total de documentos:", self.backup_total_documentos_label)

        self.backup_tamano_coleccion_label = QLabel("0")
        layout_coleccion.addRow("Tamaño de la colección:", self.backup_tamano_coleccion_label)

        self.backup_ultimo_backup_label = QLabel("Nunca")
        layout_coleccion.addRow("Último backup:", self.backup_ultimo_backup_label)

        layout.addWidget(grupo_coleccion)

        # Configuración del backup
        grupo_config = QGroupBox("Configuración del Backup")
        layout_config = QFormLayout(grupo_config)

        self.backup_ruta_input = QLineEdit()
        self.backup_ruta_input.setPlaceholderText("Ej: /ruta/al/backup_imagenes_semanticas_2024.json")
        self.backup_ruta_input.setStyleSheet("""
            QLineEdit {
                background: #1A1A1A;
                color: #FFFFFF;
                font-size: 14px;
                padding: 12px 15px;
                border: 2px solid #4A5568;
                border-radius: 12px;
                selection-background-color: #4A5568;
                selection-color: #FFFFFF;
            }
            QLineEdit:focus {
                border: 2px solid #718096;
                background: #1A1A1A;
            }
            QLineEdit:hover {
                border: 2px solid #718096;
            }
        """)
        layout_config.addRow("Ruta del archivo:", self.backup_ruta_input)

        # Botón para seleccionar archivo
        self.backup_seleccionar_btn = QPushButton("Seleccionar Archivo")
        self.backup_seleccionar_btn.clicked.connect(self._seleccionar_archivo_backup)
        self.backup_seleccionar_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1: 0, y1: 0, x2: 1, y2: 1,
                              stop: 0 #FF9800, stop: 1 #F57C00);
                color: #FFFFFF;
                font-weight: bold;
                font-size: 14px;
                padding: 12px 24px;
                border-radius: 20px;
                border: 3px solid #FF9800;
            }
            QPushButton:hover {
                background: qlineargradient(x1: 0, y1: 0, x2: 1, y2: 1,
                              stop: 0 #FF9800, stop: 1 #E65100);
                border: 3px solid #FFB74D;
            }
            QPushButton:pressed {
                background: qlineargradient(x1: 0, y1: 0, x2: 1, y2: 1,
                              stop: 0 #F57C00, stop: 1 #BF360C);
                border: 3px solid #F57C00;
            }
        """)
        layout_config.addRow(self.backup_seleccionar_btn)

        layout.addWidget(grupo_config)

        # Botones de acción
        botones_layout = QHBoxLayout()

        self.backup_crear_btn = QPushButton("Crear Backup")
        self.backup_crear_btn.clicked.connect(self._crear_backup)
        self.backup_crear_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1: 0, y1: 0, x2: 1, y2: 1,
                              stop: 0 #4A5568, stop: 1 #2D3748);
                color: #FFFFFF;
                font-weight: bold;
                font-size: 14px;
                padding: 12px 24px;
                border-radius: 20px;
                border: 3px solid #4A5568;
            }
            QPushButton:hover {
                background: qlineargradient(x1: 0, y1: 0, x2: 1, y2: 1,
                              stop: 0 #718096, stop: 1 #4A5568);
                border: 3px solid #718096;
            }
            QPushButton:pressed {
                background: qlineargradient(x1: 0, y1: 0, x2: 1, y2: 1,
                              stop: 0 #2D3748, stop: 1 #1A202C);
                border: 3px solid #2D3748;
            }
        """)
        botones_layout.addWidget(self.backup_crear_btn)

        self.backup_restaurar_btn = QPushButton("Restaurar Backup")
        self.backup_restaurar_btn.clicked.connect(self._restaurar_backup)
        self.backup_restaurar_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1: 0, y1: 0, x2: 1, y2: 1,
                              stop: 0 #4A5568, stop: 1 #2D3748);
                color: #FFFFFF;
                font-weight: bold;
                font-size: 14px;
                padding: 12px 24px;
                border-radius: 20px;
                border: 3px solid #4A5568;
            }
            QPushButton:hover {
                background: qlineargradient(x1: 0, y1: 0, x2: 1, y2: 1,
                              stop: 0 #718096, stop: 1 #4A5568);
                border: 3px solid #718096;
            }
            QPushButton:pressed {
                background: qlineargradient(x1: 0, y1: 0, x2: 1, y2: 1,
                              stop: 0 #2D3748, stop: 1 #1A202C);
                border: 3px solid #2D3748;
            }
        """)
        botones_layout.addWidget(self.backup_restaurar_btn)

        self.backup_validar_btn = QPushButton("Validar Backup")
        self.backup_validar_btn.clicked.connect(self._validar_backup)
        self.backup_validar_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1: 0, y1: 0, x2: 1, y2: 1,
                              stop: 0 #4A5568, stop: 1 #2D3748);
                color: #FFFFFF;
                font-weight: bold;
                font-size: 14px;
                padding: 12px 24px;
                border-radius: 20px;
                border: 3px solid #4A5568;
            }
            QPushButton:hover {
                background: qlineargradient(x1: 0, y1: 0, x2: 1, y2: 1,
                              stop: 0 #718096, stop: 1 #4A5568);
                border: 3px solid #718096;
            }
            QPushButton:pressed {
                background: qlineargradient(x1: 0, y1: 0, x2: 1, y2: 1,
                              stop: 0 #2D3748, stop: 1 #1A202C);
                border: 3px solid #2D3748;
            }
        """)
        botones_layout.addWidget(self.backup_validar_btn)

        layout.addLayout(botones_layout)

        # Opciones adicionales
        grupo_opciones = QGroupBox("Opciones")
        layout_opciones = QVBoxLayout(grupo_opciones)

        # Opción para Qdrant
        self.backup_recrear_checkbox = QCheckBox("Recrear colección antes de restaurar")
        self.backup_recrear_checkbox.setChecked(True)
        self.backup_recrear_checkbox.setToolTip("Si está marcado, elimina y recrea la colección antes de restaurar")
        self.backup_recrear_checkbox.setVisible(True)
        layout_opciones.addWidget(self.backup_recrear_checkbox)

        # Opción para MongoDB
        self.backup_eliminar_existente_checkbox = QCheckBox("Eliminar colección existente antes de restaurar")
        self.backup_eliminar_existente_checkbox.setChecked(True)
        self.backup_eliminar_existente_checkbox.setToolTip("Si está marcado, elimina la colección existente antes de restaurar")
        self.backup_eliminar_existente_checkbox.setVisible(False)
        layout_opciones.addWidget(self.backup_eliminar_existente_checkbox)

        layout.addWidget(grupo_opciones)

        # Área de progreso
        grupo_progreso = QGroupBox("Progreso de la Operación")
        layout_progreso = QVBoxLayout(grupo_progreso)

        self.backup_progress_bar = QProgressBar()
        self.backup_progress_bar.setVisible(False)
        self.backup_progress_bar.setStyleSheet("""
            QProgressBar {
                border: 2px solid #4A5568;
                border-radius: 10px;
                background: #1A1A1A;
                color: #FFFFFF;
                font-size: 12px;
                font-weight: bold;
                text-align: center;
            }
            QProgressBar::chunk {
                background: qlineargradient(x1: 0, y1: 0, x2: 1, y2: 1,
                              stop: 0 #718096, stop: 1 #4A5568);
                border-radius: 8px;
            }
        """)
        layout_progreso.addWidget(self.backup_progress_bar)

        self.backup_progress_label = QLabel("Listo para operaciones de backup")
        self.backup_progress_label.setAlignment(Qt.AlignCenter)
        layout_progreso.addWidget(self.backup_progress_label)

        layout.addWidget(grupo_progreso)

        # Área de log
        grupo_log = QGroupBox("Log de Backup/Restore")
        layout_log = QVBoxLayout(grupo_log)

        self.backup_log = QTextEdit()
        self.backup_log.setMaximumHeight(200)
        self.backup_log.setPlaceholderText("Los mensajes de backup/restore aparecerán aquí...")
        self.backup_log.setStyleSheet("""
            QTextEdit {
                background: #1A1A1A;
                color: #FFFFFF;
                font-size: 12px;
                font-family: 'Consolas', 'Monaco', 'Courier New', monospace;
                border: 2px solid #4A5568;
                border-radius: 12px;
                padding: 10px;
                selection-background-color: #4A5568;
                selection-color: #FFFFFF;
            }
            QTextEdit:focus {
                border: 2px solid #718096;
                background: #1A1A1A;
            }
            QTextEdit:hover {
                border: 2px solid #718096;
            }
        """)
        layout_log.addWidget(self.backup_log)

        layout.addWidget(grupo_log)

        return widget

    def _cambiar_tipo_backup(self, tipo: str):
        """Cambiar entre tipos de backup (Qdrant/MongoDB)."""
        if tipo == "Qdrant":
            # Mostrar información de Qdrant
            self.info_qdrant.setVisible(True)
            self.info_mongodb.setVisible(False)

            # Mostrar opciones de Qdrant
            self.backup_recrear_checkbox.setVisible(True)
            self.backup_eliminar_existente_checkbox.setVisible(False)

            # Actualizar estado de Qdrant
            self._actualizar_estado_backup_qdrant()

        elif tipo == "MongoDB":
            # Mostrar información de MongoDB
            self.info_qdrant.setVisible(False)
            self.info_mongodb.setVisible(True)

            # Mostrar opciones de MongoDB
            self.backup_recrear_checkbox.setVisible(False)
            self.backup_eliminar_existente_checkbox.setVisible(True)

            # Actualizar estado de MongoDB
            self._actualizar_estado_backup_mongodb()

        # Actualizar el título del grupo de opciones
        grupo_opciones = self.backup_recrear_checkbox.parent().parent()
        if tipo == "Qdrant":
            grupo_opciones.setTitle("Opciones de Qdrant")
        else:
            grupo_opciones.setTitle("Opciones de MongoDB")

    def _seleccionar_archivo_backup(self):
        """Abrir diálogo para seleccionar archivo de backup."""
        from PySide6.QtWidgets import QFileDialog

        tipo_backup = self.backup_tipo_combo.currentText()
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')

        if tipo_backup == "Qdrant":
            nombre_base = f"backup_qdrant_imagenes_semanticas_{timestamp}.json"
            titulo = "Seleccionar archivo de backup Qdrant"
        else:
            nombre_base = f"backup_mongodb_imagenes_2_{timestamp}.json"
            titulo = "Seleccionar archivo de backup MongoDB"

        archivo, _ = QFileDialog.getSaveFileName(
            self,
            titulo,
            nombre_base,
            "Archivos JSON (*.json)"
        )

        if archivo:
            self.backup_ruta_input.setText(archivo)
            self.backup_log.append(f"✓ Archivo seleccionado: {archivo}")

    def _actualizar_estado_backup_qdrant(self):
        """Actualizar información del estado de la colección Qdrant."""
        try:
            if not self.qdrant_manager:
                return

            stats = self.qdrant_manager.obtener_estadisticas()

            self.backup_total_vectores_label.setText(str(stats['total_vectors']))
            self.backup_tamano_vector_label.setText(str(stats['vector_size']))

            # Ocultar labels de MongoDB
            self.backup_total_documentos_label.setVisible(False)
            self.backup_tamano_coleccion_label.setVisible(False)

            # Aquí podrías implementar lógica para mostrar el último backup
            # Por ahora mostrar "No disponible"
            self.backup_ultimo_backup_label.setText("No disponible")

            # Verificar si backup_log existe antes de usarlo
            if hasattr(self, 'backup_log'):
                self.backup_log.append("✓ Estado de backup Qdrant actualizado correctamente")

        except Exception as e:
            # Verificar si backup_log existe antes de usarlo
            if hasattr(self, 'backup_log'):
                self.backup_log.append(f"⚠ Error al actualizar estado Qdrant: {str(e)}")

    def _actualizar_estado_backup_mongodb(self):
        """Actualizar información del estado de la colección MongoDB."""
        try:
            if not self.db_manager:
                return

            stats = self.db_manager.obtener_estadisticas()

            # Mostrar labels de MongoDB
            self.backup_total_documentos_label.setVisible(True)
            self.backup_tamano_coleccion_label.setVisible(True)

            self.backup_total_documentos_label.setText(str(stats['total_documentos']))
            self.backup_tamano_coleccion_label.setText(f"{stats['tasa_procesamiento']:.1f}% procesados")

            # Ocultar labels de Qdrant
            self.backup_total_vectores_label.setVisible(False)
            self.backup_tamano_vector_label.setVisible(False)

            # Aquí podrías implementar lógica para mostrar el último backup
            # Por ahora mostrar "No disponible"
            self.backup_ultimo_backup_label.setText("No disponible")

            # Verificar si backup_log existe antes de usarlo
            if hasattr(self, 'backup_log'):
                self.backup_log.append("✓ Estado de backup MongoDB actualizado correctamente")

        except Exception as e:
            # Verificar si backup_log existe antes de usarlo
            if hasattr(self, 'backup_log'):
                self.backup_log.append(f"⚠ Error al actualizar estado MongoDB: {str(e)}")

    def _actualizar_estado_backup(self):
        """Actualizar información del estado de la colección (método legacy)."""
        tipo_backup = self.backup_tipo_combo.currentText()
        if tipo_backup == "Qdrant":
            self._actualizar_estado_backup_qdrant()
        else:
            self._actualizar_estado_backup_mongodb()

    def _crear_backup(self):
        """Crear backup de la colección."""
        try:
            ruta_backup = self.backup_ruta_input.text().strip()

            if not ruta_backup:
                QMessageBox.warning(self, "Error", "Seleccione una ruta para el archivo de backup")
                return

            tipo_backup = self.backup_tipo_combo.currentText()

            # Confirmar creación de backup
            if tipo_backup == "Qdrant":
                coleccion = self.qdrant_manager.collection_name
            else:
                coleccion = self.db_manager.collection.name

            reply = QMessageBox.question(
                self, "Confirmar Backup",
                f"¿Está seguro de que desea crear un backup de la colección '{coleccion}' ({tipo_backup})?\n"
                f"El archivo se guardará en: {ruta_backup}",
                QMessageBox.Yes | QMessageBox.No, QMessageBox.Yes
            )

            if reply != QMessageBox.Yes:
                return

            # Mostrar progreso
            self.backup_progress_bar.setVisible(True)
            self.backup_progress_bar.setRange(0, 0)  # Indefinido
            self.backup_progress_label.setText("Creando backup...")
            self.backup_log.clear()
            self.backup_log.append(f"🔄 Iniciando creación de backup de {tipo_backup}...")

            # Deshabilitar botones
            self.backup_crear_btn.setEnabled(False)
            self.backup_restaurar_btn.setEnabled(False)
            self.backup_validar_btn.setEnabled(False)

            # Crear hilo de trabajo para el backup
            if tipo_backup == "Qdrant":
                self.backup_thread = WorkerThread("backup", self.qdrant_manager, ruta_backup)
            else:
                self.backup_thread = WorkerThread("backup_mongodb", self.db_manager, ruta_backup)
            self.backup_thread.progreso_actualizado.connect(self._actualizar_progreso_backup)
            self.backup_thread.procesamiento_completado.connect(self._backup_completado)
            self.backup_thread.error_ocurrido.connect(self._error_backup)
            self.backup_thread.start()

        except Exception as e:
            self.backup_log.append(f"❌ Error al iniciar backup: {str(e)}")
            QMessageBox.critical(self, "Error", f"Error al iniciar backup: {str(e)}")

    def _restaurar_backup(self):
        """Restaurar backup de la colección."""
        try:
            ruta_backup = self.backup_ruta_input.text().strip()

            if not ruta_backup:
                QMessageBox.warning(self, "Error", "Seleccione una ruta del archivo de backup")
                return

            if not os.path.exists(ruta_backup):
                QMessageBox.warning(self, "Error", f"El archivo de backup no existe: {ruta_backup}")
                return

            tipo_backup = self.backup_tipo_combo.currentText()

            # Confirmar restauración
            if tipo_backup == "Qdrant":
                coleccion = self.qdrant_manager.collection_name
                eliminar_existente = self.backup_recrear_checkbox.isChecked()
                opcion_text = "La colección actual será eliminada y recreada. " if eliminar_existente else ""
            else:
                coleccion = self.db_manager.collection.name
                eliminar_existente = self.backup_eliminar_existente_checkbox.isChecked()
                opcion_text = "La colección actual será eliminada. " if eliminar_existente else ""

            reply = QMessageBox.question(
                self, "Confirmar Restauración",
                f"¿Está seguro de que desea restaurar la colección '{coleccion}' ({tipo_backup}) desde '{ruta_backup}'?\n"
                f"{opcion_text}"
                "Esta operación no se puede deshacer.",
                QMessageBox.Yes | QMessageBox.No, QMessageBox.No
            )

            if reply != QMessageBox.Yes:
                return

            # Mostrar progreso
            self.backup_progress_bar.setVisible(True)
            self.backup_progress_bar.setRange(0, 0)  # Indefinido
            self.backup_progress_label.setText("Restaurando backup...")
            self.backup_log.clear()
            self.backup_log.append(f"🔄 Iniciando restauración de backup de {tipo_backup}...")

            # Deshabilitar botones
            self.backup_crear_btn.setEnabled(False)
            self.backup_restaurar_btn.setEnabled(False)
            self.backup_validar_btn.setEnabled(False)

            # Crear hilo de trabajo para la restauración
            if tipo_backup == "Qdrant":
                self.restore_thread = WorkerThread("restore", self.qdrant_manager, ruta_backup, eliminar_existente)
            else:
                self.restore_thread = WorkerThread("restore_mongodb", self.db_manager, ruta_backup, eliminar_existente)
            self.restore_thread.progreso_actualizado.connect(self._actualizar_progreso_restore)
            self.restore_thread.procesamiento_completado.connect(self._restore_completado)
            self.restore_thread.error_ocurrido.connect(self._error_restore)
            self.restore_thread.start()

        except Exception as e:
            self.backup_log.append(f"❌ Error al iniciar restauración: {str(e)}")
            QMessageBox.critical(self, "Error", f"Error al iniciar restauración: {str(e)}")

    def _validar_backup(self):
        """Validar archivo de backup."""
        try:
            ruta_backup = self.backup_ruta_input.text().strip()

            if not ruta_backup:
                QMessageBox.warning(self, "Error", "Seleccione una ruta del archivo de backup")
                return

            if not os.path.exists(ruta_backup):
                QMessageBox.warning(self, "Error", f"El archivo de backup no existe: {ruta_backup}")
                return

            tipo_backup = self.backup_tipo_combo.currentText()

            self.backup_log.clear()
            self.backup_log.append(f"🔍 Validando archivo de backup de {tipo_backup}...")

            # Validar backup
            if tipo_backup == "Qdrant":
                resultado = self.qdrant_manager.validar_backup(ruta_backup)
                tipo_dato = "vectores"
                cantidad = resultado.get('total_vectores', 0)
            else:
                resultado = self.db_manager.validar_backup(ruta_backup)
                tipo_dato = "documentos"
                cantidad = resultado.get('total_documentos', 0)

            if resultado["valido"]:
                self.backup_log.append("✅ Validación exitosa:")
                self.backup_log.append(f"   • Archivo: {resultado['ruta']}")
                self.backup_log.append(f"   • Tamaño: {resultado['tamano_archivo']} bytes")
                self.backup_log.append(f"   • {tipo_dato.title()}: {cantidad}")
                self.backup_log.append(f"   • Fecha backup: {resultado['fecha_backup']}")
                self.backup_log.append(f"   • Hash SHA256: {resultado['hash_sha256'][:16]}...")

                QMessageBox.information(
                    self, "Validación Exitosa",
                    f"Backup válido:\n"
                    f"• {cantidad} {tipo_dato}\n"
                    f"• Tamaño: {resultado['tamano_archivo']} bytes\n"
                    f"• Fecha: {resultado['fecha_backup']}"
                )
            else:
                self.backup_log.append(f"❌ Error de validación: {resultado['error']}")

                QMessageBox.warning(
                    self, "Error de Validación",
                    f"Backup inválido:\n{resultado['error']}"
                )

        except Exception as e:
            self.backup_log.append(f"❌ Error al validar backup: {str(e)}")
            QMessageBox.critical(self, "Error", f"Error al validar backup: {str(e)}")

    def _actualizar_progreso_backup(self, progreso: int, mensaje: str):
        """Actualizar progreso del backup."""
        self.backup_progress_bar.setValue(progreso)
        self.backup_progress_label.setText(mensaje)
        self.backup_log.append(f"Progreso: {progreso}% - {mensaje}")

    def _backup_completado(self, resultado: dict):
        """Manejador para cuando termina el backup."""
        # Rehabilitar botones
        self.backup_crear_btn.setEnabled(True)
        self.backup_restaurar_btn.setEnabled(True)
        self.backup_validar_btn.setEnabled(True)

        # Ocultar progreso
        self.backup_progress_bar.setVisible(False)

        if resultado:
            tipo_backup = self.backup_tipo_combo.currentText()

            if tipo_backup == "Qdrant":
                tipo_dato = "vectores"
                cantidad = resultado.get('total_vectores', 0)
            else:
                tipo_dato = "documentos"
                cantidad = resultado.get('total_documentos', 0)

            self.backup_progress_label.setText("Backup completado")
            self.backup_log.append(f"\n=== BACKUP {tipo_backup.upper()} COMPLETADO ===")
            self.backup_log.append(f"✓ Archivo: {resultado.get('ruta_archivo', 'Desconocido')}")
            self.backup_log.append(f"✓ {tipo_dato.title()}: {cantidad}")
            self.backup_log.append(f"✓ Tamaño: {resultado.get('tamano_archivo', 0)} bytes")
            self.backup_log.append(f"✓ Hash: {resultado.get('hash_sha256', 'N/A')[:16]}...")
            self.backup_log.append(f"✓ Fecha: {resultado.get('fecha_backup', 'N/A')}")

            QMessageBox.information(
                self, "Backup Completado",
                f"Backup {tipo_backup} creado exitosamente:\n"
                f"• Archivo: {resultado.get('ruta_archivo', 'Desconocido')}\n"
                f"• {tipo_dato.title()}: {cantidad}\n"
                f"• Tamaño: {resultado.get('tamano_archivo', 0)} bytes"
            )

            # Actualizar estado
            self._actualizar_estado_backup()
        else:
            self.backup_progress_label.setText("Backup completado")
            self.backup_log.append("Backup completado sin resultado detallado")

    def _actualizar_progreso_restore(self, progreso: int, mensaje: str):
        """Actualizar progreso de la restauración."""
        self.backup_progress_bar.setValue(progreso)
        self.backup_progress_label.setText(mensaje)
        self.backup_log.append(f"Progreso: {progreso}% - {mensaje}")

    def _restore_completado(self, resultado: dict):
        """Manejador para cuando termina la restauración."""
        # Rehabilitar botones
        self.backup_crear_btn.setEnabled(True)
        self.backup_restaurar_btn.setEnabled(True)
        self.backup_validar_btn.setEnabled(True)

        # Ocultar progreso
        self.backup_progress_bar.setVisible(False)

        if resultado:
            tipo_backup = self.backup_tipo_combo.currentText()

            if tipo_backup == "Qdrant":
                tipo_dato = "vectores"
                cantidad_restaurada = resultado.get('total_vectores_restaurados', 0)
                cantidad_total = resultado.get('total_vectores_en_coleccion', 0)
            else:
                tipo_dato = "documentos"
                cantidad_restaurada = resultado.get('total_documentos_restaurados', 0)
                cantidad_total = resultado.get('total_documentos_en_coleccion', 0)

            self.backup_progress_label.setText("Restauración completada")
            self.backup_log.append(f"\n=== RESTAURACIÓN {tipo_backup.upper()} COMPLETADA ===")
            self.backup_log.append(f"✓ {tipo_dato.title()} restaurados: {cantidad_restaurada}")
            self.backup_log.append(f"✓ {tipo_dato.title()} en colección: {cantidad_total}")
            self.backup_log.append(f"✓ Fecha restauración: {resultado.get('fecha_restauracion', 'N/A')}")

            QMessageBox.information(
                self, "Restauración Completada",
                f"Restauración {tipo_backup} completada exitosamente:\n"
                f"• {tipo_dato.title()} restaurados: {cantidad_restaurada}\n"
                f"• {tipo_dato.title()} en colección: {cantidad_total}"
            )

            # Actualizar estado
            self._actualizar_estado_backup()
        else:
            self.backup_progress_label.setText("Restauración completada")
            self.backup_log.append("Restauración completada sin resultado detallado")

    def _error_backup(self, error_msg: str):
        """Mostrar mensaje de error de backup."""
        QMessageBox.critical(self, "Error de Backup", f"Error durante el backup: {error_msg}")

        # Rehabilitar botones y ocultar progreso
        self.backup_crear_btn.setEnabled(True)
        self.backup_restaurar_btn.setEnabled(True)
        self.backup_validar_btn.setEnabled(True)
        self.backup_progress_bar.setVisible(False)
        self.backup_progress_label.setText("Error en backup")

        self.backup_log.append(f"❌ Error durante el backup: {error_msg}")
        self.backup_log.append("=== BACKUP INTERRUMPIDO POR ERROR ===")

    def _error_restore(self, error_msg: str):
        """Mostrar mensaje de error de restauración."""
        QMessageBox.critical(self, "Error de Restauración", f"Error durante la restauración: {error_msg}")

        # Rehabilitar botones y ocultar progreso
        self.backup_crear_btn.setEnabled(True)
        self.backup_restaurar_btn.setEnabled(True)
        self.backup_validar_btn.setEnabled(True)
        self.backup_progress_bar.setVisible(False)
        self.backup_progress_label.setText("Error en restauración")

        self.backup_log.append(f"❌ Error durante la restauración: {error_msg}")
        self.backup_log.append("=== RESTAURACIÓN INTERRUMPIDA POR ERROR ===")

    def _conectar_senales(self):
        """Conectar señales de la interfaz."""
        # Conectar cambios en la consulta para autocompletado
        self.consulta_input.textChanged.connect(self._actualizar_sugerencias)

    def _realizar_busqueda(self):
        """Realizar búsqueda con los parámetros actuales."""
        if not self.buscador:
            QMessageBox.warning(self, "Error", "Sistema no inicializado")
            return

        consulta_texto = self.consulta_input.text().strip()
        if not consulta_texto:
            QMessageBox.warning(self, "Error", "Ingrese una consulta de búsqueda")
            return

        # Crear consulta
        consulta = ConsultaBusqueda(
            query=consulta_texto,
            limite=self.limite_spin.value(),
            umbral_similitud=self.umbral_spin.value()
        )

        # Mostrar progreso
        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, 0)  # Indefinido
        self.buscar_btn.setEnabled(False)

        # Crear y ejecutar hilo de trabajo
        self.worker_thread = WorkerThread("buscar", self.buscador, consulta)
        self.worker_thread.busqueda_completada.connect(self._mostrar_resultados)
        self.worker_thread.error_ocurrido.connect(self._mostrar_error)
        self.worker_thread.finished.connect(self._busqueda_finalizada)
        self.worker_thread.start()

    def _mostrar_resultados(self, resultados: List[ResultadoBusqueda]):
        """Mostrar resultados de búsqueda en la tabla."""
        self.resultados_table.setRowCount(0)

        for resultado in resultados:
            row = self.resultados_table.rowCount()
            self.resultados_table.insertRow(row)

            # Nombre
            nombre_item = QTableWidgetItem(resultado.documento.nombre)
            self.resultados_table.setItem(row, 0, nombre_item)

            # Ubicación
            ubicacion = ", ".join([
                resultado.documento.ciudad,
                resultado.documento.barrio,
                resultado.documento.calle
            ]).strip(", ")
            ubicacion_item = QTableWidgetItem(ubicacion or "No especificada")
            self.resultados_table.setItem(row, 1, ubicacion_item)

            # Objetos
            objetos = ", ".join(resultado.documento.objetos) if resultado.documento.objetos else "Ninguno"
            objetos_item = QTableWidgetItem(objetos)
            self.resultados_table.setItem(row, 2, objetos_item)

            # Similitud
            similitud_item = QTableWidgetItem(f"{resultado.similitud:.3f}")
            self.resultados_table.setItem(row, 3, similitud_item)

            # Tipo
            tipo_item = QTableWidgetItem(resultado.tipo_busqueda)
            self.resultados_table.setItem(row, 4, tipo_item)

    def _mostrar_detalle_imagen(self, index):
        """Mostrar detalles de una imagen seleccionada."""
        row = index.row()
        if row < 0:
            return

        # Obtener documento de la fila seleccionada
        nombre = self.resultados_table.item(row, 0).text()

        try:
            # Buscar el documento en la base de datos
            documento_data = self.db_manager.collection.find_one({"nombre": nombre})

            if not documento_data:
                self._mostrar_error_imagen("Documento no encontrado en la base de datos")
                return

            # Convertir a objeto ImagenDocumento
            documento = ImagenDocumento(**documento_data)

            # Limpiar área de previsualización
            self.imagen_preview.clear()

            # Restaurar el QLabel original si fue reemplazado por un error
            if not hasattr(self.info_imagen, 'parent') or self.info_imagen.parent() is None:
                # Crear un nuevo QLabel si no existe
                self.info_imagen = QLabel("Sin información")
                self.info_imagen.setWordWrap(True)
                self.info_imagen.setAlignment(Qt.AlignCenter)
                self.info_imagen.setStyleSheet("""
                    QLabel {
                        border: 3px solid #5A6578;
                        padding: 15px;
                        background: #0F0F0F;
                        border-radius: 12px;
                        qproperty-alignment: AlignCenter;
                        color: #FFFFFF;
                        font-size: 14px;
                        line-height: 1.6;
                        font-weight: 500;
                    }
                """)

                # Buscar el contenedor de información y establecer el widget
                for child in self.findChildren(QWidget):
                    if child.layout() and hasattr(child.layout(), 'setAlignment'):
                        # Buscar el scroll area dentro del contenedor de información
                        for scroll_child in child.findChildren(QScrollArea):
                            if scroll_child.widget() is None or not hasattr(scroll_child.widget(), 'text'):
                                scroll_child.setWidget(self.info_imagen)
                                break

            self.info_imagen.clear()

            # Extraer ubicación del campo ruta
            ubicacion = "No especificada"
            if documento.ruta:
                try:
                    # Obtener el directorio padre de la ruta
                    ruta_dir = os.path.dirname(documento.ruta)
                    if ruta_dir and ruta_dir != ".":
                        ubicacion = ruta_dir
                    else:
                        ubicacion = documento.ruta
                except Exception as e:
                    debug_info += f"⚠ Error al procesar ubicación: {str(e)}\n"
                    ubicacion = documento.ruta or "Error al procesar ruta"

            # Mostrar información básica con mejor formato
            info_text = f"""
            <div style='text-align: center;'>
            <h4>📋 Información de la Imagen</h4>
            <hr>
            <p><b>🏷️ Nombre:</b> {documento.nombre}</p>
            <p><b>📍 Ubicación:</b> {ubicacion}</p>
            <p><b>📐 Dimensiones:</b> {documento.ancho}x{documento.alto}px</p>
            <p><b>💾 Peso:</b> {documento.peso/1024:.1f} KB</p>
            <p><b>🔍 Objetos detectados:</b></p>
            <p style='margin-left: 20px; color: #333; text-align: center;'>
            {('<br>').join(f'• {objeto}' for objeto in documento.objetos) if documento.objetos else 'Ninguno'}
            </p>
            <p><b>✅ Procesado:</b> {'Sí' if documento.objeto_procesado else 'No'}</p>
            </div>
            """
            self.info_imagen.setText(info_text)

            # Intentar cargar la imagen
            imagen_cargada = False

            # Debug: mostrar información de rutas
            debug_info = f"Nombre: {documento.nombre}\n"
            debug_info += f"Ruta principal: {documento.ruta}\n"
            debug_info += f"Ruta alternativa: {documento.ruta_alternativa}\n"

            # Probar con la ruta principal
            if documento.ruta:
                debug_info += f"Verificando ruta principal: {documento.ruta}\n"
                if os.path.exists(documento.ruta):
                    debug_info += "✓ Ruta principal existe\n"
                    try:
                        pixmap = QPixmap(documento.ruta)
                        if not pixmap.isNull():
                            debug_info += "✓ Imagen cargada correctamente\n"
                            self._mostrar_imagen(pixmap)
                            imagen_cargada = True
                        else:
                            debug_info += "✗ QPixmap isNull() - formato no soportado\n"
                    except Exception as e:
                        debug_info += f"✗ Error al cargar imagen: {str(e)}\n"
                else:
                    debug_info += "✗ Ruta principal no existe\n"
            else:
                debug_info += "✗ No hay ruta principal\n"

            # Si no funcionó, probar con la ruta alternativa
            if not imagen_cargada and documento.ruta_alternativa:
                debug_info += f"Verificando ruta alternativa: {documento.ruta_alternativa}\n"
                if os.path.exists(documento.ruta_alternativa):
                    debug_info += "✓ Ruta alternativa existe\n"
                    try:
                        pixmap = QPixmap(documento.ruta_alternativa)
                        if not pixmap.isNull():
                            debug_info += "✓ Imagen cargada desde ruta alternativa\n"
                            self._mostrar_imagen(pixmap)
                            imagen_cargada = True
                        else:
                            debug_info += "✗ QPixmap isNull() - formato no soportado en ruta alternativa\n"
                    except Exception as e:
                        debug_info += f"✗ Error al cargar imagen alternativa: {str(e)}\n"
                else:
                    debug_info += "✗ Ruta alternativa no existe\n"

            # Si no se pudo cargar la imagen
            if not imagen_cargada:
                debug_info += "❌ No se pudo cargar la imagen desde ninguna ruta\n"
                self._mostrar_error_imagen(f"No se pudo cargar la imagen desde las rutas disponibles\n\nDebug:\n{debug_info}")
            else:
                # Limpiar información de debug si la imagen se cargó correctamente
                self.info_imagen.setText(info_text)

        except Exception as e:
            self._mostrar_error_imagen(f"Error al cargar la imagen: {str(e)}")

    def _mostrar_imagen(self, pixmap: QPixmap):
        """Mostrar imagen en el área de previsualización con tamaño fijo."""
        # Escalar la imagen manteniendo la proporción
        # Ancho fijo de 320px, altura proporcional
        scaled_pixmap = pixmap.scaledToWidth(
            320,
            Qt.SmoothTransformation
        )

        self.imagen_preview.setPixmap(scaled_pixmap)
        self.imagen_preview.setMinimumHeight(scaled_pixmap.height())
        self.imagen_preview.setMaximumHeight(scaled_pixmap.height())

    def _mostrar_error_imagen(self, mensaje: str):
        """Mostrar mensaje de error en el área de previsualización."""
        self.imagen_preview.clear()
        self.imagen_preview.setText(f"Error:\n{mensaje}")
        error_text = f"""
        <div style='text-align: center; color: #FFFFFF; padding: 10px;'>
        <h4>❌ Error al cargar la imagen</h4>
        <p>No se pudo cargar la información de la imagen</p>
        </div>
        """
        # Crear un nuevo QLabel para el error para mantener la funcionalidad del scroll
        error_label = QLabel(error_text)
        error_label.setWordWrap(True)
        error_label.setAlignment(Qt.AlignCenter)
        error_label.setStyleSheet("""
            QLabel {
                border: 3px solid #d32f2f;
                padding: 12px;
                background: #0F0F0F;
                border-radius: 8px;
                color: #FFFFFF;
            }
        """)

        # Buscar el contenedor de información y reemplazar el widget en el scroll area
        for child in self.findChildren(QWidget):
            if child.layout() and hasattr(child.layout(), 'setAlignment'):
                # Buscar el scroll area dentro del contenedor de información
                for scroll_child in child.findChildren(QScrollArea):
                    scroll_child.setWidget(error_label)
                    # Guardar referencia al label de error para poder restaurarlo después
                    self.info_imagen = error_label
                    break

    def _limpiar_resultados(self):
        """Limpiar resultados de búsqueda."""
        self.resultados_table.setRowCount(0)
        self.consulta_input.clear()

    def _actualizar_estadisticas(self):
        """Actualizar estadísticas mostradas."""
        if not self.db_manager:
            return

        try:
            stats = self.db_manager.obtener_estadisticas()

            self.total_docs_label.setText(str(stats['total_documentos']))
            self.docs_procesados_label.setText(str(stats['documentos_procesados']))
            self.docs_con_embedding_label.setText(str(stats['documentos_con_embedding']))
            self.tasa_procesamiento_label.setText(f"{stats['tasa_procesamiento']:.1f}%")

        except Exception as e:
            QMessageBox.warning(self, "Error", f"Error al actualizar estadísticas: {str(e)}")

    def _procesar_documentos_pendientes(self):
        """Procesar documentos que no tienen embedding."""
        if not self.buscador:
            QMessageBox.warning(self, "Error", "Sistema no inicializado")
            return

        # Obtener documentos sin procesar
        documentos_pendientes = list(self.db_manager.collection.find(
            {"$or": [
                {"objeto_procesado": False},
                {"embedding": {"$exists": False}}
            ]}
        ).limit(10))

        if not documentos_pendientes:
            QMessageBox.information(self, "Información", "No hay documentos pendientes de procesar")
            return

        # Procesar documentos
        self.log_text.append(f"Iniciando procesamiento de {len(documentos_pendientes)} documentos...")

        for doc_data in documentos_pendientes:
            try:
                documento = self.db_manager.obtener_documento_por_id(doc_data["_id"])
                if documento:
                    self.buscador.procesar_documento(documento, None)  # Sin callback para procesamiento individual
                    self.log_text.append(f"✓ Procesado: {documento.nombre}")
            except Exception as e:
                self.log_text.append(f"✗ Error procesando {doc_data.get('nombre', 'desconocido')}: {str(e)}")

        self.log_text.append("Procesamiento completado.")
        self._actualizar_estadisticas()

    def _guardar_configuracion(self):
        """Guardar configuración en archivo .env."""
        # Aquí podrías implementar guardar la configuración
        QMessageBox.information(self, "Configuración", "Configuración guardada (funcionalidad pendiente)")

    def _probar_conexiones(self):
        """Probar conexiones a MongoDB, Qdrant y Ollama."""
        try:
            # Probar MongoDB
            self.db_manager.client.admin.command('ping')
            QMessageBox.information(self, "Conexión", "✓ MongoDB conectado correctamente")

            # Probar Qdrant
            try:
                self.qdrant_manager.client.get_collections()
                QMessageBox.information(self, "Conexión", "✓ Qdrant conectado correctamente")
            except Exception as qdrant_error:
                QMessageBox.warning(self, "Error de Conexión", f"Error con Qdrant: {str(qdrant_error)}")

            # Probar Ollama
            # Aquí podrías implementar una prueba de conexión con Ollama

        except Exception as e:
            QMessageBox.warning(self, "Error de Conexión", f"Error: {str(e)}")





    def _actualizar_estadisticas_procesamiento(self):
        """Actualizar estadísticas de procesamiento."""
        if not self.batch_processor:
            QMessageBox.warning(self, "Error", "Sistema no inicializado")
            return

        try:
            stats = self.batch_processor.obtener_estadisticas_coleccion()

            # Actualizar etiquetas
            self.total_docs_label.setText(str(stats['mongodb']['total_documentos']))
            self.docs_sin_procesar_label.setText(str(stats['resumen']['documentos_pendientes']))
            self.docs_procesados_label.setText(str(stats['mongodb']['documentos_con_embedding']))

            # Obtener documentos en Qdrant
            docs_en_qdrant = self.db_manager.collection.count_documents({"qdrant": True})
            self.docs_en_qdrant_label.setText(str(docs_en_qdrant))

            self.completitud_label.setText(f"{stats['resumen']['completitud']:.1f}%")

            self.procesamiento_log.append(
                f"Estadísticas actualizadas: {stats['mongodb']['documentos_con_embedding']}/{stats['mongodb']['total_documentos']} procesados"
            )

        except Exception as e:
            QMessageBox.warning(self, "Error", f"Error al actualizar estadísticas: {str(e)}")


    def _procesar_coleccion_completa(self):
        """Procesar toda la colección para generar embeddings."""
        if not self.batch_processor:
            QMessageBox.warning(self, "Error", "Sistema no inicializado")
            return

        # Confirmar procesamiento
        reply = QMessageBox.question(
            self, "Confirmar Procesamiento",
            "¿Está seguro de que desea procesar TODA la colección?\n"
            "Este proceso puede tomar mucho tiempo dependiendo del número de documentos.\n"
            "Se procesarán documentos sin embedding o sin descripción semántica.",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        )

        if reply != QMessageBox.Yes:
            return

        # Deshabilitar botones durante el procesamiento
        self.procesar_btn.setEnabled(False)
        self.actualizar_stats_btn.setEnabled(False)
        self.cancelar_btn.setEnabled(True)

        # Limpiar log y mostrar progreso
        self.procesamiento_log.clear()
        self.procesamiento_log.append("Iniciando procesamiento de la colección completa...")

        self.progreso_bar.setVisible(True)
        self.progreso_bar.setRange(0, 0)  # Indefinido
        self.progreso_label.setText("Procesando documentos...")

        # Resetear flag de cancelación
        self.cancelar_procesamiento_flag = False

        # Crear y ejecutar hilo de procesamiento
        max_docs = self.max_docs_spin.value() if self.max_docs_spin.value() != 0 else None
        self.procesamiento_thread = WorkerThread("procesar_coleccion", self.batch_processor, self.batch_size_spin.value(), max_docs, cancel_callback=self._verificar_cancelacion)
        self.procesamiento_thread.progreso_actualizado.connect(self._actualizar_progreso_procesamiento)
        self.procesamiento_thread.procesamiento_completado.connect(self._procesamiento_completado)
        self.procesamiento_thread.error_ocurrido.connect(self._mostrar_error_procesamiento)
        self.procesamiento_thread.start()

    def _cancelar_procesamiento(self):
        """Cancelar el procesamiento actual."""
        if not hasattr(self, 'procesamiento_thread') or not self.procesamiento_thread:
            QMessageBox.information(self, "Información", "No hay procesamiento en curso")
            return

        # Establecer flag de cancelación
        self.cancelar_procesamiento_flag = True

        # Actualizar interfaz
        self.progreso_label.setText("Cancelando procesamiento...")
        self.procesamiento_log.append("⚠️ Solicitud de cancelación enviada...")

        # El hilo se detendrá en el próximo punto de verificación
        QMessageBox.information(
            self, "Cancelación Solicitada",
            "Se ha solicitado la cancelación del procesamiento.\n"
            "El proceso se detendrá en el próximo punto de control."
        )

    def _cancelar_busqueda_imagenes(self):
        """Cancelar la búsqueda de imágenes actual."""
        if not hasattr(self, 'busqueda_thread') or not self.busqueda_thread:
            QMessageBox.information(self, "Información", "No hay búsqueda en curso")
            return

        # Establecer flag de cancelación
        self.cancelar_busqueda_flag = True

        # Actualizar interfaz
        self.busqueda_progress_label.setText("Cancelando búsqueda...")
        self.busqueda_log.append("⚠️ Solicitud de cancelación enviada...")

        # El hilo se detendrá en el próximo punto de verificación
        QMessageBox.information(
            self, "Cancelación Solicitada",
            "Se ha solicitado la cancelación de la búsqueda.\n"
            "El proceso se detendrá en el próximo punto de control."
        )

    def _verificar_cancelacion(self):
        """Verificar si se ha solicitado la cancelación del procesamiento."""
        resultado = self.cancelar_procesamiento_flag
        if resultado:
            print(f"🚫 CANCELACIÓN SOLICITADA - Flag de cancelación: {resultado}")
        return resultado

    def _verificar_cancelacion_busqueda(self):
        """Verificar si se ha solicitado la cancelación de la búsqueda de imágenes."""
        resultado = self.cancelar_busqueda_flag
        if resultado:
            print(f"🚫 CANCELACIÓN SOLICITADA - Flag de cancelación de búsqueda: {resultado}")
        return resultado


    def _actualizar_progreso_procesamiento(self, progreso: int, mensaje: str):
        """Actualizar progreso del procesamiento."""
        self.progreso_bar.setValue(progreso)
        self.progreso_label.setText(mensaje)
        self.procesamiento_log.append(f"Progreso: {progreso}% - {mensaje}")

    def _procesamiento_completado(self, resultado: dict):
        """Manejador para cuando termina el procesamiento."""
        # Rehabilitar botones
        self.procesar_btn.setEnabled(True)
        self.actualizar_stats_btn.setEnabled(True)
        self.cancelar_btn.setEnabled(False)

        # Ocultar progreso
        self.progreso_bar.setVisible(False)

        # Mostrar resultado
        if resultado:
            print(f"📊 RESULTADO RECIBIDO: {resultado}")
            # Verificar si fue cancelado
            if resultado.get('cancelado', False):
                print("✅ CANCELACIÓN DETECTADA EN RESULTADO")
                self.progreso_label.setText("Procesamiento cancelado")
                self.procesamiento_log.append("\n=== PROCESAMIENTO CANCELADO ===")
                QMessageBox.information(
                    self, "Procesamiento Cancelado",
                    f"Procesamiento cancelado por el usuario:\n"
                    f"• {resultado.get('total_exitosos', 0)} documentos procesados exitosamente\n"
                    f"• {resultado.get('total_errores', 0)} errores\n"
                    f"• {resultado.get('total_procesados', 0)} total procesados"
                )
            else:
                self.progreso_label.setText("Procesamiento completado")
                self.procesamiento_log.append("\n=== RESULTADO DEL PROCESAMIENTO ===")
                QMessageBox.information(
                    self, "Procesamiento Completado",
                    f"Procesamiento finalizado:\n"
                    f"• {resultado.get('total_exitosos', 0)} documentos procesados exitosamente\n"
                    f"• {resultado.get('total_errores', 0)} errores\n"
                    f"• {resultado.get('total_procesados', 0)} total procesados"
                )

            self.procesamiento_log.append(f"Total procesados: {resultado.get('total_procesados', 0)}")
            self.procesamiento_log.append(f"Total exitosos: {resultado.get('total_exitosos', 0)}")
            self.procesamiento_log.append(f"Total errores: {resultado.get('total_errores', 0)}")
            self.procesamiento_log.append(f"Mensaje: {resultado.get('mensaje', 'Sin mensaje')}")

            # Actualizar estadísticas
            self._actualizar_estadisticas_procesamiento()
        else:
            self.progreso_label.setText("Procesamiento completado")
            self.procesamiento_log.append("Procesamiento completado sin resultado detallado")

    def _mostrar_error_procesamiento(self, error_msg: str):
        """Mostrar mensaje de error de procesamiento."""
        QMessageBox.critical(self, "Error de Procesamiento", f"Error durante el procesamiento: {error_msg}")

        # Rehabilitar botones y ocultar progreso
        self.procesar_btn.setEnabled(True)
        self.actualizar_stats_btn.setEnabled(True)
        self.cancelar_btn.setEnabled(False)
        self.progreso_bar.setVisible(False)
        self.progreso_label.setText("Error en procesamiento")

        # Registrar el error en el log
        self.procesamiento_log.append(f"❌ Error durante el procesamiento: {error_msg}")
        self.procesamiento_log.append("=== PROCESAMIENTO INTERRUMPIDO POR ERROR ===")


    def _actualizar_sugerencias(self, texto: str):
        """Actualizar sugerencias de búsqueda."""
        if len(texto) < 3:
            return

        try:
            sugerencias = self.buscador.obtener_sugerencias(texto, 5)
            # Aquí podrías implementar mostrar sugerencias en un dropdown
        except:
            pass

    def _busqueda_finalizada(self):
        """Manejador para cuando termina la búsqueda."""
        self.progress_bar.setVisible(False)
        self.buscar_btn.setEnabled(True)

    def _mostrar_error(self, error_msg: str):
        """Mostrar mensaje de error."""
        QMessageBox.critical(self, "Error", f"Error durante la búsqueda: {error_msg}")
        self._busqueda_finalizada()

    def _actualizar_estado_deteccion(self):
        """Actualizar el estado del sistema de detección de objetos."""
        try:
            # Verificar si el detector está inicializado
            detector_inicializado = hasattr(self, 'object_detector') and self.object_detector is not None

            if detector_inicializado:
                self.deteccion_status_label.setText("Inicializado")
                self.deteccion_status_label.setStyleSheet("color: green;")

                # Obtener número de documentos pendientes
                documentos_pendientes = self.db_manager.collection.count_documents({
                    "$or": [
                        {"objetos": {"$exists": False}},
                        {"objetos": {"$size": 0}},
                        {"objeto_procesado": False}
                    ]
                })

                self.deteccion_documentos_pendientes_label.setText(str(documentos_pendientes))
                self.deteccion_procesando_label.setText("No")
                self.deteccion_ultima_verificacion_label.setText(datetime.now().strftime("%H:%M:%S"))

                self.deteccion_log.append(f"✓ Estado actualizado: {documentos_pendientes} imágenes pendientes")

                # Mostrar estadísticas de la base de datos
                try:
                    stats = self.db_manager.obtener_estadisticas()
                    self.deteccion_log.append(
                        f"📊 Base de datos: {stats.get('documentos_procesados', 0)}/{stats.get('total_documentos', 0)} procesados"
                    )
                except Exception as e:
                    self.deteccion_log.append(f"⚠ Error al obtener estadísticas: {str(e)}")
            else:
                self.deteccion_status_label.setText("No inicializado")
                self.deteccion_status_label.setStyleSheet("color: red;")
                self.deteccion_documentos_pendientes_label.setText("0")
                self.deteccion_procesando_label.setText("No")
                self.deteccion_ultima_verificacion_label.setText("Nunca")
                self.deteccion_log.append("❌ Sistema de detección no inicializado")

        except Exception as e:
            self.deteccion_log.append(f"❌ Error al actualizar estado: {str(e)}")
            QMessageBox.warning(self, "Error", f"Error al actualizar estado: {str(e)}")

    def _inicializar_sistema_deteccion_manual(self):
        """Inicializar el sistema de detección para uso manual."""
        try:
            from src.object_detector import ObjectDetector
            self.object_detector = ObjectDetector()
            self.deteccion_log.append("✓ Detector de objetos inicializado correctamente")
            return True
        except Exception as e:
            self.deteccion_log.append(f"❌ Error al inicializar detector de objetos: {str(e)}")
            return False

    def _procesar_objetos_manual(self):
        """Procesar objetos manualmente."""
        try:
            self.deteccion_log.append("🔄 Iniciando procesamiento manual de objetos...")

            # Inicializar detector si no existe
            if not hasattr(self, 'object_detector') or not self.object_detector:
                if not self._inicializar_sistema_deteccion_manual():
                    QMessageBox.warning(self, "Error", "No se pudo inicializar el sistema de detección")
                    return

            # Obtener el procesador de objetos
            from src.object_detector import BackgroundObjectProcessor
            processor = BackgroundObjectProcessor(self.db_manager, self.object_detector)

            # Obtener número total de documentos pendientes
            documentos_pendientes = self.db_manager.collection.count_documents({
                "$or": [
                    {"objetos": {"$exists": False}},
                    {"objetos": {"$size": 0}},
                    {"objeto_procesado": False}
                ]
            })

            if documentos_pendientes == 0:
                QMessageBox.information(self, "Sin Procesamiento", "No hay imágenes pendientes de procesar")
                return

            # Procesar TODA la colección
            self.deteccion_log.append(f"📊 Procesando {documentos_pendientes} imágenes pendientes...")
            resultado = processor.procesar_imagenes_sin_objetos(batch_size=documentos_pendientes)

            # Mostrar resultados
            self.deteccion_log.append("=== RESULTADO DEL PROCESAMIENTO ===")
            self.deteccion_log.append(f"✓ Procesadas: {resultado.get('procesadas', 0)}")
            self.deteccion_log.append(f"⚠ Errores: {resultado.get('errores', 0)}")
            self.deteccion_log.append(f"📁 Sin archivo: {resultado.get('sin_archivo', 0)}")

            if resultado.get('procesadas', 0) > 0:
                QMessageBox.information(
                    self, "Procesamiento Completado",
                    f"Procesamiento manual completado:\n"
                    f"• {resultado.get('procesadas', 0)} imágenes procesadas\n"
                    f"• {resultado.get('errores', 0)} errores\n"
                    f"• {resultado.get('sin_archivo', 0)} archivos no encontrados"
                )
            else:
                QMessageBox.information(self, "Sin Procesamiento", "No hay imágenes pendientes de procesar")

            # Actualizar estado
            self._actualizar_estado_deteccion()

        except Exception as e:
            self.deteccion_log.append(f"❌ Error en procesamiento manual: {str(e)}")
            QMessageBox.warning(self, "Error", f"Error en procesamiento manual: {str(e)}")

    def _detener_procesamiento(self):
        """Detener el procesamiento en segundo plano."""
        if not hasattr(self, 'system_initializer') or not self.system_initializer:
            QMessageBox.warning(self, "Error", "Sistema de detección no inicializado")
            return

        try:
            self.system_initializer.stop_background_processing()
            self.deteccion_log.append("⏹️ Procesamiento en segundo plano detenido")
            self._actualizar_estado_deteccion()
            QMessageBox.information(self, "Procesamiento Detenido", "Procesamiento en segundo plano detenido correctamente")
        except Exception as e:
            self.deteccion_log.append(f"❌ Error al detener procesamiento: {str(e)}")
            QMessageBox.warning(self, "Error", f"Error al detener procesamiento: {str(e)}")

    def _crear_pestana_buscar_imagenes(self) -> QWidget:
        """Crear pestaña de búsqueda de imágenes no procesadas."""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        # Información del sistema
        grupo_info = QGroupBox("Sistema de Búsqueda de Imágenes")
        layout_info = QVBoxLayout(grupo_info)

        info_text = QLabel(
            "🔍 <b>BUSCAR IMÁGENES NO PROCESADAS</b>\n\n"
            "Este sistema permite buscar imágenes en un directorio específico y procesarlas "
            "para extraer metadatos y almacenarlos en la base de datos MongoDB.\n\n"
            "Características:\n"
            "• Búsqueda recursiva en directorios\n"
            "• Soporte para múltiples formatos de imagen\n"
            "• Extracción automática de metadatos EXIF\n"
            "• Cálculo de hash SHA512 para evitar duplicados\n"
            "• Procesamiento de coordenadas GPS para geolocalización\n"
            "• Inserción automática en MongoDB (colección 'imagenes_2')\n"
            "• Verificación de imágenes ya procesadas"
        )
        info_text.setWordWrap(True)
        layout_info.addWidget(info_text)

        layout.addWidget(grupo_info)

        # Configuración de búsqueda
        grupo_config = QGroupBox("Configuración de Búsqueda")
        layout_config = QFormLayout(grupo_config)

        # Campo de directorio
        self.directorio_input = QLineEdit()
        self.directorio_input.setPlaceholderText("Selecciona un directorio para buscar imágenes...")
        self.directorio_input.setStyleSheet("""
            QLineEdit {
                background: #0F0F0F;
                color: #FFFFFF;
                font-size: 16px;
                padding: 15px 18px;
                border: 3px solid #5A6578;
                border-radius: 15px;
                selection-background-color: #5A6578;
                selection-color: #FFFFFF;
            }
            QLineEdit:focus {
                border: 3px solid #8190A6;
                background: #0F0F0F;
            }
            QLineEdit:hover {
                border: 3px solid #8190A6;
            }
        """)
        layout_config.addRow("Directorio:", self.directorio_input)

        # Botón para seleccionar directorio
        self.seleccionar_directorio_btn = QPushButton("📁 Seleccionar Directorio")
        self.seleccionar_directorio_btn.clicked.connect(self._seleccionar_directorio)
        self.seleccionar_directorio_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1: 0, y1: 0, x2: 1, y2: 1,
                              stop: 0 #FF9800, stop: 1 #F57C00);
                color: #FFFFFF;
                font-weight: bold;
                font-size: 14px;
                padding: 12px 24px;
                border-radius: 20px;
                border: 3px solid #FF9800;
            }
            QPushButton:hover {
                background: qlineargradient(x1: 0, y1: 0, x2: 1, y2: 1,
                              stop: 0 #FF9800, stop: 1 #E65100);
                border: 3px solid #FFB74D;
            }
            QPushButton:pressed {
                background: qlineargradient(x1: 0, y1: 0, x2: 1, y2: 1,
                              stop: 0 #F57C00, stop: 1 #BF360C);
                border: 3px solid #F57C00;
            }
        """)
        layout_config.addRow(self.seleccionar_directorio_btn)

        # Opciones de búsqueda
        opciones_layout = QHBoxLayout()

        self.busqueda_recursiva_checkbox = QCheckBox("Búsqueda recursiva")
        self.busqueda_recursiva_checkbox.setChecked(True)
        self.busqueda_recursiva_checkbox.setToolTip("Buscar imágenes en subdirectorios")
        opciones_layout.addWidget(self.busqueda_recursiva_checkbox)

        self.solo_nuevas_checkbox = QCheckBox("Solo imágenes nuevas")
        self.solo_nuevas_checkbox.setChecked(True)
        self.solo_nuevas_checkbox.setToolTip("Solo procesar imágenes que no estén en la base de datos")
        opciones_layout.addWidget(self.solo_nuevas_checkbox)

        layout_config.addRow("Opciones:", opciones_layout)

        layout.addWidget(grupo_config)

        # Estadísticas de búsqueda
        grupo_stats = QGroupBox("Estadísticas de Búsqueda")
        layout_stats = QFormLayout(grupo_stats)

        self.imagenes_encontradas_label = QLabel("0")
        layout_stats.addRow("Imágenes encontradas:", self.imagenes_encontradas_label)

        self.imagenes_procesadas_label = QLabel("0")
        layout_stats.addRow("Imágenes procesadas:", self.imagenes_procesadas_label)

        self.imagenes_omitidas_label = QLabel("0")
        layout_stats.addRow("Imágenes omitidas:", self.imagenes_omitidas_label)

        self.imagenes_errores_label = QLabel("0")
        layout_stats.addRow("Errores:", self.imagenes_errores_label)

        layout.addWidget(grupo_stats)

        # Botones de acción
        botones_layout = QHBoxLayout()

        self.buscar_imagenes_btn = QPushButton("🔍 Buscar Imágenes")
        self.buscar_imagenes_btn.clicked.connect(self._buscar_imagenes)
        self.buscar_imagenes_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1: 0, y1: 0, x2: 1, y2: 1,
                              stop: 0 #4A5568, stop: 1 #2D3748);
                color: #FFFFFF;
                font-weight: bold;
                font-size: 14px;
                padding: 12px 24px;
                border-radius: 20px;
                border: 3px solid #4A5568;
            }
            QPushButton:hover {
                background: qlineargradient(x1: 0, y1: 0, x2: 1, y2: 1,
                              stop: 0 #718096, stop: 1 #4A5568);
                border: 3px solid #718096;
            }
            QPushButton:pressed {
                background: qlineargradient(x1: 0, y1: 0, x2: 1, y2: 1,
                              stop: 0 #2D3748, stop: 1 #1A202C);
                border: 3px solid #2D3748;
            }
        """)
        botones_layout.addWidget(self.buscar_imagenes_btn)

        self.procesar_imagenes_btn = QPushButton("⚡ Procesar Imágenes")
        self.procesar_imagenes_btn.clicked.connect(self._procesar_imagenes_encontradas)
        self.procesar_imagenes_btn.setEnabled(False)
        self.procesar_imagenes_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1: 0, y1: 0, x2: 1, y2: 1,
                              stop: 0 #4A5568, stop: 1 #2D3748);
                color: #FFFFFF;
                font-weight: bold;
                font-size: 14px;
                padding: 12px 24px;
                border-radius: 20px;
                border: 3px solid #4A5568;
            }
            QPushButton:hover {
                background: qlineargradient(x1: 0, y1: 0, x2: 1, y2: 1,
                              stop: 0 #718096, stop: 1 #4A5568);
                border: 3px solid #718096;
            }
            QPushButton:pressed {
                background: qlineargradient(x1: 0, y1: 0, x2: 1, y2: 1,
                              stop: 0 #2D3748, stop: 1 #1A202C);
                border: 3px solid #2D3748;
            }
            QPushButton:disabled {
                background: #1A1A1A;
                color: #FFFFFF;
                border: 3px solid #4A5568;
            }
        """)
        botones_layout.addWidget(self.procesar_imagenes_btn)

        self.limpiar_resultados_btn = QPushButton("🗑️ Limpiar Resultados")
        self.limpiar_resultados_btn.clicked.connect(self._limpiar_resultados_busqueda)
        self.limpiar_resultados_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1: 0, y1: 0, x2: 1, y2: 1,
                              stop: 0 #718096, stop: 1 #4A5568);
                color: #FFFFFF;
                font-weight: bold;
                font-size: 14px;
                padding: 12px 24px;
                border-radius: 20px;
                border: 3px solid #718096;
            }
            QPushButton:hover {
                background: qlineargradient(x1: 0, y1: 0, x2: 1, y2: 1,
                              stop: 0 #4A5568, stop: 1 #2D3748);
                border: 3px solid #4A5568;
            }
            QPushButton:pressed {
                background: qlineargradient(x1: 0, y1: 0, x2: 1, y2: 1,
                              stop: 0 #2D3748, stop: 1 #1A202C);
                border: 3px solid #2D3748;
            }
        """)
        botones_layout.addWidget(self.limpiar_resultados_btn)

        self.cancelar_busqueda_btn = QPushButton("⏹️ Cancelar Búsqueda")
        self.cancelar_busqueda_btn.clicked.connect(self._cancelar_busqueda_imagenes)
        self.cancelar_busqueda_btn.setEnabled(False)  # Inicialmente deshabilitado
        self.cancelar_busqueda_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1: 0, y1: 0, x2: 1, y2: 1,
                              stop: 0 #E53E3E, stop: 1 #C53030);
                color: #FFFFFF;
                font-weight: bold;
                font-size: 14px;
                padding: 12px 24px;
                border-radius: 20px;
                border: 3px solid #E53E3E;
            }
            QPushButton:hover {
                background: qlineargradient(x1: 0, y1: 0, x2: 1, y2: 1,
                              stop: 0 #C53030, stop: 1 #9C1A1A);
                border: 3px solid #C53030;
            }
            QPushButton:pressed {
                background: qlineargradient(x1: 0, y1: 0, x2: 1, y2: 1,
                              stop: 0 #9C1A1A, stop: 1 #742A2A);
                border: 3px solid #9C1A1A;
            }
            QPushButton:disabled {
                background: #1A1A1A;
                color: #FFFFFF;
                border: 3px solid #4A5568;
            }
        """)
        botones_layout.addWidget(self.cancelar_busqueda_btn)

        layout.addLayout(botones_layout)

        # Área de progreso
        grupo_progreso = QGroupBox("Progreso de la Operación")
        layout_progreso = QVBoxLayout(grupo_progreso)

        self.busqueda_progress_bar = QProgressBar()
        self.busqueda_progress_bar.setVisible(False)
        self.busqueda_progress_bar.setStyleSheet("""
            QProgressBar {
                border: 2px solid #4A5568;
                border-radius: 10px;
                background: #1A1A1A;
                color: #FFFFFF;
                font-size: 12px;
                font-weight: bold;
                text-align: center;
            }
            QProgressBar::chunk {
                background: qlineargradient(x1: 0, y1: 0, x2: 1, y2: 1,
                              stop: 0 #718096, stop: 1 #4A5568);
                border-radius: 8px;
            }
        """)
        layout_progreso.addWidget(self.busqueda_progress_bar)

        self.busqueda_progress_label = QLabel("Listo para buscar imágenes")
        self.busqueda_progress_label.setAlignment(Qt.AlignCenter)
        layout_progreso.addWidget(self.busqueda_progress_label)

        layout.addWidget(grupo_progreso)

        # Área de log
        grupo_log = QGroupBox("Log de Búsqueda y Procesamiento")
        layout_log = QVBoxLayout(grupo_log)

        self.busqueda_log = QTextEdit()
        self.busqueda_log.setMaximumHeight(200)
        self.busqueda_log.setPlaceholderText("Los mensajes de búsqueda y procesamiento aparecerán aquí...")
        self.busqueda_log.setStyleSheet("""
            QTextEdit {
                background: #0F0F0F;
                color: #FFFFFF;
                font-size: 13px;
                font-family: 'Consolas', 'Monaco', 'Courier New', monospace;
                border: 3px solid #5A6578;
                border-radius: 15px;
                padding: 12px;
                selection-background-color: #5A6578;
                selection-color: #FFFFFF;
            }
            QTextEdit:focus {
                border: 3px solid #8190A6;
                background: #0F0F0F;
            }
            QTextEdit:hover {
                border: 3px solid #8190A6;
            }
        """)
        layout_log.addWidget(self.busqueda_log)

        layout.addWidget(grupo_log)

        return widget

    def _seleccionar_directorio(self):
        """Abrir diálogo para seleccionar directorio."""
        from PySide6.QtWidgets import QFileDialog

        directorio = QFileDialog.getExistingDirectory(
            self,
            "Seleccionar directorio para buscar imágenes",
            self.directorio_input.text() or "."
        )

        if directorio:
            self.directorio_input.setText(directorio)
            self.busqueda_log.append(f"✓ Directorio seleccionado: {directorio}")

    def _buscar_imagenes(self):
        """Buscar imágenes en el directorio seleccionado."""
        try:
            directorio = self.directorio_input.text().strip()

            if not directorio:
                QMessageBox.warning(self, "Error", "Seleccione un directorio para buscar imágenes")
                return

            if not os.path.exists(directorio):
                QMessageBox.warning(self, "Error", f"El directorio no existe: {directorio}")
                return

            # Mostrar progreso
            self.busqueda_progress_bar.setVisible(True)
            self.busqueda_progress_bar.setRange(0, 0)  # Indefinido
            self.busqueda_progress_label.setText("Buscando imágenes...")
            self.busqueda_log.clear()
            self.busqueda_log.append("🔍 Iniciando búsqueda de imágenes...")

            # Deshabilitar botones
            self.buscar_imagenes_btn.setEnabled(False)
            self.procesar_imagenes_btn.setEnabled(False)
            self.cancelar_busqueda_btn.setEnabled(True)

            # Resetear flag de cancelación
            self.cancelar_busqueda_flag = False

            # Crear hilo de trabajo para la búsqueda
            self.busqueda_thread = WorkerThread("buscar_imagenes", directorio, self.busqueda_recursiva_checkbox.isChecked(), self.solo_nuevas_checkbox.isChecked(), self.db_manager, cancel_callback=self._verificar_cancelacion_busqueda)
            self.busqueda_thread.progreso_actualizado.connect(self._actualizar_progreso_busqueda)
            self.busqueda_thread.procesamiento_completado.connect(self._busqueda_completada)
            self.busqueda_thread.error_ocurrido.connect(self._error_busqueda)
            self.busqueda_thread.start()

        except Exception as e:
            self.busqueda_log.append(f"❌ Error al iniciar búsqueda: {str(e)}")
            QMessageBox.critical(self, "Error", f"Error al iniciar búsqueda: {str(e)}")

    def _procesar_imagenes_encontradas(self):
        """Procesar las imágenes encontradas."""
        try:
            if not hasattr(self, 'imagenes_encontradas') or not self.imagenes_encontradas:
                QMessageBox.warning(self, "Error", "No hay imágenes para procesar")
                return

            # Mostrar progreso
            self.busqueda_progress_bar.setVisible(True)
            self.busqueda_progress_bar.setRange(0, 0)  # Indefinido
            self.busqueda_progress_label.setText("Procesando imágenes...")
            self.busqueda_log.append("⚡ Iniciando procesamiento de imágenes...")

            # Deshabilitar botones
            self.buscar_imagenes_btn.setEnabled(False)
            self.procesar_imagenes_btn.setEnabled(False)

            # Crear hilo de trabajo para el procesamiento
            self.procesamiento_thread = WorkerThread("procesar_imagenes", self.imagenes_encontradas, self.db_manager)
            self.procesamiento_thread.progreso_actualizado.connect(self._actualizar_progreso_procesamiento_imagenes)
            self.procesamiento_thread.procesamiento_completado.connect(self._procesamiento_imagenes_completado)
            self.procesamiento_thread.error_ocurrido.connect(self._error_procesamiento_imagenes)
            self.procesamiento_thread.start()

        except Exception as e:
            self.busqueda_log.append(f"❌ Error al iniciar procesamiento: {str(e)}")
            QMessageBox.critical(self, "Error", f"Error al iniciar procesamiento: {str(e)}")

    def _limpiar_resultados_busqueda(self):
        """Limpiar resultados de búsqueda."""
        self.directorio_input.clear()
        self.imagenes_encontradas_label.setText("0")
        self.imagenes_procesadas_label.setText("0")
        self.imagenes_omitidas_label.setText("0")
        self.imagenes_errores_label.setText("0")
        self.busqueda_log.clear()

        # Deshabilitar botones
        self.procesar_imagenes_btn.setEnabled(False)
        self.cancelar_busqueda_btn.setEnabled(False)

        # Limpiar variables de instancia
        if hasattr(self, 'imagenes_encontradas'):
            delattr(self, 'imagenes_encontradas')

    def _actualizar_progreso_busqueda(self, progreso: int, mensaje: str):
        """Actualizar progreso de la búsqueda."""
        self.busqueda_progress_bar.setValue(progreso)
        self.busqueda_progress_label.setText(mensaje)
        self.busqueda_log.append(f"Progreso: {progreso}% - {mensaje}")

        # Si la búsqueda está completada o cancelada, deshabilitar botón de cancelación
        if progreso >= 100 or "cancel" in mensaje.lower():
            self.cancelar_busqueda_btn.setEnabled(False)

    def _busqueda_completada(self, resultado: dict):
        """Manejador para cuando termina la búsqueda."""
        # Rehabilitar botones
        self.buscar_imagenes_btn.setEnabled(True)
        self.cancelar_busqueda_btn.setEnabled(False)

        # Ocultar progreso
        self.busqueda_progress_bar.setVisible(False)

        if resultado:
            # Verificar si fue cancelado
            if resultado.get('cancelado', False):
                print("✅ CANCELACIÓN DETECTADA EN RESULTADO - Búsqueda de Imágenes")
                self.busqueda_progress_label.setText("Búsqueda cancelada")
                self.busqueda_log.append("\n=== BÚSQUEDA CANCELADA ===")
                QMessageBox.information(
                    self, "Búsqueda Cancelada",
                    f"Búsqueda cancelada por el usuario:\n"
                    f"• {resultado.get('total_encontradas', 0)} imágenes encontradas hasta el momento\n"
                    f"• {resultado.get('ya_procesadas', 0)} imágenes ya procesadas\n"
                    f"• {resultado.get('errores', 0)} errores"
                )
            else:
                self.busqueda_progress_label.setText("Búsqueda completada")
                self.busqueda_log.append("\n=== BÚSQUEDA COMPLETADA ===")

                # Actualizar estadísticas
                self.imagenes_encontradas_label.setText(str(resultado.get('total_encontradas', 0)))
                self.imagenes_procesadas_label.setText(str(resultado.get('ya_procesadas', 0)))
                self.imagenes_omitidas_label.setText(str(resultado.get('omitidas_por_ruta', 0) + resultado.get('omitidas_por_hash', 0)))
                self.imagenes_errores_label.setText(str(resultado.get('errores', 0)))

                # Guardar lista de imágenes encontradas
                self.imagenes_encontradas = resultado.get('imagenes', [])

                # Habilitar botón de procesamiento si hay imágenes nuevas
                if self.imagenes_encontradas:
                    self.procesar_imagenes_btn.setEnabled(True)
                    self.busqueda_log.append(f"✓ {len(self.imagenes_encontradas)} imágenes listas para procesar")
                else:
                    if resultado.get('ya_procesadas', 0) > 0:
                        self.busqueda_log.append(f"ℹ️ Todas las {resultado.get('total_encontradas', 0)} imágenes encontradas ya están procesadas")
                        self.busqueda_log.append(f"   • {resultado.get('omitidas_por_ruta', 0)} imágenes con la misma ruta")
                        self.busqueda_log.append(f"   • {resultado.get('omitidas_por_hash', 0)} imágenes con el mismo hash")
                    else:
                        self.busqueda_log.append("ℹ️ No se encontraron imágenes para procesar")

                # Mostrar resumen detallado
                self.busqueda_log.append(f"📊 Resumen detallado:")
                self.busqueda_log.append(f"   • Total encontradas: {resultado.get('total_encontradas', 0)}")
                self.busqueda_log.append(f"   • Ya procesadas: {resultado.get('ya_procesadas', 0)}")
                self.busqueda_log.append(f"     └─ Por ruta exacta: {resultado.get('omitidas_por_ruta', 0)}")
                self.busqueda_log.append(f"     └─ Por hash coincidente: {resultado.get('omitidas_por_hash', 0)}")
                self.busqueda_log.append(f"   • Errores: {resultado.get('errores', 0)}")
                self.busqueda_log.append(f"   • Imágenes nuevas para procesar: {len(self.imagenes_encontradas)}")

        else:
            self.busqueda_progress_label.setText("Búsqueda completada")
            self.busqueda_log.append("Búsqueda completada sin resultado detallado")

    def _actualizar_progreso_procesamiento_imagenes(self, progreso: int, mensaje: str):
        """Actualizar progreso del procesamiento de imágenes."""
        self.busqueda_progress_bar.setValue(progreso)
        self.busqueda_progress_label.setText(mensaje)
        self.busqueda_log.append(f"Progreso: {progreso}% - {mensaje}")

    def _procesamiento_imagenes_completado(self, resultado: dict):
        """Manejador para cuando termina el procesamiento de imágenes."""
        # Rehabilitar botones
        self.buscar_imagenes_btn.setEnabled(True)
        self.procesar_imagenes_btn.setEnabled(True)

        # Ocultar progreso
        self.busqueda_progress_bar.setVisible(False)

        if resultado:
            self.busqueda_progress_label.setText("Procesamiento completado")
            self.busqueda_log.append("\n=== PROCESAMIENTO COMPLETADO ===")

            # Actualizar estadísticas
            self.imagenes_procesadas_label.setText(str(resultado.get('procesadas', 0)))
            self.imagenes_errores_label.setText(str(resultado.get('errores', 0)))

            # Mostrar resultados
            self.busqueda_log.append(f"✓ Procesadas: {resultado.get('procesadas', 0)}")
            self.busqueda_log.append(f"⚠ Errores: {resultado.get('errores', 0)}")
            self.busqueda_log.append(f"📝 Insertadas en BD: {resultado.get('insertadas', 0)}")

            if resultado.get('procesadas', 0) > 0:
                QMessageBox.information(
                    self, "Procesamiento Completado",
                    f"Procesamiento completado exitosamente:\n"
                    f"• {resultado.get('procesadas', 0)} imágenes procesadas\n"
                    f"• {resultado.get('errores', 0)} errores\n"
                    f"• {resultado.get('insertadas', 0)} imágenes insertadas en la base de datos"
                )
            else:
                QMessageBox.information(self, "Sin Procesamiento", "No se procesaron imágenes nuevas")

        else:
            self.busqueda_progress_label.setText("Procesamiento completado")
            self.busqueda_log.append("Procesamiento completado sin resultado detallado")

    def _error_busqueda(self, error_msg: str):
        """Mostrar mensaje de error de búsqueda."""
        QMessageBox.critical(self, "Error de Búsqueda", f"Error durante la búsqueda: {error_msg}")

        # Rehabilitar botones y ocultar progreso
        self.buscar_imagenes_btn.setEnabled(True)
        self.procesar_imagenes_btn.setEnabled(False)
        self.cancelar_busqueda_btn.setEnabled(False)
        self.busqueda_progress_bar.setVisible(False)
        self.busqueda_progress_label.setText("Error en búsqueda")

        self.busqueda_log.append(f"❌ Error durante la búsqueda: {error_msg}")
        self.busqueda_log.append("=== BÚSQUEDA INTERRUMPIDA POR ERROR ===")

    def _error_procesamiento_imagenes(self, error_msg: str):
        """Mostrar mensaje de error de procesamiento."""
        QMessageBox.critical(self, "Error de Procesamiento", f"Error durante el procesamiento: {error_msg}")

        # Rehabilitar botones y ocultar progreso
        self.buscar_imagenes_btn.setEnabled(True)
        self.procesar_imagenes_btn.setEnabled(True)
        self.busqueda_progress_bar.setVisible(False)
        self.busqueda_progress_label.setText("Error en procesamiento")

        self.busqueda_log.append(f"❌ Error durante el procesamiento: {error_msg}")
        self.busqueda_log.append("=== PROCESAMIENTO INTERRUMPIDO POR ERROR ===")

    def closeEvent(self, event):
        """Manejador para cuando se cierra la ventana."""
        # Detener procesamiento en segundo plano
        if hasattr(self, 'system_initializer') and self.system_initializer:
            self.system_initializer.stop_background_processing()

        # Cerrar conexiones
        if hasattr(self, 'db_manager') and self.db_manager:
            self.db_manager.cerrar_conexion()
        if hasattr(self, 'qdrant_manager') and self.qdrant_manager:
            self.qdrant_manager.cerrar_conexion()
        event.accept()