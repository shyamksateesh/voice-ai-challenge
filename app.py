import os
import uuid
import threading
import time
import traceback # Import traceback for detailed error logging
from flask import Flask, request, jsonify, render_template, send_from_directory
from werkzeug.utils import secure_filename
import config # Import config settings
import pipeline # Import your main processing logic
# Recognition import removed

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = config.UPLOADS_DIR
app.config['OUTPUT_FOLDER'] = config.OUTPUTS_DIR
# <<< Add this config to potentially get better error details >>>
app.config['PROPAGATE_EXCEPTIONS'] = True
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs(app.config['OUTPUT_FOLDER'], exist_ok=True)

TASK_STATUS = {} # Simplified status

def is_allowed_file(filename):
    allowed_extensions = set(config.VIDEO_EXTENSIONS + config.AUDIO_EXTENSIONS)
    if not filename: return False
    parts = filename.rsplit('.', 1)
    if len(parts) < 2: return False
    ext = f".{parts[1].lower()}"
    return ext in allowed_extensions


# --- Background Processing ---
def start_processing_thread(task_id, input_path, output_path, options, log_callback):
    """Function to run the main pipeline in a separate thread."""
    try:
        # Ensure task exists before starting
        if task_id not in TASK_STATUS:
             print(f"[Thread {task_id}]: Task cancelled or removed before starting.")
             return
        log_callback(f"[Task {task_id}]: Pipeline thread started.")
        pipeline.run_pipeline(input_path, output_path, options, log_callback)
        # Check again if task still exists before marking complete
        if task_id in TASK_STATUS:
             TASK_STATUS[task_id]['status'] = 'complete'
        log_callback(f"[Task {task_id}]: Processing complete.")
    except Exception as e:
        tb_str = traceback.format_exc()
        error_message = f"ERROR in pipeline: {e}\nTraceback:\n{tb_str}"
        log_callback(f"[Task {task_id}]: {error_message}")
        if task_id in TASK_STATUS:
             TASK_STATUS[task_id]['status'] = 'failed'
             TASK_STATUS[task_id]['error'] = str(e) # Store simpler error for UI
    finally:
        log_callback(f"[Task {task_id}]: Main pipeline thread finished.")


# Recognition thread function removed

# --- Flask Routes ---
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload_file():
    """Handles file upload, saves file, and starts background processing."""
    task_id = str(uuid.uuid4()) # Generate task_id *before* try block
    # Define a preliminary log_callback for early errors
    def early_log(message):
        print(message)
        # Don't assume TASK_STATUS[task_id] exists yet
        if task_id in TASK_STATUS and 'log' in TASK_STATUS[task_id]:
            TASK_STATUS[task_id]['log'].append(message)

    early_log(f"[Task {task_id}]: Entering upload route.")

    try:
        # Initialize status only after task_id is confirmed valid
        TASK_STATUS[task_id] = {'status': 'pending', 'log': []}

        # Define the main log_callback for this task
        def log_callback(message):
            print(message)
            task_data = TASK_STATUS.get(task_id)
            if task_data:
                task_data['log'].append(message)

        log_callback(f"[Task {task_id}]: Received upload request.")

        # --- File Handling ---
        input_path = None
        original_filename = "unknown_file"
        # <<< Add check for request.files existence >>>
        if not request.files:
            raise ValueError("No files included in the request.")

        if 'file' in request.files and request.files['file'].filename != '':
            file = request.files['file']
            original_filename = file.filename
            log_callback(f"[Task {task_id}]: Processing uploaded file: {original_filename}") # Log filename
            if file and is_allowed_file(original_filename):
                filename = secure_filename(f"{task_id}_{original_filename}")
                input_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                try: file.save(input_path); log_callback(f"[Task {task_id}]: File saved to {input_path}")
                except Exception as e:
                     raise ValueError(f"Error saving file: {e}") # Raise to be caught by main try/except
            else:
                 raise ValueError(f"File type not allowed: {original_filename}")
        elif 'audio_blob' in request.files:
             blob = request.files['audio_blob']
             original_filename = "audio_recording.wav"
             log_callback(f"[Task {task_id}]: Processing recorded audio blob.")
             filename = secure_filename(f"{task_id}_{original_filename}")
             input_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
             try: blob.save(input_path); log_callback(f"Recorded audio saved to {input_path}")
             except Exception as e:
                  raise ValueError(f"Error saving blob: {e}")
        else:
            raise ValueError("No file part or audio blob found in the request.")

        # --- Options & Output Path ---
        options = {
            'model': request.form.get('model', config.WHISPER_MODEL),
            'do_separate_vocals': request.form.get('separate_vocals') == 'true',
            'do_wipe_text': request.form.get('wipe_text') == 'true',
            'is_video': '.' in original_filename and \
                        f".{original_filename.rsplit('.', 1)[1].lower()}" in config.VIDEO_EXTENSIONS
        }
        log_callback(f"[Task {task_id}]: Options: {options}")

        base_name = os.path.splitext(original_filename)[0]
        output_filename = secure_filename(f"{base_name}_lyrics_{task_id[:8]}.mp4")
        output_path = os.path.join(app.config['OUTPUT_FOLDER'], output_filename)
        TASK_STATUS[task_id]['output_filename'] = output_filename

        # --- Start Background Thread ---
        TASK_STATUS[task_id]['status'] = 'processing'
        log_callback(f"[Task {task_id}]: Starting main processing pipeline thread...")
        thread_pipeline = threading.Thread(
            target=start_processing_thread,
            args=(task_id, input_path, output_path, options, log_callback)
        )
        thread_pipeline.start()

        log_callback(f"[Task {task_id}]: Background processing initiated.")
        return jsonify({'status': 'Processing started', 'task_id': task_id})

    except Exception as e:
        # Log the unexpected error using the preliminary logger
        print(f"!!! UNHANDLED ERROR IN UPLOAD ROUTE for task {task_id} !!!")
        print(traceback.format_exc())
        error_msg = f"Unexpected server error during upload setup: {e}"
        early_log(f"[Task {task_id}]: {error_msg}") # Use early_log

        # Ensure a JSON error response is sent
        response_data = {'error': 'An unexpected server error occurred during upload.'}
        # Update status if task entry was created
        if task_id in TASK_STATUS:
             TASK_STATUS[task_id]['status'] = 'failed'
             TASK_STATUS[task_id]['error'] = response_data['error']
             response_data['task_id'] = task_id

        return jsonify(response_data), 500


# Watcher thread function removed

@app.route('/status/<task_id>')
def task_status(task_id):
    """Provides status updates for a given task."""
    status_info = TASK_STATUS.get(task_id, {'status': 'not_found', 'log': ['Task ID not found.']})
    if 'log' not in status_info: status_info['log'] = []
    if 'song_info' in status_info: del status_info['song_info'] # Clean up old key if present
    return jsonify(status_info)

@app.route('/serve_video/<filename>')
def serve_video(filename):
    """Serves the processed video file for embedding."""
    print(f"[Server] Attempting to serve video: {filename}")
    try:
        return send_from_directory(app.config['OUTPUT_FOLDER'], filename, as_attachment=False, mimetype='video/mp4')
    except FileNotFoundError:
        print(f"[Server] Error: Output file not found: {filename}")
        return jsonify({"error": "File not found"}), 404
    except Exception as e:
         print(f"[Server] Error serving file {filename}: {e}")
         return jsonify({"error": "Could not serve file"}), 500


if __name__ == '__main__':
    app.run(debug=True, port=5001)

