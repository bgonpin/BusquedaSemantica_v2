#!/bin/bash

# ==========================================
# SETUP CONDA - BÚSQUEDA SEMÁNTICA V2
# ==========================================
# Script para configurar entorno conda en Linux/Mac
# Fecha: 2025-09-26
# ==========================================

set -e  # Detener en caso de error

echo "=========================================="
echo "BÚSQUEDA SEMÁNTICA V2 - SETUP CONDA (Linux)"
echo "=========================================="
echo ""

# ==========================================
# VERIFICACIÓN DE CONDA
# ==========================================
echo "Verificando instalación de conda..."
if ! command -v conda &> /dev/null; then
    echo "❌ Error: conda no está instalado."
    echo "Por favor, instale Miniconda o Anaconda desde:"
    echo "https://docs.conda.io/en/latest/miniconda.html"
    exit 1
fi

echo "✅ conda está instalado: $(conda --version)"

# ==========================================
# CREACIÓN DEL ENTORNO
# ==========================================
ENV_NAME="busqueda_semantica_v2"
PYTHON_VERSION="3.11"

echo ""
echo "Creando entorno conda: $ENV_NAME"
echo "Versión de Python: $PYTHON_VERSION"

# Crear el entorno con Python 3.11
conda create -n $ENV_NAME python=$PYTHON_VERSION -y

echo "✅ Entorno '$ENV_NAME' creado exitosamente"

# ==========================================
# ACTIVACIÓN DEL ENTORNO
# ==========================================
echo ""
echo "Activando entorno: $ENV_NAME"
source "$(conda info --base)/etc/profile.d/conda.sh"
conda activate $ENV_NAME

# Verificar activación
echo "✅ Entorno activado: $(python --version)"

# ==========================================
# INSTALACIÓN DE DEPENDENCIAS
# ==========================================
echo ""
echo "Instalando dependencias desde requirements.txt..."

# Instalar PyTorch con soporte CUDA si está disponible
echo "Instalando PyTorch..."
if python -c "import torch; print('CUDA available:', torch.cuda.is_available())" 2>/dev/null; then
    echo "CUDA detectado, instalando PyTorch con CUDA..."
    pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118
else
    echo "Instalando PyTorch CPU..."
    pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cpu
fi

# Instalar el resto de dependencias
echo "Instalando dependencias principales..."
pip install -r requirements.txt

echo "✅ Dependencias instaladas exitosamente"

# ==========================================
# INSTALACIÓN DE DEPENDENCIAS OPCIONALES
# ==========================================
echo ""
echo "Instalando dependencias opcionales..."

# Instalar jupyter para desarrollo
pip install jupyter notebook ipykernel

# ==========================================
# VERIFICACIÓN DE INSTALACIÓN
# ==========================================
echo ""
echo "Verificando instalación de librerías críticas..."

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