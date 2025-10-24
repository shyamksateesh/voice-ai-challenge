import os
import threading
import uuid
from flask import Flask, request, jsonify, render_template, send_from_directory
from werkzeug.utils import secure_filename
import config
from pipeline import run_pipeline # This imports your pipeline.py

# --- Configuration ---
UPLOAD_FOLDER = 'uploads'
OUTPUT_FOLDER = 'outputs'

# <<< FIX: Normalize all extensions to be dot-less
# This cleans up the inconsistent list from config.py (e.g., '.mp4' and 'flac')
def get_allowed_extensions():
    video_exts = set(ext.lstrip('.') for ext in config.VIDEO_EXTENSIONS)
    audio_exts = set(ext.lstrip('.') for ext in config.AUDIO_EXTENSIONS)
    return video_exts | audio_exts

ALLOWED_EXTENSIONS = get_allowed_extensions()

# <<< NEW: Add audio formats our recorder will use
ALLOWED_EXTENSIONS.add("webm")
ALLOWED_EXTENSIONS.add("mp4") # Add mp4 here as well for audio
ALLOWED_EXTENSIONS.add("mp3")

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['OUTPUT_FOLDER'] = OUTPUT_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 1024 * 1024 * 500 # 500 MB upload limit

# --- Global Status Object ---
# This is a simple, in-memory "database" to track our single task
task_status = {
    "status": "idle",  # idle, processing, complete, error
    "message": "Waiting for a file.",
    "output_file": None
}

def allowed_file(filename):
    # <<< FIX: Check if the dot-less extension is in our normalized set
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def run_pipeline_in_background(input_path, output_name, options):
    """
    A wrapper function to run our heavy pipeline in a separate thread
    and update the global status object.
    """
    global task_status
    try:
        final_file_path = run_pipeline(input_path, output_name, options)
        task_status = {
            "status": "complete",
            "message": "Processing complete!",
            "output_file": os.path.basename(final_file_path)
        }
    except Exception as e:
        task_status = {
            "status": "error",
            "message": f"An error occurred: {str(e)}",
            "output_file": None
        }
    finally:
        # Clean up the original upload file after processing
        if os.path.exists(input_path):
            os.remove(input_path)
        print(f"Cleaned up temporary upload: {input_path}")


# --- API Endpoints ---

@app.route('/')
def index():
    """Serves the main HTML page."""
    # Reset status on main page load
    global task_status
    if task_status["status"] != "processing":
         task_status = {"status": "idle", "message": "Waiting for a file.", "output_file": None}
    # Flask automatically looks in the 'templates' folder for this file
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload_file():
    """
    Handles the file upload OR audio blob and starts the background processing thread.
    """
    global task_status
    if task_status["status"] == "processing":
        return jsonify({"error": "Server is already processing a file. Please wait."}), 429

    file = None
    original_filename = None

    # <<< NEW: Check for audio blob OR file upload
    if 'audio_blob' in request.files:
        file = request.files['audio_blob']
        original_filename = "audio_recording.webm" # Give it a default name
        print("Received audio blob.")
    elif 'file' in request.files:
        file = request.files['file']
        original_filename = file.filename
        print(f"Received file: {original_filename}")
    else:
        return jsonify({"error": "No file part or audio blob"}), 400
    
    if original_filename == '':
        return jsonify({"error": "No selected file"}), 400

    if file and allowed_file(original_filename):
        # Use a unique ID for the filename to prevent conflicts
        secure_name = secure_filename(original_filename)
        file_ext = os.path.splitext(secure_name)[1]
        unique_filename = f"{uuid.uuid4()}{file_ext}"
        
        input_file_path = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)
        file.save(input_file_path)
        print(f"Saved temporary file to: {input_file_path}")

        # --- Get options from the form ---
        base_name = os.path.splitext(secure_name)[0]
        output_file_name = f"{base_name}_lyrics.mp4"
        
        # <<< FIX: Check extension against normalized list
        is_video = file_ext.lower().lstrip('.') in (set(ext.lstrip('.') for ext in config.VIDEO_EXTENSIONS))

        # If it's a recording, it's definitely not a video
        if 'audio_blob' in request.files:
            is_video = False

        options = {
            "model": request.form.get("model", "small.en"),
            "wipe_text": request.form.get("wipe_text") == "on",
            "separate_vocals": request.form.get("separate_vocals") == "on",
            "is_video": is_video
        }
        
        # --- Start the background thread ---
        task_status = {"status": "processing", "message": "Processing... This may take a while.", "output_file": None}
        
        thread = threading.Thread(
            target=run_pipeline_in_background,
            args=(input_file_path, output_file_name, options)
        )
        thread.start()
        
        return jsonify({"status": "processing_started", "message": "Processing started..."})
    else:
        # <<< FIX: Provide a more helpful error message
        return jsonify({"error": f"File type not allowed. Allowed types are: {list(ALLOWED_EXTENSIONS)}"}), 400

@app.route('/status')
def get_status():
    """A polling endpoint for the client to check the task status."""
    global task_status
    return jsonify(task_status)

@app.route('/download/<filename>')
def download_file(filename):
    """Serves the final processed video file for download."""
    return send_from_directory(app.config['OUTPUT_FOLDER'], filename, as_attachment=True)

# <<< NEW: Add a route to *serve* the video for embedding >>>
@app.route('/serve_video/<filename>')
def serve_video(filename):
    """Serves the final processed video file for embedding."""
    print(f"Serving video file: {filename}")
    return send_from_directory(app.config['OUTPUT_FOLDER'], filename)

if __name__ == '__main__':
    # This makes the app runnable with `python app.py`
    app.run(debug=True, host='0.0.0.0', port=5001)

