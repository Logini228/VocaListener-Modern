import numpy as np
import soundfile as sf
import librosa
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

def extract_pitch_at_intervals(wav_path, interval_ms, output_txt_path):
    """Extract pitch data from audio file at specified intervals"""
    print(f"Loading audio: {wav_path}")

    # Check if file exists
    if not os.path.exists(wav_path):
        raise FileNotFoundError(f"Audio file not found: {wav_path}")

    y, sr = sf.read(wav_path)

    # Ensure mono
    if y.ndim > 1:
        y = np.mean(y, axis=1)

    duration_sec = len(y) / sr
    interval_sec = interval_ms / 1000.0

    # Use PYIN algorithm for better vocal pitch tracking
    print("Extracting pitch using PYIN algorithm...")
    f0, voiced_flag, voiced_probs = librosa.pyin(
        y,
        fmin=librosa.note_to_hz('C2'),
        fmax=librosa.note_to_hz('C7'),
        sr=sr,
        frame_length=2048,
        hop_length=512
    )

    # Get time stamps for each frame
    times_pyin = librosa.times_like(f0, sr=sr, hop_length=512)

    # Prepare output timestamps based on requested interval
    times_out = np.arange(0, duration_sec + interval_sec, interval_sec)

    # Interpolation - replace NaNs with 0.0 before interpolating
    f0_clean = np.nan_to_num(f0, nan=0.0)
    pitches_interp = np.interp(times_out, times_pyin, f0_clean)

    # Write to file
    print(f"Writing pitch data to: {output_txt_path}")
    lines = []
    for t, pitch in zip(times_out, pitches_interp):
        lines.append(f"{int(t * 1000)}\t{pitch:.2f}")

    with open(output_txt_path, 'w') as f:
        f.write('\n'.join(lines))

    print(f"Done. Created pitch file with {len(lines)} points.")
    return output_txt_path

def main():
    parser = argparse.ArgumentParser(description='Extract pitch from audio file')
    parser.add_argument('--input', type=str, required=True, help='Input WAV file')
    parser.add_argument('--interval', type=int, default=10, help='Interval in milliseconds (default: 10ms)')
    parser.add_argument('--output', type=str, default='pitch.txt', help='Output pitch file')

    args = parser.parse_args()

    try:
        extract_pitch_at_intervals(args.input, args.interval, args.output)
    except Exception as e:
        print(f"Error: {e}")
        exit(1)

if __name__ == '__main__':
    main()
