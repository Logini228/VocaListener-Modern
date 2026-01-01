import json
import uuid
import math
import argparse
import sys
import os
import subprocess

def verify_environment():
    # Check if we're in the right conda environment
    conda_env = os.environ.get('CONDA_DEFAULT_ENV', '')
    if 'VocaListener-Modern' not in conda_env:
        print("ERROR: This script must be run in the voice_to_synth conda environment")
        print("Please activate the environment first:")
        print(f"conda activate {os.path.abspath('./lib')}")
        sys.exit(1)

    # Additional package verification
    required_packages = ['librosa', 'soundfile', 'numpy']
    for package in required_packages:
        try:
            __import__(package)
        except ImportError:
            print(f"ERROR: Required package '{package}' is missing from the environment")
            print("Please reinstall the environment using:")
            print("conda env create -f environment.yml --prefix ./lib")
            sys.exit(1)

# Run verification at script start
verify_environment()

# Constants
BLICKS_PER_SECOND = 1411200000  # SynthesizerV uses this resolution
BLICKS_PER_MS = BLICKS_PER_SECOND / 1000
C4_PITCH = 60  # MIDI pitch for C4
C4_FREQ = 261.6255653005986  # Frequency in Hz for MIDI Note 60

# Language to phoneset mapping for SynthesizerV
LANGUAGE_MAPPING = {
    "Japanese": {"language": "japanese", "phoneset": "romaji"},
    "English": {"language": "english", "phoneset": "arpabet"},
    "Spanish": {"language": "spanish", "phoneset": "xsampa"},
    "Mandarin": {"language": "mandarin", "phoneset": "xsampa"}
}

# Updated Constants for your SVP script
MIN_FREQ_THRESHOLD = 60.0  # Matches C2
MAX_FREQ_THRESHOLD = 1200.0 # Allows up to roughly D6 (Safe for sopranos)

def smooth_pitch_data(raw_pitch_data):
    """
    Cleans the raw pitch data.
    Strategy: Use PYIN's accuracy, but still filter out extreme glitches just in case.
    """
    smoothed_data = []
    if not raw_pitch_data:
        return []

    last_valid_hz = C4_FREQ
    for ms, hz in raw_pitch_data:
        current_hz = hz
        is_valid = True

        # PYIN is good, but we check boundaries
        if current_hz < MIN_FREQ_THRESHOLD and current_hz != 0:
            is_valid = False
            #print(f"Pitch too low at {ms}ms: {current_hz}Hz (threshold: {MIN_FREQ_THRESHOLD}Hz)")
        elif current_hz > MAX_FREQ_THRESHOLD and current_hz != 0:
            is_valid = False
            #print(f"Pitch too high at {ms}ms: {current_hz}Hz (threshold: {MAX_FREQ_THRESHOLD}Hz)")

        if is_valid:
            last_valid_hz = current_hz
            smoothed_data.append((ms, current_hz))
        else:
            # If garbage, hold the last known good pitch
            smoothed_data.append((ms, last_valid_hz))
            #print(f"Fixed invalid pitch at {ms}ms: used last valid pitch {last_valid_hz}Hz")

    return smoothed_data

