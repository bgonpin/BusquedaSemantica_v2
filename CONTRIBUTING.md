# 🤝 Guía de Contribución

¡Gracias por tu interés en contribuir al proyecto **Búsqueda Semántica V2**! Esta guía te ayudará a contribuir de manera efectiva al proyecto.

## 📋 Tabla de Contenidos

- [Código de Conducta](#-código-de-conducta)
- [Cómo Contribuir](#-cómo-contribuir)
- [Flujo de Trabajo](#-flujo-de-trabajo)
- [Estándares de Código](#-estándares-de-código)
- [Testing](#-testing)
- [Documentación](#-documentación)
- [Reportar Bugs](#-reportar-bugs)
- [Sugerir Mejoras](#-sugerir-mejoras)

## 🎯 Código de Conducta

Este proyecto sigue el [Código de Conducta de Contributor Covenant](https://www.contributor-covenant.org/version/2/0/code_of_conduct.html). Al participar, se espera que mantengas este código.

Resumen:
- Sé respetuoso y considerado
- Usa un lenguaje inclusivo y acogedor
- Sé colaborativo
- Enfócate en lo que es mejor para la comunidad

## 🚀 Cómo Contribuir

### 1. Fork el Proyecto

1. Ve al repositorio en GitHub
2. Haz clic en el botón "Fork"
3. Clona tu fork localmente:
   ```bash
   git clone https://github.com/tu-usuario/busqueda-semantica-v2.git
   cd busqueda-semantica-v2
   ```

### 2. Configura el Entorno de Desarrollo

```bash
# Crea un entorno virtual
conda create -n busqueda_semantica_dev python=3.9
conda activate busqueda_semantica_dev

# Instala dependencias de desarrollo
pip install -r requirements.txt

# Instala herramientas de desarrollo adicionales
pip install pytest pytest-cov black flake8 mypy
```

### 3. Crea una Rama para tu Feature

```bash
# Asegúrate de estar en la rama principal
git checkout main
git pull origin main

# Crea una rama descriptiva para tu feature
git checkout -b feature/nueva-funcionalidad
# o
git checkout -b fix/correccion-bug
# o
git checkout -b docs/actualizacion-documentacion
```

## 🔄 Flujo de Trabajo

### Para Nuevas Funcionalidades

1. **Crea una rama** con un nombre descriptivo
2. **Implementa la funcionalidad** siguiendo los estándares
3. **Escribe tests** para la nueva funcionalidad
4. **Actualiza la documentación** si es necesario
5. **Haz commit** de tus cambios con mensajes claros
6. **Push** la rama a tu fork
7. **Crea un Pull Request** al repositorio principal

### Para Correcciones de Bugs

1. **Crea una rama** con prefijo `fix/`
2. **Reproduce el bug** y confirma el problema
3. **Implementa la corrección**
4. **Escribe un test** que falle antes y pase después
5. **Verifica** que no rompes otros tests
6. **Crea un Pull Request**

### Mensajes de Commit

Usa el formato [Conventional Commits](https://conventionalcommits.org/):

```
feat: agregar nueva funcionalidad de búsqueda por ubicación
fix: corregir error en el procesamiento de embeddings
docs: actualizar documentación de instalación
test: agregar tests para el módulo de detección de objetos
refactor: optimizar consultas a MongoDB
```

## 📏 Estándares de Código

### Python

- **PEP 8**: Sigue las guías de estilo oficiales de Python
- **Type Hints**: Usa anotaciones de tipo en todas las funciones
- **Docstrings**: Documenta todas las clases y funciones públicas
- **Imports**: Organiza imports siguiendo PEP 8

### Ejemplo de Función Bien Documentada

```python
def procesar_imagenes(
    imagenes: List[str],
    batch_size: int = 50,
    max_workers: Optional[int] = None
) -> List[Dict[str, Any]]:
    """
    Procesa un lote de imágenes para extracción de metadatos.

    Args:
        imagenes: Lista de rutas a las imágenes a procesar
        batch_size: Tamaño del lote para procesamiento
        max_workers: Número máximo de workers para procesamiento paralelo

    Returns:
        Lista de diccionarios con metadatos extraídos

    Raises:
        ValueError: Si batch_size es menor o igual a 0
        FileNotFoundError: Si alguna imagen no existe

    Example:
        >>> imagenes = ["img1.jpg", "img2.jpg"]
        >>> metadatos = procesar_imagenes(imagenes, batch_size=25)
        >>> len(metadatos)
        2
    """
    if batch_size <= 0:
        raise ValueError("batch_size debe ser mayor que 0")

    # Implementación...
```

### Formateo de Código

```bash
# Formatear código con black
black src/ tests/

# Verificar estilo con flake8
flake8 src/ tests/

# Verificar tipos con mypy
mypy src/
```

## 🧪 Testing

### Ejecutar Tests

```bash
# Ejecutar todos los tests
pytest

# Ejecutar tests con cobertura
pytest --cov=src --cov-report=html

# Ejecutar tests específicos
pytest tests/test_busqueda_semantica.py

# Ejecutar tests en paralelo
pytest -n auto
```

### Escribir Tests

- **Unit Tests**: Para funciones individuales
- **Integration Tests**: Para interacción entre componentes
- **End-to-End Tests**: Para flujos completos

```python
import pytest
from src.busqueda_semantica import BuscadorSemantico

def test_buscador_semantico_inicializacion():
    """Test inicialización del buscador semántico."""
    # Arrange
    # Act
    # Assert

def test_busqueda_con_resultados():
    """Test búsqueda semántica con resultados esperados."""
    # Arrange
    # Act
    # Assert
```

## 📚 Documentación

### Actualizar README

- Mantén el README actualizado con cambios importantes
- Incluye ejemplos de uso para nuevas funcionalidades
- Actualiza requisitos si cambian las dependencias

### Documentar APIs

- Documenta todas las funciones públicas
- Incluye ejemplos de uso
- Especifica parámetros y tipos de retorno

### Diagramas

- Actualiza diagramas de arquitectura cuando cambie
- Usa herramientas como Draw.io o PlantUML
- Incluye diagramas en la documentación

## 🐛 Reportar Bugs

### Antes de Reportar

1. **Verifica** si ya existe un issue similar
2. **Reproduce** el bug en un entorno limpio
3. **Documenta** los pasos para reproducir
4. **Incluye** información del entorno

### Información Requerida

- **Descripción**: Descripción clara del bug
- **Pasos**: Pasos para reproducir
- **Comportamiento Esperado**: Qué debería pasar
- **Comportamiento Actual**: Qué pasa en realidad
- **Entorno**: SO, Python version, dependencias
- **Logs**: Logs relevantes si aplica

## 💡 Sugerir Mejoras

### Tipos de Mejoras

- **Feature Requests**: Nuevas funcionalidades
- **Enhancements**: Mejoras a funcionalidades existentes
- **Performance**: Optimizaciones de rendimiento
- **UX/UI**: Mejoras en la interfaz de usuario

### Información Requerida

- **Descripción**: Descripción detallada de la mejora
- **Motivación**: Por qué es útil
- **Ejemplos**: Casos de uso o ejemplos
- **Alternativas**: Otras soluciones consideradas
- **Implementación**: Ideas sobre cómo implementarlo

## 🔍 Revisión de Código

### Pull Request Checklist

- [ ] **Tests**: Todos los tests pasan
- [ ] **Cobertura**: Cobertura de tests adecuada
- [ ] **Documentación**: Documentación actualizada
- [ ] **Estilo**: Código formateado correctamente
- [ ] **Types**: Type hints correctos
- [ ] **Commits**: Mensajes de commit claros
- [ ] **Funcionalidad**: Funcionalidad probada manualmente

### Proceso de Revisión

1. **Revisor** revisa el código
2. **Comentarios** sobre mejoras o problemas
3. **Autor** implementa cambios solicitados
4. **Revisor** aprueba o solicita más cambios
5. **Merge** cuando todo esté correcto

## 📞 Contacto

### Canales de Comunicación

- **Issues**: Para bugs y discusiones técnicas
- **Discussions**: Para ideas y preguntas generales
- **Email**: Para contacto directo con maintainers

### Mantenedores

- **Nombre**: Tu Nombre
- **Email**: tu.email@ejemplo.com
- **GitHub**: [@tu-usuario](https://github.com/tu-usuario)

## 🎉 Reconocimiento

¡Gracias por contribuir! Tu ayuda hace que este proyecto sea mejor para toda la comunidad.

---

<div align="center">

**¡Juntos construimos algo increíble! 🚀**

</div>