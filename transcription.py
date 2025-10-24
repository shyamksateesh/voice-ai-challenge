import whisper # type: ignore

# <<< FIX: Add word_timestamps parameter
def transcribe_audio(wav_path, model_name, word_timestamps=False):
    """Transcribes a WAV file using Whisper and returns phrase-level segments."""
    try:
        print(f"Loading Whisper model '{model_name}'...")
        model = whisper.load_model(model_name)
        
        # <<< FIX: Use the parameter to decide what to print and request
        if word_timestamps:
            print("Starting transcription (with word-level timestamps)...")
        else:
            print("Starting transcription...")
            
        result = model.transcribe(wav_path, language='en', fp16=False, word_timestamps=word_timestamps)
        
        segments = result.get('segments', [])
        print(f"Transcription complete. Found {len(segments)} segments.")
        return segments
    except Exception as e:
        print(f"An error occurred during transcription: {e}")
        return []