def read_pitch_file(pitch_file_path):
    """
    Parses the pitch file where format is: ms (float) pitch (float)
    Returns a list of tuples: [(ms, pitch_hz), ...]
    """
    pitch_data = []
    try:
        with open(pitch_file_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                parts = line.split()
                if len(parts) >= 2:
                    try:
                        ms = float(parts[0])
                        hz = float(parts[1])
                        pitch_data.append((ms, hz))
                    except ValueError:
                        print(f"Skipping malformed line: {line}")
    except FileNotFoundError:
        print(f"Warning: Pitch file '{pitch_file_path}' not found. Proceeding without pitch data.")
    except Exception as e:
        print(f"Error reading pitch file: {e}")

    print(f"Loaded {len(pitch_data)} pitch points from {pitch_file_path}")
    return pitch_data

def generate_pitch_delta_points(pitch_data):
    """
    Converts pitch data (ms, hz) into SVP systemPitchDelta format (blicks, cents).
    """
    points = []
    for ms, hz in pitch_data:
        # 1. Convert time to blicks
        blicks = int(ms * BLICKS_PER_MS)

        # 2. Convert Hz to Cents deviation from C4
        # Formula: cents = 1200 * log2(f_target / f_base)
        # We use C4_FREQ as the base because the notes are set to C4
        if hz > 0:
            cents = 1200 * math.log2(hz / C4_FREQ)
        else:
            cents = 0.0

        points.append(blicks)
        points.append(cents)

    return points

def create_note(phoneme_data, onset_blicks, duration_blicks):
    """Create a note object from phoneme data"""
    phoneme = phoneme_data["phoneme"]
    language = phoneme_data["language"]

    # Get language settings
    lang_settings = LANGUAGE_MAPPING.get(language, {"language": "japanese", "phoneset": "romaji"})

    # For empty spaces, use breath marker
    if phoneme.strip() == "" or phoneme == " ":
        lyrics = "br"
        phonemes = ""
        # Don't override language for breath marks
        note = {
            "musicalType": "singing",
            "onset": onset_blicks,
            "duration": duration_blicks,
            "lyrics": lyrics,
            "phonemes": phonemes,
            "accent": "",
            "pitch": C4_PITCH,
            "detune": 0,
            "instantMode": True,
            "attributes": {
                "evenSyllableDuration": True
            },
            "systemAttributes": {
                "tF0Offset": 0.0,
                "tF0Left": 0.1000000014901161,
                "tF0Right": 0.1000000014901161,
                "dF0Left": 0.0,
                "dF0Right": 0.0,
                "dF0Vbr": 0.0,
                "evenSyllableDuration": True
            },
            "pitchTakes": {
                "activeTakeId": 0,
                "takes": [{"id": 0, "expr": 0.0, "liked": False}]
            },
            "timbreTakes": {
                "activeTakeId": 0,
                "takes": [{"id": 0, "expr": 0.0, "liked": False}]
            }
        }
    else:
        # For actual phonemes, use "la" as lyrics and specify language override
        lyrics = "la"
        phonemes = phoneme
        note = {
            "musicalType": "singing",
            "onset": onset_blicks,
            "duration": duration_blicks,
            "lyrics": lyrics,
            "phonemes": phonemes,
            "accent": "",
            "pitch": C4_PITCH,
            "detune": 0,
            "instantMode": True,
            "attributes": {
                "evenSyllableDuration": True,
                "languageOverride": lang_settings["language"],
                "phonesetOverride": lang_settings["phoneset"]
            },
            "systemAttributes": {
                "tF0Offset": 0.0,
                "tF0Left": 0.1000000014901161,
                "tF0Right": 0.1000000014901161,
                "dF0Left": 0.0,
                "dF0Right": 0.0,
                "dF0Vbr": 0.0,
                "evenSyllableDuration": True,
                "languageOverride": lang_settings["language"],
                "phonesetOverride": lang_settings["phoneset"]
            },
            "pitchTakes": {
                "activeTakeId": 0,
                "takes": [{"id": 0, "expr": 0.0, "liked": False}]
            },
            "timbreTakes": {
                "activeTakeId": 0,
                "takes": [{"id": 0, "expr": 0.0, "liked": False}]
            }
        }

    return note

def convert_phonemes_to_svp(phonemes_json, output_file="output.svp", pitch_file_path=None):
    """Convert phoneme JSON to SVP file"""
    # Parse input if it's a string
    if isinstance(phonemes_json, str):
        phonemes = json.loads(phonemes_json)
    else:
        phonemes = phonemes_json

    print(f"Processing {len(phonemes)} phonemes for SVP conversion")

    # Create notes from phonemes
    notes = []
    for i, phoneme_data in enumerate(phonemes):
        start_time = phoneme_data["start_time"]
        end_time = phoneme_data["end_time"]

        # Convert seconds to blicks
        onset_blicks = int(start_time * BLICKS_PER_SECOND)
        duration_blicks = int((end_time - start_time) * BLICKS_PER_SECOND)

        note = create_note(phoneme_data, onset_blicks, duration_blicks)
        notes.append(note)

        if i < 5:  # Show first few notes for debugging
            print(f"Note {i}: '{phoneme_data['phoneme']}' from {start_time:.3f}s to {end_time:.3f}s")

    # --- Handle Pitch Data ---
    pitch_delta_points = []
    if pitch_file_path:
        print(f"\nProcessing pitch data from: {pitch_file_path}")
        raw_pitch_data = read_pitch_file(pitch_file_path)
        if raw_pitch_data:
            # APPLY SMOOTHING HERE
            smoothed_pitch_data = smooth_pitch_data(raw_pitch_data)
            pitch_delta_points = generate_pitch_delta_points(smoothed_pitch_data)
            print(f"Loaded {len(raw_pitch_data)} raw pitch points.")
            print(f"Smoothed and generated {len(pitch_delta_points)//2} points for SVP.")

    # Generate unique UUID for the track
    track_uuid = str(uuid.uuid4())

    # Create the SVP structure
    svp = {
        "version": 153,
        "time": {
            "meter": [{"index": 0, "numerator": 4, "denominator": 4}],
            "tempo": [{"position": 0, "bpm": 120.0}]
        },
        "library": [],
        "tracks": [
            {
                "name": "Phoneme Track",
                "dispColor": "ff7db235",
                "dispOrder": 0,
                "renderEnabled": True,
                "mixer": {
                    "gainDecibel": 0.0,
                    "pan": 0.0,
                    "mute": False,
                    "solo": False,
                    "display": True
                },
                "mainGroup": {
                    "name": "main",
                    "uuid": track_uuid,
                    "parameters": {
                        "pitchDelta": {"mode": "cubic", "points": []},
                        "vibratoEnv": {"mode": "cubic", "points": []},
                        "loudness": {"mode": "cubic", "points": []},
                        "tension": {"mode": "cubic", "points": []},
                        "breathiness": {"mode": "cubic", "points": []},
                        "voicing": {"mode": "cubic", "points": []},
                        "gender": {"mode": "cubic", "points": []},
                        "toneShift": {"mode": "cubic", "points": []}
                    },
                    "vocalModes": {},
                    "notes": notes
                },
                "mainRef": {
                    "groupID": track_uuid,
                    "blickAbsoluteBegin": 0,
                    "blickAbsoluteEnd": -1,
                    "blickOffset": 0,
                    "pitchOffset": 0,
                    "isInstrumental": False,
                    # THIS IS WHERE THE PITCH DATA IS INJECTED
                    "systemPitchDelta": {
                        "mode": "cubic",
                        "points": pitch_delta_points
                    },
                    "database": {
                        "name": "Kasane Teto",
                        "language": "japanese",
                        "phoneset": "romaji",
                        "languageOverride": "",
                        "phonesetOverride": "",
                        "backendType": "SVR2AI",
                        "version": "104"
                    },
                    "dictionary": "",
                    "voice": {
                        "vocalModeInherited": True,
                        "vocalModePreset": "",
                        "vocalModeParams": {}
                    },
                    "pitchTakes": {
                        "activeTakeId": 0,
                        "takes": [{"id": 0, "expr": 0.0, "liked": False}]
                    },
                    "timbreTakes": {
                        "activeTakeId": 0,
                        "takes": [{"id": 0, "expr": 0.0, "liked": False}]
                    }
                },
                "groups": []
            }
        ],
        "renderConfig": {
            "destination": "",
            "filename": "output",
            "numChannels": 2,
            "aspirationFormat": "noAspiration",
            "bitDepth": 16,
            "sampleRate": 44100,
            "exportMixDown": True,
            "exportPitch": False
        }
    }

    # Write to file
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(svp, f, indent=2, ensure_ascii=False)

    print(f"\nSVP file created: {output_file}")
    print(f"Total notes: {len(notes)}")
    return svp

def main():
    parser = argparse.ArgumentParser(description='Convert phonemes to Synthesizer V project')
    parser.add_argument('--input', type=str, required=True, help='Input remapped phones JSON file')
    parser.add_argument('--output', type=str, default='output.svp', help='Output SVP file')
    parser.add_argument('--pitch_file', type=str, help='Optional pitch file')

    args = parser.parse_args()

    # Load phonemes
    with open(args.input, 'r', encoding='utf-8') as f:
        phonemes = json.load(f)

    # Convert and save
    convert_phonemes_to_svp(phonemes, args.output, args.pitch_file)

if __name__ == "__main__":
    main()
