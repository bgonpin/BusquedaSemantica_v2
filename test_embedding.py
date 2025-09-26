#!/usr/bin/env python3
"""
Script de prueba para verificar que el modelo de embedding de Ollama funciona correctamente.
"""
import os
import sys
from dotenv import load_dotenv
from pathlib import Path

# Añadir el directorio raíz al path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from langchain_ollama import OllamaEmbeddings

def test_ollama_embedding():
    """Probar el modelo de embedding de Ollama."""
    print("🧪 Probando modelo de embedding de Ollama...")

    # Cargar configuración
    dotenv_path = Path('config/.env')
    load_dotenv(dotenv_path=dotenv_path)

    try:
        # Inicializar modelo de embeddings
        ollama_base_url = os.getenv('OLLAMA_BASE_URL', 'http://localhost:11434')
        embedding_model = os.getenv('EMBEDDING_MODEL', 'embeddinggemma')

        print(f"🔗 Conectando a Ollama en: {ollama_base_url}")
        print(f"🤖 Usando modelo: {embedding_model}")

        model = OllamaEmbeddings(
            base_url=ollama_base_url,
            model=embedding_model
        )

        # Probar generación de embedding
        test_text = "Esta es una imagen de un paisaje con montañas y un lago azul"
        print(f"📝 Generando embedding para: '{test_text}'")

        embedding = model.embed_query(test_text)

        print(f"✅ Embedding generado exitosamente")
        print(f"📊 Dimensiones del embedding: {len(embedding)}")
        print(f"📊 Tipo de datos: {type(embedding)}")
        print(f"📊 Primeros 10 valores: {embedding[:10]}")

        # Verificar que el embedding tenga valores razonables
        if len(embedding) > 0:
            print("✅ El embedding tiene la longitud esperada")
        else:
            print("❌ El embedding está vacío")
            return False

        # Verificar que no todos los valores sean cero
        if any(abs(x) > 0.001 for x in embedding):
            print("✅ El embedding contiene valores no cero")
        else:
            print("⚠️  El embedding contiene solo ceros")
            return False

        print("🎉 ¡Modelo de embedding de Ollama funcionando correctamente!")
        return True

    except Exception as e:
        print(f"❌ Error al probar el modelo de embedding: {e}")
        print("💡 Asegúrate de que:")
        print("   - Ollama esté ejecutándose")
        print("   - El modelo 'embeddinggemma' esté instalado en Ollama")
        print("   - La URL de Ollama sea correcta en config/.env")
        return False

if __name__ == "__main__":
    success = test_ollama_embedding()
    sys.exit(0 if success else 1)