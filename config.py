# -- Directories --
UPLOADS_DIR = "uploads"
OUTPUTS_DIR = "outputs"
DEMUCS_OUTPUT_DIR = "temp_demucs_output" # For cleaning up Demucs temp files

# -- Whisper Options --
WHISPER_MODEL = "medium.en" # Default model

# <<< FIX: Add back allowed file extensions >>>
VIDEO_EXTENSIONS = ['.mp4', '.mov', '.avi', '.mkv']
AUDIO_EXTENSIONS = ['.mp3', '.wav', '.m4a', '.flac'] # Ensure .flac has the dot

# -- Video Style Options --
# For Phrase Video (generate_phrase_video)
RELATIVE_FONT_SIZE = 0.045 # Relative to video width
FONT_COLOR = 'white'
FONT_FAMILY = 'Arial-Bold'
FONT_BACKGROUND = 'rgba(0, 0, 0, 0.6)' # Semi-transparent black
SUBTITLE_Y_POSITION = 0.85 # Relative Y position (0.0 top, 1.0 bottom)

# For Karaoke Video (generate_karaoke_video)
KARAOKE_FONT = "Courier-Bold" # MUST be monospace for wipe effect
BG_COLOR = "gray30" # Added for karaoke base text
# Karaoke uses fixed font size defined in video_processing.py based on width

# -- Pipeline Options --
REPLACE_AUDIO_WITH_VOCALS = True # If True, use separated vocals in final video (requires --separate-vocals)

# ACRCloud settings removed