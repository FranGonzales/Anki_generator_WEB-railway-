from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import os
from dotenv import load_dotenv
import csv
import io
import google.generativeai as genai
from PIL import Image
import PyPDF2
from pathlib import Path

load_dotenv()

app = Flask(__name__, static_folder='frontend', static_url_path='')

# CORS configurado para producción
CORS(app, resources={
    r"/api/*": {
        "origins": "*",
        "methods": ["GET", "POST"],
        "allow_headers": ["Content-Type"]
    }
})

# Configuración de upload
UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'pdf', 'png', 'jpg', 'jpeg', 'gif', 'webp'}
MAX_FILE_SIZE = 20 * 1024 * 1024  # 20MB

Path(UPLOAD_FOLDER).mkdir(exist_ok=True)

# Configurar Gemini
GOOGLE_API_KEY = os.getenv('GOOGLE_API_KEY')
if not GOOGLE_API_KEY:
    print("⚠️ ADVERTENCIA: No se encontró GOOGLE_API_KEY")
else:
    genai.configure(api_key=GOOGLE_API_KEY)
    print("✅ Gemini configurado correctamente")

PROMPT_TEMPLATE = """
Eres un experto en aprendizaje basado en evidencia y creación de tarjetas ANKI altamente efectivas.

{contexto_adicional}

Analiza el siguiente contenido y crea tarjetas de estudio siguiendo estas reglas:
1. Formula preguntas directas, breves y concretas (1 sola línea). Evita conectores largos. Si una pregunta tiene dos ideas, divídela en dos tarjetas separadas. Prioriza formulaciones cortas como “¿Concepto X?” en lugar de frases extensas.
La respuesta debe ser breve y directa (1–2 oraciones). Si el concepto puede generar confusión o requiere refuerzo, añade debajo una breve explicación, ejemplo o pista mnemotécnica, usando HTML para formato (negritas, saltos de línea o listas cortas).
3. Enfócate en conceptos clave, definiciones, fechas importantes, relaciones y aplicaciones
4. Crea entre 5-25 tarjetas dependiendo de la extensión del contenido
5. Varía el tipo de preguntas: definiciones, comparaciones, aplicaciones, ejemplos
6. Si el contenido incluye diagramas o imágenes, crea preguntas basadas en la información que contienen, pero sin mencionarlos explícitamente. Usa solo los datos o conceptos que muestran, sin frases como “según la imagen” o “en el diagrama”.
7. Las preguntas y respuestas siempre debe evaluar una sola idea ( Atomicidad)
8. Para conceptos abstractos, crea una imagen mental con una palabra clave. No necesitas insertar imágenes (ralentiza repaso), solo evocarlas. Ejemplo: "Imagina un CALEidoscopio para recordar que la **CALEfacción global altera patrones climáticos".
9. Usa un formato simple: PREGUNTA|||RESPUESTA (separado por tres barras verticales |||)

IMPORTANTE PARA FÓRMULAS Y ECUACIONES (Matemáticas, Física, Química):
- Para matemáticas EN LÍNEA usa: \\( formula \\)
  Ejemplo: La energía es \\(E = mc^2\\)
- Para ecuaciones EN BLOQUE usa: \\[ formula \\]
  Ejemplo: \\[F = ma\\]
- NUNCA uses signos de dólar $ ni $$
- Química: \\(H_2O\\), \\(CO_2\\), \\(NaCl\\)
- Fracciones: \\(\\frac(a)(b)\\) usando paréntesis
- Raíces: \\(\\sqrt(x)\\) usando paréntesis
- Potencias: \\(x^2\\), Subíndices: \\(x_1\\)

{contenido}

IMPORTANTE: Responde ÚNICAMENTE con las tarjetas en este formato exacto:
PREGUNTA|||RESPUESTA
(una tarjeta por línea, sin numeración, viñetas ni texto adicional)

Ejemplos de formato correcto:
¿Qué es la fotosíntesis?|||Es el proceso mediante el cual las plantas convierten la luz solar en energía química
¿Cuál es la fórmula de Einstein?|||\\(E = mc^2\\) donde E es energía, m es masa y c es la velocidad de la luz
¿Cómo se escribe agua en química?|||\\(H_2O\\) - dos átomos de hidrógeno y uno de oxígeno
¿Cuál es la segunda ley de Newton?|||\\[F = ma\\] donde F es fuerza, m es masa y a es aceleración
¿Cuáles son los eventos históricos más importantes del Perú?|||<html><p>Los eventos más importantes de la historia del Perú son:</p><ul><li><bImperio Inca (1438)</b>: Consolidación del Tawantinsuyo bajo Pachacútec.</li><li><b>Conquista española (1532)</b>: Captura de Atahualpa por Francisco Pizarro.</li><li><b>Fundación de Lima (1535)</b>: Capital del Virreinato del Perú.</li><li><b>Independencia (1821)</b>: Proclamada por José de San Martín en Lima.</li><li><b>Batalla de Ayacucho (1824)</b>: Aseguró la independencia definitiva.</li><li><b>Guerra del Pacífico (1879–1883)</b>: Perú y Bolivia contra Chile, con pérdida territorial.</li><li><b>Reforma agraria (1968–1975)</b>: Durante el gobierno de Juan Velasco Alvarado.</li><li><b>Conflicto interno (1980–2000)</b>: Enfrentamiento con Sendero Luminoso y el MRTA.</li><li><b>Caída del régimen de Fujimori (2000)</b>: Fin de una década marcada por autoritarismo y corrupción.</li></ul></html>"""

