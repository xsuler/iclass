from flask import Flask, request, jsonify, send_from_directory
from werkzeug.utils import secure_filename
import os
from iclass import analyze_image
import json
from flask_cors import CORS
import time
from dotenv import load_dotenv
import threading
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

# Task status tracking
task_status = {}

def process_image_task(task_id, filepath):
    """Background task to process the image"""
    try:
        task_status[task_id]['status'] = 'processing'
        
        retry_count = 0
        last_error = None
        
        while retry_count < app.config['MAX_RETRIES']:
            try:
                # Update status
                task_status[task_id]['progress'] = (retry_count + 1) * 20
                
                result = analyze_image(filepath)
                
                # Check if result is None
                if result is None:
                    retry_count += 1
                    if retry_count < app.config['MAX_RETRIES']:
                        task_status[task_id]['status'] = f'retry-{retry_count}'
                        print(f"Image analysis attempt {retry_count} returned no results, retrying...")
                        time.sleep(app.config['RETRY_DELAY'])
                        continue
                    else:
                        print("Image analysis failed after all retries")
                        task_status[task_id]['status'] = 'failed'
                        task_status[task_id]['error'] = "Failed to analyze image after multiple attempts"
                        return
                
                # Ensure result is properly parsed as JSON
                if isinstance(result, str):
                    try:
                        courses = json.loads(result)
                    except json.JSONDecodeError as e:
                        retry_count += 1
                        last_error = str(e)
                        if retry_count < app.config['MAX_RETRIES']:
                            task_status[task_id]['status'] = f'retry-{retry_count}'
                            print(f"JSON parsing error on attempt {retry_count}, retrying...")
                            time.sleep(app.config['RETRY_DELAY'])
                            continue
                        else:
                            print("JSON parsing failed after all retries:", last_error)
                            task_status[task_id]['status'] = 'failed'
                            task_status[task_id]['error'] = "Invalid JSON format from image analysis"
                            return
                else:
                    courses = result
                
                global session_counter
                session_id = session_counter
                courses_db[session_id] = courses
                session_counter += 1

                final_courses = []
                for course in courses:
                    if course["class_name"] is not None:
                        final_courses.append(course)
                
                # Update task status with results
                task_status[task_id]['status'] = 'completed'
                task_status[task_id]['progress'] = 100
                task_status[task_id]['result'] = {
                    "session_id": session_id,
                    "courses": final_courses
                }
                return
                
            except Exception as e:
                retry_count += 1
                last_error = str(e)
                if retry_count < app.config['MAX_RETRIES']:
                    task_status[task_id]['status'] = f'retry-{retry_count}'
                    print(f"Error on attempt {retry_count}: {str(e)}, retrying...")
                    time.sleep(app.config['RETRY_DELAY'])
                    continue
                else:
                    print("Operation failed after all retries:", last_error)
                    task_status[task_id]['status'] = 'failed'
                    task_status[task_id]['error'] = str(last_error)
                    return
    except Exception as e:
        task_status[task_id]['status'] = 'failed'
        task_status[task_id]['error'] = str(e)
    finally:
        # Clean up the file if it exists
        if os.path.exists(filepath):
            try:
                os.remove(filepath)
            except Exception as e:
                print(f"Error removing file {filepath}: {str(e)}")

@app.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        print("No file uploaded")
        return jsonify({"error": "No file uploaded"}), 400
    
    file = request.files['file']
    if file.filename == '':
        print("Empty filename")
        return jsonify({"error": "Empty filename"}), 400
    
    # Generate a unique task ID
    task_id = str(uuid.uuid4())
    
    # Save the file
    filename = secure_filename(file.filename)
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    file.save(filepath)
    
    # Initialize task status
    task_status[task_id] = {
        'status': 'pending',
        'progress': 0,
        'created_at': time.time()
    }
    
    # Start processing in background
    thread = threading.Thread(target=process_image_task, args=(task_id, filepath))
    thread.daemon = True
    thread.start()
    
    # Return task ID immediately
    return jsonify({
        "task_id": task_id,
        "status": "pending"
    })

@app.route('/status/<task_id>', methods=['GET'])
def get_task_status(task_id):
    """Get the status of a task"""
    if task_id not in task_status:
        return jsonify({"error": "Task not found"}), 404
    
    status_data = task_status[task_id]
    
    # If task is completed, return the result
    if status_data['status'] == 'completed':
        result = status_data.copy()
        
        # Clean up task status after some time (keep for 1 hour)
        if time.time() - status_data['created_at'] > 3600:
            task_status.pop(task_id, None)
            
        return jsonify(result)
    
    # If task failed, return the error
    if status_data['status'] == 'failed':
        return jsonify(status_data), 500
    
    # Otherwise return current status
    return jsonify(status_data)

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint for Render.com"""
    return jsonify({"status": "healthy"})

if __name__ == '__main__':
    app.run(debug=True) 