import whisper
import config

def transcribe_audio(wav_path, model_name, request_word_timestamps, log_callback):
    """
    Transcribes a WAV file using Whisper and returns phrase-level segments.
    Optionally requests word-level timestamps.
    """
    try:
        log_callback(f"Loading Whisper model '{model_name}'...")
        model = whisper.load_model(model_name)
        log_callback("Model loaded. Starting transcription...")
        
        result = model.transcribe(
            wav_path,
            language='en',
            fp16=False,
            word_timestamps=request_word_timestamps # Pass the flag here
        )
        
        segments = result.get('segments', [])
        log_callback(f"Transcription complete. Found {len(segments)} segments.")
        return segments
    except Exception as e:
        log_callback(f"An error occurred during transcription: {e}")
        return []