def obtener_modelo_disponible():
    """Intenta obtener el mejor modelo de Gemini disponible"""
    modelos_intentar = [
        ('gemini-2.5-flash', '⚡ Gemini 2.5 Flash (Estable - Multimodal)'),
        ('gemini-2.5-flash-preview-05-20', '⚡ Gemini 2.5 Flash Preview'),
        ('gemini-flash-latest', '⚡ Gemini Flash Latest'),
        ('gemini-2.0-flash', '⚡ Gemini 2.0 Flash'),
    ]
    
    for modelo_nombre, descripcion in modelos_intentar:
        try:
            print(f"🔍 Intentando: {descripcion}")
            modelo = genai.GenerativeModel(modelo_nombre)
            response = modelo.generate_content(
                "Di solo 'OK'",
                generation_config=genai.types.GenerationConfig(
                    temperature=0.1,
                    max_output_tokens=10,
                )
            )
            if response.text:
                print(f"✅ ¡Modelo funcionando! Usando: {descripcion}")
                return modelo, modelo_nombre, descripcion
        except Exception as e:
            print(f"❌ {modelo_nombre} no disponible: {str(e)[:50]}...")
            continue
    
    raise Exception("No se encontró ningún modelo de Gemini disponible")

# Inicializar modelo
try:
    MODELO_GEMINI, NOMBRE_MODELO, DESCRIPCION_MODELO = obtener_modelo_disponible()
    print(f"🎯 Modelo activo: {DESCRIPCION_MODELO}")
except Exception as e:
    print(f"⚠️ Error al inicializar modelo: {str(e)}")
    MODELO_GEMINI = None
    NOMBRE_MODELO = None
    DESCRIPCION_MODELO = None

def extraer_texto_pdf(archivo_bytes):
    """Extrae texto de un archivo PDF"""
    try:
        pdf_file = io.BytesIO(archivo_bytes)
        pdf_reader = PyPDF2.PdfReader(pdf_file)
        
        texto_completo = []
        num_paginas = len(pdf_reader.pages)
        
        print(f"📄 PDF detectado: {num_paginas} páginas")
        
        for i, page in enumerate(pdf_reader.pages):
            texto = page.extract_text()
            if texto.strip():
                texto_completo.append(f"--- Página {i+1} ---\n{texto}")
        
        texto_final = "\n\n".join(texto_completo)
        print(f"✅ Texto extraído: {len(texto_final)} caracteres")
        
        return texto_final
    except Exception as e:
        raise Exception(f"Error al procesar PDF: {str(e)}")

def procesar_imagen(archivo_bytes, mime_type):
    """Procesa una imagen para Gemini"""
    try:
        img = Image.open(io.BytesIO(archivo_bytes))
        
        max_dimension = 3072
        if img.width > max_dimension or img.height > max_dimension:
            ratio = min(max_dimension / img.width, max_dimension / img.height)
            new_size = (int(img.width * ratio), int(img.height * ratio))
            img = img.resize(new_size, Image.Resampling.LANCZOS)
            print(f"🖼️ Imagen redimensionada a: {new_size}")
        
        img_byte_arr = io.BytesIO()
        img_format = img.format or 'PNG'
        img.save(img_byte_arr, format=img_format)
        img_byte_arr = img_byte_arr.getvalue()
        
        print(f"✅ Imagen procesada: {img.width}x{img.height}")
        
        return {
            'mime_type': mime_type,
            'data': img_byte_arr
        }
    except Exception as e:
        raise Exception(f"Error al procesar imagen: {str(e)}")

