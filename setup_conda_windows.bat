@echo off
REM ==========================================
REM SETUP CONDA - BÚSQUEDA SEMÁNTICA V2
REM ==========================================
REM Script para configurar entorno conda en Windows
REM Fecha: 2025-09-26
REM ==========================================

echo ==========================================
echo BÚSQUEDA SEMÁNTICA V2 - SETUP CONDA (Windows)
echo ==========================================
echo.

REM ==========================================
REM VERIFICACIÓN DE CONDA
REM ==========================================
echo Verificando instalación de conda...
where conda >nul 2>nul
if %errorlevel% neq 0 (
    echo ❌ Error: conda no está instalado.
    echo Por favor, instale Miniconda o Anaconda desde:
    echo https://docs.conda.io/en/latest/miniconda.html
    pause
    exit /b 1
)

echo ✅ conda está instalado: 
conda --version

REM ==========================================
REM CREACIÓN DEL ENTORNO
REM ==========================================
set ENV_NAME=busqueda_semantica_v2
set PYTHON_VERSION=3.11

echo.
echo Creando entorno conda: %ENV_NAME%
echo Versión de Python: %PYTHON_VERSION%

REM Crear el entorno con Python 3.11
conda create -n %ENV_NAME% python=%PYTHON_VERSION% -y

if %errorlevel% neq 0 (
    echo ❌ Error al crear el entorno conda
    pause
    exit /b 1
)

echo ✅ Entorno '%ENV_NAME%' creado exitosamente

REM ==========================================
REM ACTIVACIÓN DEL ENTORNO
REM ==========================================
echo.
echo Activando entorno: %ENV_NAME%
call conda activate %ENV_NAME%

REM Verificar activación
echo ✅ Entorno activado: 
python --version

REM ==========================================
REM INSTALACIÓN DE DEPENDENCIAS
REM ==========================================
echo.
echo Instalando dependencias desde requirements.txt...

REM Instalar PyTorch con soporte CUDA si está disponible
echo Instalando PyTorch...
python -c "import torch; print('CUDA available:', torch.cuda.is_available())" >nul 2>nul
if %errorlevel% equ 0 (
    echo CUDA detectado, instalando PyTorch con CUDA...
    pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118
) else (
    echo Instalando PyTorch CPU...
    pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cpu
)

REM Instalar el resto de dependencias
echo Instalando dependencias principales...
pip install -r requirements.txt

if %errorlevel% neq 0 (
    echo ❌ Error al instalar dependencias
    pause
    exit /b 1
)

echo ✅ Dependencias instaladas exitosamente

REM ==========================================
REM INSTALACIÓN DE DEPENDENCIAS OPCIONALES
REM ==========================================
echo.
echo Instalando dependencias opcionales...

REM Instalar jupyter para desarrollo
pip install jupyter notebook ipykernel

REM ==========================================
REM VERIFICACIÓN DE INSTALACIÓN
REM ==========================================
echo.
echo Verificando instalación de librerías críticas...

python -c "
import sys
print(f'Python version: {sys.version}')

# Verificar librerías críticas
critical_libs = [
    'torch', 'transformers', 'sentence_transformers',
    'langchain', 'pymongo', 'qdrant_client',
    'PySide6', 'PIL', 'numpy'
]

for lib in critical_libs:
    try:
        __import__(lib)
        print(f'✅ {lib}')
    except ImportError as e:
        print(f'❌ {lib}: {e}')

print('\n🎉 ¡Instalación completada exitosamente!')
print(f'Para activar el entorno en futuras sesiones:')
print(f'conda activate {ENV_NAME}')
"

echo.
echo ==========================================
echo INSTALACIÓN COMPLETADA
echo ==========================================
echo.
echo El entorno conda '%ENV_NAME%' ha sido configurado exitosamente.
echo.
echo Para usar el entorno en futuras sesiones de terminal:
echo conda activate %ENV_NAME%
echo.
echo Para usar el entorno en VS Code:
echo 1. Presione Ctrl+Shift+P
echo 2. Seleccione "Python: Select Interpreter"
echo 3. Elija el intérprete del entorno %ENV_NAME%
echo.
pause