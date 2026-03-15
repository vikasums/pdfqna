import pypdf
import os
from flask import Flask, request, jsonify, render_template
import openai
from dotenv import load_dotenv
from werkzeug.utils import secure_filename

# Load environment variables
load_dotenv()

app = Flask(__name__)
UPLOAD_FOLDER = 'uploads/'
ALLOWED_EXTENSIONS = {'pdf'}
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16 MB limit
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Set your OpenAI API key from environment variable
openai.api_key = os.getenv('OPENAI_API_KEY')
if not openai.api_key:
    raise RuntimeError("OPENAI_API_KEY environment variable is not set")

OPENAI_MODEL = os.getenv('OPENAI_MODEL', 'gpt-3.5-turbo')
MAX_TOKENS = int(os.getenv('OPENAI_MAX_TOKENS', '500'))


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


@app.route('/', methods=['GET'])
def index():
    return render_template('index.html')


@app.route('/upload', methods=['POST'])
def upload_pdf():
    if 'file' not in request.files:
        return jsonify({'error': 'No file part'}), 400

    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400

    if not allowed_file(file.filename):
        return jsonify({'error': 'Only PDF files are allowed'}), 400

    filename = secure_filename(file.filename)
    filepath = os.path.join(UPLOAD_FOLDER, filename)
    file.save(filepath)

    try:
        text = extract_text_from_pdf(filepath)
    except ValueError as e:
        return jsonify({'error': str(e)}), 422
    finally:
        # Clean up uploaded file after extraction
        if os.path.exists(filepath):
            os.remove(filepath)

    return jsonify({'text': text, 'filename': filename})


def extract_text_from_pdf(filepath):
    try:
        extracted_text = ''
        with open(filepath, 'rb') as f:
            reader = pypdf.PdfReader(f)
            for page in reader.pages:
                page_text = page.extract_text()
                if page_text:
                    extracted_text += page_text
        return extracted_text
    except Exception as e:
        raise ValueError(f"Failed to extract text from PDF: {e}") from e


@app.route('/query', methods=['POST'])
def query_pdf():
    data = request.get_json(silent=True)
    if not data:
        return jsonify({'error': 'Request must be JSON'}), 400
    if 'query' not in data:
        return jsonify({'error': 'No query provided'}), 400
    if 'filename' not in data:
        return jsonify({'error': 'No filename provided'}), 400

    query = data['query']
    filename = secure_filename(data['filename'])
    filepath = os.path.join(UPLOAD_FOLDER, filename)

    try:
        text = extract_text_from_pdf(filepath)
    except ValueError as e:
        return jsonify({'error': str(e)}), 422

    try:
        response = openai.chat.completions.create(
            model=OPENAI_MODEL,
            messages=[
                {"role": "system", "content": "You are a helpful assistant that answers questions about PDF documents."},
                {"role": "user", "content": f"Based on this document: {text}\n\nQuestion: {query}"}
            ],
            max_tokens=MAX_TOKENS
        )
        answer = response.choices[0].message.content.strip()
    except openai.AuthenticationError:
        return jsonify({'error': 'Invalid OpenAI API key'}), 401
    except openai.RateLimitError:
        return jsonify({'error': 'OpenAI rate limit exceeded, please try again later'}), 429
    except openai.OpenAIError as e:
        return jsonify({'error': f'OpenAI API error: {e}'}), 502

    return jsonify({'answer': answer})


if __name__ == '__main__':
    debug = os.getenv('FLASK_DEBUG', 'false').lower() == 'true'
    app.run(debug=debug, port=5012)
