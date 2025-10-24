# --- Central Configuration File ---

# --- Whisper Model ---
WHISPER_MODEL = "medium.en"

# --- File Extensions ---
VIDEO_EXTENSIONS = ['.mp4', '.mov', '.avi', '.mkv']
AUDIO_EXTENSIONS = ['.mp3', '.wav', '.m4a', 'flac']

# --- Subtitle Style ---
RELATIVE_FONT_SIZE = 0.045 # 4.5% of video width
FONT_COLOR = 'white'
FONT_FAMILY = 'Arial-Bold'
FONT_BACKGROUND = 'rgba(0, 0, 0, 0.6)' # Semi-transparent black
SUBTITLE_Y_POSITION = 0.85 # 85% from the top

# --- Karaoke Wipe Style (must be monospace) ---
KARAOKE_FONT = "Courier-Bold"
BG_COLOR = "gray30"

# --- Audio Replacement ---
# If True, and --separate-vocals is used, the final video will
# have its audio *replaced* with the vocals-only track.
REPLACE_AUDIO_WITH_VOCALS = True

# --- Temporary Files ---
TEMP_WAV_FILE = "temp_audio.wav"
VOCALS_WAV_FILE = "temp_vocals.wav" # <<< ADD THIS LINE
