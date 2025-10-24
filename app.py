import os
import uuid
import threading
from flask import Flask, request, render_template, jsonify, send_from_directory
from werkzeug.utils import secure_filename

# Import your existing pipeline and config
import pipeline
import config

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = config.UPLOADS_DIR
app.config['MAX_CONTENT_LENGTH'] = 100 * 1024 * 1024  # 100 MB max upload size

# --- Task Status Database (In-Memory) ---
TASK_STATUS = {}

def is_allowed_file(filename):
    """Checks if the file's extension is allowed."""
    if '.' not in filename:
        return False
    # Get the full extension, including the dot (e.g., '.mp4')
    ext = os.path.splitext(filename)[1].lower() 
    allowed_extensions = set(config.VIDEO_EXTENSIONS) | set(config.AUDIO_EXTENSIONS)
    return ext in allowed_extensions

# --- FIX: New helper function to check if it's a video extension ---
def is_video_file(filename):
    """Checks if the file extension is in the VIDEO_EXTENSIONS list."""
    if '.' not in filename:
        return False
    ext = os.path.splitext(filename)[1].lower()
    return ext in set(config.VIDEO_EXTENSIONS)
# --- End of new helper function ---

def start_processing_thread(task_id, input_path, output_path, options):
    """
    This function runs in a separate thread to avoid blocking the web server.
    """
    def log_callback(message):
        print(f"[Task {task_id}]: {message}") 
        if task_id in TASK_STATUS:
            TASK_STATUS[task_id]["log"].append(message)
    
    try:
        pipeline.run_pipeline(input_path, output_path, options, log_callback)
        TASK_STATUS[task_id]["status"] = "Complete"
        TASK_STATUS[task_id]["file"] = os.path.basename(output_path)
        log_callback("Processing complete.")
        
    except Exception as e:
        error_message = f"Error during processing: {e}"
        print(error_message)
        if task_id in TASK_STATUS:
            TASK_STATUS[task_id]["status"] = "Error"
            TASK_STATUS[task_id]["log"].append(error_message)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files and 'audio_blob' not in request.files:
        return jsonify({"error": "No file part"}), 400

    file = request.files.get('file') or request.files.get('audio_blob')
    
    if not file.filename:
         if 'audio_blob' in request.files:
             file.filename = 'audio_recording.wav' 
         else:
              return jsonify({"error": "No file selected or recorded"}), 400

    if file and is_allowed_file(file.filename):
        filename = secure_filename(file.filename)
        input_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        
        os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
        file.save(input_path)

        # --- FIX: Determine if it's a video file ---
        is_video = is_video_file(filename)

        options = {
            "model_size": request.form.get('model_size', config.WHISPER_MODEL),
            "do_wipe_text": request.form.get('do_wipe_text') == 'on',
            "do_separate_vocals": request.form.get('do_separate_vocals') == 'on',
            "is_video": is_video # <<< Pass the boolean here
        }

        task_id = str(uuid.uuid4())
        base_name = os.path.splitext(filename)[0]
        output_filename = f"{base_name}_lyrics.mp4"
        
        os.makedirs(config.OUTPUTS_DIR, exist_ok=True)
        output_path = os.path.join(config.OUTPUTS_DIR, output_filename)

        TASK_STATUS[task_id] = {
            "status": "Processing...",
            "log": ["Task started. File saved."] 
        }

        threading.Thread(
            target=start_processing_thread,
            args=(task_id, input_path, output_path, options)
        ).start()

        return jsonify({"status": "Processing started", "task_id": task_id})
    elif not file:
         return jsonify({"error": "No file selected or recorded"}), 400
    else: 
         return jsonify({"error": f"File type '{os.path.splitext(file.filename)[1]}' not allowed"}), 400


@app.route('/status/<task_id>')
def get_status(task_id):
    status = TASK_STATUS.get(task_id, {"status": "Not Found", "log": []})
    return jsonify(status)

@app.route('/download/<filename>')
def download_file(filename):
    return send_from_directory(config.OUTPUTS_DIR, filename, as_attachment=True)

@app.route('/serve_video/<filename>')
def serve_video(filename):
    return send_from_directory(config.OUTPUTS_DIR, filename, as_attachment=False)

if __name__ == '__main__':
    os.makedirs(config.UPLOADS_DIR, exist_ok=True)
    os.makedirs(config.OUTPUTS_DIR, exist_ok=True)
    app.run(debug=True, port=5001)
