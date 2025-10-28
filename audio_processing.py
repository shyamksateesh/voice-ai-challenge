import os
import subprocess
import shutil
from pydub import AudioSegment
import config

def extract_audio(input_path, wav_path, log_callback):
    """
    Extracts audio, standardizes it to 16kHz mono for Whisper,
    and saves it as a temporary WAV file.
    """
    try:
        log_callback(f"Extracting audio from '{os.path.basename(input_path)}'...")
        audio = AudioSegment.from_file(input_path)
        audio = audio.set_channels(1).set_frame_rate(16000)
        audio.export(wav_path, format="wav")
        log_callback(f"Temporary WAV file created at '{wav_path}'.")
        return wav_path
    except Exception as e:
        log_callback(f"Error during audio extraction: {e}")
        return None

def separate_vocals(audio_path, log_callback):
    """
    Uses Demucs to separate vocals from an audio file.
    Returns the path to the separated vocals file, or None on failure.
    """
    output_dir = "temp_demucs_output"
    try:
        log_callback("Starting vocal separation with Demucs (this will take a while)...")
        
        # Build the command to run Demucs
        command = [
            "python", "-m", "demucs.separate",
            "-n", "htdemucs_ft",
            "--two-stems=vocals",
            "-o", output_dir,
            audio_path
        ]
        
        # Run the command
        # We capture stdout/stderr to log it, but Demucs' progress bars
        # will still print to the console, which is fine.
        result = subprocess.run(command, capture_output=True, text=True, check=True)
        
        # Log Demucs output (useful for debugging)
        if result.stdout:
            log_callback("Demucs STDOUT: " + result.stdout)
        if result.stderr:
            log_callback("Demucs STDERR: " + result.stderr)

        # --- Find the separated vocal file ---
        # Demucs creates a nested folder structure, e.g.,
        # temp_demucs_output/htdemucs_ft/temp_audio/vocals.wav
        
        # Find the model-named folder (e.g., 'htdemucs_ft')
        model_output_dir = os.path.join(output_dir, "htdemucs_ft")
        if not os.path.exists(model_output_dir):
             model_output_dir = os.path.join(output_dir, "htdemucs") # Fallback for older demucs
             if not os.path.exists(model_output_dir):
                 raise Exception("Could not find Demucs output model folder.")
        
        # Find the track-named folder (e.g., 'temp_audio')
        track_name = os.path.splitext(os.path.basename(audio_path))[0]  
        vocal_file_dir = os.path.join(model_output_dir, track_name)
        vocal_file_path = os.path.join(vocal_file_dir, "vocals.wav")

        if not os.path.exists(vocal_file_path):
            raise Exception(f"Could not find 'vocals.wav' in {vocal_file_dir}")

        # --- Move the file and clean up ---
        final_vocal_path = os.path.join(config.UPLOADS_DIR, "vocals_only.wav")
        shutil.move(vocal_file_path, final_vocal_path)
        log_callback(f"Successfully separated vocals: {final_vocal_path}")
        
        return final_vocal_path

    except subprocess.CalledProcessError as e:
        log_callback("--- DEMUCS FAILED ---")
        log_callback(f"Error during vocal separation: {e}")
        log_callback(f"STDOUT: {e.stdout}")
        log_callback(f"STDERR: {e.stderr}")
        log_callback("Please ensure 'demucs' is installed (`pip install demucs`) and that you have enough RAM.")
        return None
    except Exception as e:
        log_callback(f"--- DEMUCS FAILED (Post-processing) ---")
        log_callback(f"Error finding/moving Demucs output: {e}")
        return None
    finally:
        # Clean up the entire demucs output directory
        if os.path.exists(output_dir):
            try:
                shutil.rmtree(output_dir)
                log_callback(f"Cleaned up temporary directory: {output_dir}")
            except Exception as e:
                log_callback(f"Warning: Could not clean up {output_dir}. Error: {e}")
