import PyPDF2
import os
from flask import Flask, request, jsonify, render_template
import openai
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

app = Flask(__name__)
UPLOAD_FOLDER = 'uploads/'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Set your OpenAI API key from environment variable
openai.api_key = os.getenv('OPENAI_API_KEY')

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

    filepath = os.path.join(UPLOAD_FOLDER, file.filename)
    file.save(filepath)
    text = extract_text_from_pdf(filepath)
    return jsonify({'text': text})

# read the file and extract the text. 
def extract_text_from_pdf(filepath):
    text = ''
    with open(filepath, 'rb') as file:
        reader = PyPDF2.PdfReader(file)
        for page in reader.pages:
            text += page.extract_text()
    return text

@app.route('/query', methods=['POST'])
def query_pdf():
    data = request.json
    if 'query' not in data:
        return jsonify({'error': 'No query provided'}), 400

    query = data['query']
    # Here, you would typically fetch the text from the database or cache
    # For simplicity, let's assume the text is already extracted and stored in a variable
    text = extract_text_from_pdf('uploads/' + data['filename'])  # Replace with actual text extraction logic

    response = openai.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[
            {"role": "system", "content": "You are a helpful assistant that answers questions about PDF documents."},
            {"role": "user", "content": f"Based on this document: {text}\n\nQuestion: {query}"}
        ],
        max_tokens=150
    )

    answer = response.choices[0].message.content.strip()
    return jsonify({'answer': answer})

if __name__ == '__main__':
    app.run(debug=True, port=5012)
