# Guía de Configuración - Entorno Conda

Esta guía explica cómo configurar el entorno de desarrollo para el proyecto **Búsqueda Semántica V2** usando Conda.

## 📋 Requisitos Previos

- **Miniconda** o **Anaconda** instalado
- **Git** para clonar el repositorio
- Conexión a internet para descargar dependencias

## 🚀 Configuración Rápida

### En Linux/Mac:
```bash
./setup_conda_linux.sh
```

### En Windows:
```cmd
setup_conda_windows.bat
```

## 📝 ¿Qué hace el script?

1. **Verifica conda**: Asegura que conda esté instalado
2. **Crea entorno**: Crea un entorno aislado llamado `busqueda_semantica_v2`
3. **Instala Python**: Configura Python 3.11
4. **Instala dependencias**: Instala todas las librerías necesarias:
   - **IA/ML**: PyTorch, Transformers, Sentence Transformers
   - **Bases de datos**: MongoDB, Qdrant
   - **Interfaz**: PySide6 (Qt para Python)
   - **Procesamiento**: Pillow, OpenCV, etc.
   - **Lenguaje**: LangChain, Ollama
5. **Verifica instalación**: Comprueba que todo funcione correctamente

## 🔧 Activación Manual del Entorno

### Linux/Mac:
```bash
conda activate busqueda_semantica_v2
```

### Windows:
```cmd
conda activate busqueda_semantica_v2
```

## 🛠️ Uso en VS Code

1. Presiona `Ctrl+Shift+P` (o `Cmd+Shift+P` en Mac)
2. Selecciona **"Python: Select Interpreter"**
3. Elige el intérprete del entorno `busqueda_semantica_v2`

## 📦 Dependencias Incluidas

### Framework de IA
- **LangChain**: Framework para aplicaciones LLM
- **PyTorch**: Deep Learning
- **Transformers**: Modelos de lenguaje
- **Sentence Transformers**: Embeddings de texto

### Bases de Datos
- **MongoDB**: Base de datos NoSQL
- **Qdrant**: Base de datos vectorial

### Interfaz Gráfica
- **PySide6**: Qt para Python

### Procesamiento de Imágenes
- **Pillow**: Manipulación de imágenes
- **timm**: Modelos de visión por computadora

### Utilidades
- **Requests**: HTTP requests
- **python-dotenv**: Variables de entorno
- **tqdm**: Barras de progreso

## ⚠️ Notas Importantes

- **CUDA**: Si tienes GPU NVIDIA, PyTorch se instalará con soporte CUDA
- **Memoria**: Asegúrate de tener al menos 8GB de RAM disponible
- **Espacio**: Necesitarás aproximadamente 4-6GB de espacio libre
- **Tiempo**: La instalación puede tomar 10-20 minutos dependiendo de tu conexión

## 🔍 Solución de Problemas

### Error: "conda no está instalado"
- Descarga e instala Miniconda desde: https://docs.conda.io/en/latest/miniconda.html
- Reinicia tu terminal después de la instalación

### Error: "No hay suficiente espacio"
- Libera espacio en disco
- Considera usar una instalación mínima de PyTorch

### Error: "Falla la instalación de PyTorch"
- Verifica tu conexión a internet
- Intenta instalar manualmente: `pip install torch torchvision torchaudio`

## 📞 Soporte

Si encuentras problemas:
1. Revisa los logs de instalación
2. Verifica que todas las dependencias se instalaron correctamente
3. Consulta la documentación oficial de cada librería

---

**¡Listo!** Una vez completada la instalación, puedes ejecutar el proyecto con:

```bash
python main.py