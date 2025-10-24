# --- Project Folders ---
UPLOADS_DIR = "uploads"
OUTPUTS_DIR = "outputs"

# --- AI Models ---
WHISPER_MODEL = "medium.en"

# --- File Types ---
VIDEO_EXTENSIONS = ['.mp4', '.mov', '.avi', '.mkv']
# <<< FIX: Added dot to flac
AUDIO_EXTENSIONS = ['.mp3', '.wav', '.m4a', '.flac'] 

# --- Subtitle Style ---
RELATIVE_FONT_SIZE = 0.045 # 4.5% of video width
FONT_COLOR = 'white'
FONT_FAMILY = 'Arial-Bold'
FONT_BACKGROUND = 'rgba(0, 0, 0, 0.6)' # Semi-transparent black
SUBTITLE_Y_POSITION = 0.85 # 85% from the top

# --- Karaoke Style ---
KARAOKE_FONT = "Courier-Bold" # Monospace font for wipe effect
BG_COLOR = "gray30" # Color for un-highlighted text

# --- Processing Options ---
REPLACE_AUDIO_WITH_VOCALS = True # If True and separate_vocals runs, use vocal track

