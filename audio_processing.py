import os
from pydub import AudioSegment # type: ignore
import subprocess # <<< ADD THIS
import shutil # <<< ADD THIS

def extract_audio(input_path, wav_path):
    """
    Extracts audio, standardizes it to 16kHz mono for Whisper,
    and saves it as a temporary WAV file.
    """
    try:
        print(f"Extracting audio from '{os.path.basename(input_path)}'...")
        audio = AudioSegment.from_file(input_path)
        audio = audio.set_channels(1).set_frame_rate(16000) 
        audio.export(wav_path, format="wav")
        print(f"Temporary WAV file created at '{wav_path}'.")
        return True
    except Exception as e:
        print(f"Error during audio extraction: {e}")
        return False

# -----------------------------------------------------------------
# --- NEW VOCAL SEPARATION FUNCTION (Add everything below) ---
# -----------------------------------------------------------------
def separate_vocals(input_audio_path, output_vocals_path):
    """
    Uses Demucs to separate vocals from an audio file.
    Saves the output to the specified path.
    Returns True on success, False on failure.
    """
    print("Starting vocal separation with Demucs (this will take a while)...")
    
    # Define a temporary output directory for Demucs
    temp_output_dir = "temp_demucs_output"
    
    try:
        # We use subprocess to call the `demucs` command.
        # This is more stable than importing it as a library.
        # -n htdemucs_ft: A good, fast model.
        # --two-stems=vocals: Tells it to only save the vocals.
        command = [
            "python", "-m", "demucs.separate",
            "-n", "htdemucs_ft",
            "--two-stems=vocals",
            "-o", temp_output_dir,
            input_audio_path
        ]
        
        subprocess.run(command, check=True, capture_output=True, text=True)

        # --- Find the created vocal file ---
        # Demucs creates a nested folder structure, e.g.:
        # temp_demucs_output/htdemucs_ft/temp_audio/vocals.wav
        
        # Get the model name used (e.g., 'htdemucs_ft')
        model_name = "htdemucs_ft" 
        # Get the audio file's base name (e.g., 'temp_audio')
        audio_basename = os.path.splitext(os.path.basename(input_audio_path))[0]
        
        # Construct the expected path
        generated_vocal_path = os.path.join(temp_output_dir, model_name, audio_basename, "vocals.wav")

        if os.path.exists(generated_vocal_path):
            # Move the vocal file to our desired output path
            shutil.move(generated_vocal_path, output_vocals_path)
            print(f"Vocal separation successful. Vocals saved to: {output_vocals_path}")
            return True
        else:
            print(f"Error: Demucs ran, but the vocal file was not found at {generated_vocal_path}")
            return False

    except subprocess.CalledProcessError as e:
        print("--- DEMUCS FAILED ---")
        print(f"Error during vocal separation: {e}")
        print("STDOUT:", e.stdout)
        print("STDERR:", e.stderr)
        print("Please ensure 'demucs' is installed (`pip install demucs`) and that you have enough RAM.")
        return False
    except Exception as e:
        print(f"An unexpected error occurred during separation: {e}")
        return False
    finally:
        # --- Cleanup ---
        # Delete the temporary demucs output folder
        if os.path.exists(temp_output_dir):
            try:
                shutil.rmtree(temp_output_dir)
                print(f"Cleaned up temporary directory: {temp_output_dir}")
            except Exception as e:
                print(f"Warning: Could not clean up {temp_output_dir}. Error: {e}")
