from PyPDF2 import PdfReader
from langchain.text_splitter import RecursiveCharacterTextSplitter
import os
from langchain_community.embeddings import HuggingFaceEmbeddings
from PIL import Image
from pdf2image import convert_from_path
import google.generativeai as genai
from langchain_community.vectorstores import FAISS
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.chains.question_answering import load_qa_chain
from langchain.prompts import PromptTemplate
from dotenv import load_dotenv
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import json

load_dotenv()
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
if not GOOGLE_API_KEY:
    raise ValueError("GOOGLE_API_KEY NOT FOUND in .env")
genai.configure(api_key=GOOGLE_API_KEY)

app = Flask(__name__, static_folder='.', static_url_path='')
CORS(app, resources={r"/*": {"origins": "*", "methods": ["GET", "POST", "OPTIONS"]}})


def load_document(file_path):
    ext = os.path.splitext(file_path)[-1].lower()
    images = []
    if ext == ".pdf":
        print(f"Converting PDF to images: {file_path}")
        images = convert_from_path(file_path, dpi=300)
    elif ext in [".jpg", ".jpeg", ".png"]:
        print(f"Loading image: {file_path}")
        with Image.open(file_path) as img:
            images = [img.copy()]
    else:
        raise ValueError("Unsupported file format. Please upload a PDF or an image (JPG/PNG).")
    print(f"Loaded {len(images)} page(s).")
    return images

def get_text_from_images(images):
    print("Performing OCR (Image-to-Text) using Gemini-2.5-flash...")
    model = genai.GenerativeModel('gemini-2.5-flash')
    full_text = ""
    for i, img in enumerate(images):
        response = model.generate_content(
            ["Extract all the text from this image and return it as a single block of text.", img]
        )
        full_text += response.text + "\n\n---\n\n"
    print("OCR Complete.")
    return full_text.strip()

def get_conversational_chain():
    prompt_template = """
    You are an expert data extraction bot. Your task is to extract key fields from the provided document text, which is an Aadhaar card.
    The response MUST be a valid JSON object.
    DOCUMENT TEXT:
    {context}
    TASK: Extract the following fields: "name", "gender", "dob", "aadhaar_number", "vid", and "address".
    If a field is not found, use an empty string ("").
    Example for context "Name: Rajesh Kumar\nGender: Male\nDOB: 02/05/1985\nAadhaar No: 2345 6789 0123\nVID: 9122 3901 8765 0000\nAddress: Delhi, India":
    {{
     "name": "Rajesh Kumar",
     "gender": "Male",
     "dob": "02/05/1985",
     "aadhaar_number": "2345 6789 0123",
     "vid": "9122 3901 8765 0000",
     "address": "Delhi, India"
    }}
    JSON Output:
    """
    model = ChatGoogleGenerativeAI(model='gemini-2.5-flash')
    prompt = PromptTemplate(template=prompt_template, input_variables=["context"])
    chain = load_qa_chain(model, chain_type="stuff", prompt=prompt)
    return chain

def extract_info_from_document(text):
    chain = get_conversational_chain()
    from langchain.schema import Document
    docs = [Document(page_content=text)]
    response = chain(
        {"input_documents": docs},
        return_only_outputs=True
    )
    output_text = response.get('output_text', '{}')
    print("Raw output:", output_text)
    
    # Try to parse JSON from the output
    try:
        # Remove markdown code blocks if present
        cleaned = output_text.strip()
        if cleaned.startswith('```'):
            cleaned = cleaned.split('```')[1]
            if cleaned.startswith('json'):
                cleaned = cleaned[4:]
        cleaned = cleaned.strip()
        
        result = json.loads(cleaned)
        return result
    except json.JSONDecodeError as e:
        print(f"JSON parsing error: {e}")
        return {"error": "Failed to parse extraction results", "raw_output": output_text}

# ---------------------------------------------------------------------
# Flask Routes - ORDER MATTERS!
# ---------------------------------------------------------------------

# Handle OPTIONS preflight for CORS
@app.before_request
def handle_preflight():
    if request.method == "OPTIONS":
        response = jsonify({"status": "ok"})
        response.headers.add("Access-Control-Allow-Origin", "*")
        response.headers.add("Access-Control-Allow-Headers", "Content-Type")
        response.headers.add("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        return response, 200

# API Routes FIRST
@app.route('/api/health', methods=['GET'])
def health_check():
    print("Health check endpoint hit")
    return jsonify({"status": "ok", "message": "Backend is running"})

@app.route('/api/upload', methods=['POST'])
def upload_file():
    print("=" * 60)
    print("UPLOAD ENDPOINT HIT")
    print(f"Method: {request.method}")
    print(f"Content-Type: {request.content_type}")
    print(f"Files: {request.files}")
    print("=" * 60)
    
    try:
        if 'file' not in request.files:
            print("No file in request")
            return jsonify({"success": False, "error": "No file uploaded"}), 400
        
        file = request.files['file']
        if file.filename == '':
            print("Empty filename")
            return jsonify({"success": False, "error": "Empty filename"}), 400
        
        # Save uploaded file temporarily
        upload_folder = 'uploads'
        os.makedirs(upload_folder, exist_ok=True)
        file_path = os.path.join(upload_folder, file.filename)
        file.save(file_path)
        
        print(f"File saved: {file_path}")
        
        # Process the document
        images = load_document(file_path)
        document_text = get_text_from_images(images)
        extracted_data = extract_info_from_document(document_text)
        
        # Close all image objects to release file handles
        for img in images:
            if hasattr(img, 'close'):
                img.close()
        
        # Clean up uploaded file
        try:
            os.remove(file_path)
            print("Temporary file deleted")
        except Exception as cleanup_error:
            print(f"Could not delete temp file (non-critical): {cleanup_error}")
            # Don't fail the request if cleanup fails
        
        return jsonify({
            "success": True,
            "data": extracted_data,
            "extracted_text": document_text
        })
    
    except Exception as e:
        print(f"Error: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({"success": False, "error": str(e)}), 500

# Static file routes
@app.route('/style.css')
def serve_css():
    return send_from_directory('.', 'style.css')

@app.route('/script.js')
def serve_js():
    return send_from_directory('.', 'script.js')

# Home route LAST
@app.route('/')
def index():
    return send_from_directory('.', 'index.html')

# Debug: Log all requests
@app.after_request
def after_request(response):
    print(f"Response: {request.method} {request.path} -> {response.status_code}")
    return response

# ---------------------------------------------------------------------
# Run Flask App
# ---------------------------------------------------------------------

if __name__ == '__main__':
    print("=" * 60)
    print("🚀 Starting Flask server...")
    
    print("📍 Backend running at http://localhost:5000")
    print("📍 Upload endpoint: http://localhost:5000/api/upload")
    print("📍 Health check: http://localhost:5000/api/health")
    print("=" * 60)
    app.run(debug=True, host='0.0.0.0', port=5000)