def generar_tarjetas_con_gemini(contenido_texto=None, imagen_data=None, pdf_data=None, num_tarjetas=None):
    """Genera tarjetas usando Google Gemini 2.5 Flash (Multimodal)"""
    try:
        if not MODELO_GEMINI:
            modelo, nombre, descripcion = obtener_modelo_disponible()
        else:
            modelo = MODELO_GEMINI
            nombre = NOMBRE_MODELO
        
        partes_contenido = []
        contexto_adicional = ""
        tipo_contenido = []
        
        if imagen_data:
            partes_contenido.append({
                'mime_type': imagen_data['mime_type'],
                'data': imagen_data['data']
            })
            contexto_adicional += "Hay una imagen adjunta. Analízala cuidadosamente y crea preguntas sobre su contenido.\n"
            tipo_contenido.append("📸 Imagen")
            print(f"🖼️ Imagen agregada al prompt")
        
        texto_final = ""
        
        if pdf_data:
            texto_final += f"CONTENIDO DEL PDF:\n{pdf_data}\n\n"
            tipo_contenido.append("📄 PDF")
        
        if contenido_texto:
            texto_final += f"TEXTO ADICIONAL:\n{contenido_texto}"
            tipo_contenido.append("📝 Texto")
        
        if not texto_final and not imagen_data:
            raise Exception("No se proporcionó contenido para analizar")
        
        prompt_base = PROMPT_TEMPLATE
        
        if num_tarjetas:
            prompt_base = prompt_base.replace(
                "4. Crea entre 5-25 tarjetas dependiendo de la extensión del contenido",
                f"4. Crea exactamente {num_tarjetas} tarjetas (ni más ni menos)"
            )
            print(f"🎯 Número de tarjetas solicitado: {num_tarjetas}")
        
        prompt = prompt_base.format(
            contexto_adicional=contexto_adicional,
            contenido=texto_final if texto_final else "Analiza la imagen proporcionada."
        )
        
        partes_contenido.append(prompt)
        
        print(f"📤 Enviando a Gemini: {', '.join(tipo_contenido)}")
        
        generation_config = genai.types.GenerationConfig(
            temperature=0.7,
            max_output_tokens=4000,
            top_p=0.95,
            top_k=64,
        )
        
        safety_settings = [
            {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
            {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"},
            {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
            {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"},
        ]
        
        response = modelo.generate_content(
            partes_contenido,
            generation_config=generation_config,
            safety_settings=safety_settings
        )
        
        print(f"✅ Respuesta recibida: {len(response.text)} caracteres")
        
        return response.text, ', '.join(tipo_contenido)
        
    except Exception as e:
        error_msg = str(e)
        print(f"❌ Error: {error_msg}")
        
        if "404" in error_msg:
            raise Exception("El modelo no está disponible.")
        elif "quota" in error_msg.lower() or "limit" in error_msg.lower():
            raise Exception("Límite de uso alcanzado. Espera un minuto.")
        elif "SAFETY" in error_msg:
            raise Exception("Contenido bloqueado por filtros de seguridad.")
        else:
            raise Exception(f"Error: {error_msg}")

def crear_archivo_anki(tarjetas_texto):
    """Convierte el texto de tarjetas en archivo CSV para Anki"""
    lineas = tarjetas_texto.strip().split('\n')
    tarjetas = []
    
    for linea in lineas:
        linea = linea.strip()
        if not linea or '|||' not in linea:
            continue
        
        partes = linea.split('|||', 1)
        if len(partes) == 2:
            pregunta = partes[0].strip()
            respuesta = partes[1].strip()
            
            import re
            pregunta = re.sub(r'^[\d\-\*\•]+[\.\)]\s*', '', pregunta)
            respuesta = re.sub(r'^[\d\-\*\•]+[\.\)]\s*', '', respuesta)
            pregunta = pregunta.replace('**', '')
            respuesta = respuesta.replace('**', '')
            
            if pregunta and respuesta:
                tarjetas.append([pregunta, respuesta])
    
    output = io.StringIO()
    writer = csv.writer(output, delimiter=';', quoting=csv.QUOTE_MINIMAL)
    for tarjeta in tarjetas:
        writer.writerow(tarjeta)
    
    output.seek(0)
    return output.getvalue(), len(tarjetas)

# Servir frontend
@app.route('/')
def index():
    return send_from_directory(app.static_folder, 'index.html')

@app.route('/<path:path>')
def static_files(path):
    return send_from_directory(app.static_folder, path)

# API Routes
@app.route('/api/generar', methods=['POST'])
def generar():
    try:
        if request.content_type and 'multipart/form-data' in request.content_type:
            texto = request.form.get('texto', '')
            archivo = request.files.get('archivo')
            num_tarjetas_str = request.form.get('num_tarjetas', '')
            
            num_tarjetas = int(num_tarjetas_str) if num_tarjetas_str else None
            
            imagen_data = None
            pdf_data = None
            
            if archivo:
                filename = archivo.filename
                file_bytes = archivo.read()
                
                print(f"📁 Archivo recibido: {filename} ({len(file_bytes)} bytes)")
                
                if filename.lower().endswith('.pdf'):
                    pdf_data = extraer_texto_pdf(file_bytes)
                elif filename.lower().endswith(('.png', '.jpg', '.jpeg', '.gif', '.webp')):
                    mime_type = archivo.content_type or 'image/png'
                    imagen_data = procesar_imagen(file_bytes, mime_type)
                else:
                    return jsonify({'error': 'Formato de archivo no soportado'}), 400
        else:
            data = request.json
            texto = data.get('texto', '')
            num_tarjetas = data.get('num_tarjetas')
            imagen_data = None
            pdf_data = None
        
        if not texto and not imagen_data and not pdf_data:
            return jsonify({'error': 'No se proporcionó contenido'}), 400
        
        if not GOOGLE_API_KEY:
            return jsonify({'error': 'API Key no configurada'}), 500
        
        print(f"\n{'='*60}")
        print(f"📝 Nueva solicitud multimodal")
        if num_tarjetas:
            print(f"🎯 Tarjetas solicitadas: {num_tarjetas}")
        print(f"{'='*60}\n")
        
        tarjetas_texto, tipo_contenido = generar_tarjetas_con_gemini(
            contenido_texto=texto if texto else None,
            imagen_data=imagen_data,
            pdf_data=pdf_data,
            num_tarjetas=num_tarjetas
        )
        
        csv_content, num_tarjetas_generadas = crear_archivo_anki(tarjetas_texto)
        
        if num_tarjetas_generadas == 0:
            return jsonify({'error': 'No se generaron tarjetas válidas'}), 400
        
        print(f"\n✅ ¡Éxito! {num_tarjetas_generadas} tarjetas de: {tipo_contenido}\n")
        
        return jsonify({
            'success': True,
            'tarjetas': tarjetas_texto,
            'csv': csv_content,
            'num_tarjetas': num_tarjetas_generadas,
            'modelo_usado': NOMBRE_MODELO,
            'tipo_contenido': tipo_contenido
        })
        
    except Exception as e:
        print(f"\n❌ Error: {str(e)}\n")
        return jsonify({'error': str(e)}), 500

@app.route('/api/salud', methods=['GET'])
def salud():
    return jsonify({
        'status': 'OK',
        'gemini_configurado': bool(GOOGLE_API_KEY),
        'modelo_disponible': bool(MODELO_GEMINI),
        'modelo_nombre': NOMBRE_MODELO,
        'capacidades': ['texto', 'imagen', 'pdf', 'multimodal']
    })

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    print("\n" + "="*70)
    print("🚀 SERVIDOR ANKI + GEMINI 2.5 FLASH (MULTIMODAL)")
    print("="*70)
    print(f"📍 Puerto: {port}")
    if DESCRIPCION_MODELO:
        print(f"🤖 Modelo: {DESCRIPCION_MODELO}")
        print(f"📸 Soporta: Texto, Imágenes, PDFs")
        print(f"💰 Costo: 100% GRATIS")
    print("="*70 + "\n")
    
    app.run(host='0.0.0.0', port=port)