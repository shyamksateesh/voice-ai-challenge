import os
import json
from acrcloud.recognizer import ACRCloudRecognizer
import config

def recognize_song(file_path, log_callback):
    """
    Recognizes a song using the ACRCloud API.

    Args:
        file_path (str): Path to the audio/video file.
        log_callback (function): Callback function for logging.

    Returns:
        dict: A dictionary containing song metadata (title, artist, album, spotify_id)
              or None if recognition fails. Returns {} if ACRCloud keys are missing.
    """
    log_callback("Starting song recognition via ACRCloud...")

    # Check if ACRCloud keys are configured
    if not all([config.ACRCLOUD_HOST, config.ACRCLOUD_ACCESS_KEY, config.ACRCLOUD_ACCESS_SECRET]) or \
       "YOUR_ACRCLOUD" in config.ACRCLOUD_HOST:
        log_callback("ACRCloud API keys not configured in config.py. Skipping recognition.")
        return {} # Return empty dict to signify skipped

    acr_config = {
        'host': config.ACRCLOUD_HOST,
        'access_key': config.ACRCLOUD_ACCESS_KEY,
        'access_secret': config.ACRCLOUD_ACCESS_SECRET,
        'recognize_type': 'audio'
    }

    try:
        recognizer = ACRCloudRecognizer(acr_config)
        log_callback("Calling ACRCloud API...")
        # Recognizes audio file by path. Max duration: 5 minutes for free tier? Check docs.
        result_json = recognizer.recognize_by_file(file_path, start_seconds=0)
        result = json.loads(result_json)
        log_callback("Received response from ACRCloud.") # Log successful call

        # --- FIX: Improved Logging for Failure ---
        status_code = result.get('status', {}).get('code', -1) # Default to -1 if missing

        if status_code == 0 and result.get('metadata', {}).get('music'):
            metadata = result['metadata']['music'][0]
            song_info = {
                'title': metadata.get('title'),
                'artists': [artist['name'] for artist in metadata.get('artists', [])],
                'album': metadata.get('album', {}).get('name'),
                'spotify_id': metadata.get('external_metadata', {}).get('spotify', {}).get('track', {}).get('id')
            }
            log_callback(f"Song recognized: {song_info.get('title')} by {', '.join(song_info.get('artists',[]))}")
            return song_info
        else:
            # Log the full response details on failure or no match
            error_msg = result.get('status', {}).get('msg', 'Unknown status')
            log_callback(f"Song recognition failed or no match found.")
            log_callback(f"ACRCloud Status Code: {status_code}")
            log_callback(f"ACRCloud Message: {error_msg}")
            # Optionally log the full result for deep debugging (can be large)
            # log_callback(f"Full ACRCloud Response: {result_json}") 
            return None # Indicate failure or no match
        # --- End Improved Logging ---

    except Exception as e:
        log_callback(f"Critical error during ACRCloud recognition call: {e}")
        return None # Indicate failure
