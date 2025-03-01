from flask import Flask, request, jsonify, send_from_directory
from werkzeug.utils import secure_filename
import os
from iclass import analyze_image
import json
from flask_cors import CORS
import time
from dotenv import load_dotenv
import uuid

load_dotenv()

app = Flask(__name__)
CORS(app, supports_credentials=True, origins=["*"])
app.config['UPLOAD_FOLDER'] = 'uploads/'
app.config['MAX_CONTENT_LENGTH'] = 32 * 1024 * 1024  # Increased to 32MB limit
app.config['MAX_RETRIES'] = 3  # 最大重试次数
app.config['RETRY_DELAY'] = 1  # 重试间隔秒数
app.config['REQUEST_TIMEOUT'] = 300  # 5 minutes timeout
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# Temporary storage for parsed courses
courses_db = {}
session_counter = 0

@app.route('/upload', methods=['POST'])
def upload_file():
    global session_counter
    if 'file' not in request.files:
        print("No file uploaded")
        return jsonify({"error": "No file uploaded"}), 400
    
    file = request.files['file']
    if file.filename == '':
        print("Empty filename")
        return jsonify({"error": "Empty filename"}), 400
    
    filename = secure_filename(file.filename)
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    file.save(filepath)

    try:
        retry_count = 0
        last_error = None
        
        while retry_count < app.config['MAX_RETRIES']:
            try:
                # Process the image synchronously
                print(f"Processing image, attempt {retry_count + 1}")
                result = analyze_image(filepath)
                
                # Check if result is None
                if result is None:
                    retry_count += 1
                    if retry_count < app.config['MAX_RETRIES']:
                        print(f"Image analysis attempt {retry_count} returned no results, retrying...")
                        time.sleep(app.config['RETRY_DELAY'])
                        continue
                    else:
                        print("Image analysis failed after all retries")
                        return jsonify({"error": "Failed to analyze image after multiple attempts"}), 500
                
                # Ensure result is properly parsed as JSON
                if isinstance(result, str):
                    try:
                        courses = json.loads(result)
                    except json.JSONDecodeError as e:
                        retry_count += 1
                        last_error = str(e)
                        if retry_count < app.config['MAX_RETRIES']:
                            print(f"JSON parsing error on attempt {retry_count}, retrying...")
                            time.sleep(app.config['RETRY_DELAY'])
                            continue
                        else:
                            print("JSON parsing failed after all retries:", last_error)
                            return jsonify({"error": "Invalid JSON format from image analysis"}), 500
                else:
                    courses = result
                
                session_id = session_counter
                courses_db[session_id] = courses
                session_counter += 1

                final_courses = []
                for course in courses:
                    if course["class_name"] is not None:
                        final_courses.append(course)
                
                return jsonify({
                    "session_id": session_id,
                    "courses": final_courses
                })
                
            except Exception as e:
                retry_count += 1
                last_error = str(e)
                if retry_count < app.config['MAX_RETRIES']:
                    print(f"Error on attempt {retry_count}: {str(e)}, retrying...")
                    time.sleep(app.config['RETRY_DELAY'])
                    continue
                else:
                    print("Operation failed after all retries:", last_error)
                    return jsonify({"error": str(last_error)}), 500
    finally:
        # Clean up the file if it exists
        if os.path.exists(filepath):
            try:
                os.remove(filepath)
                print(f"Removed temporary file: {filepath}")
            except Exception as e:
                print(f"Error removing file {filepath}: {str(e)}")

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint for Render.com"""
    return jsonify({"status": "healthy"})

if __name__ == '__main__':
    app.run(debug=True) 