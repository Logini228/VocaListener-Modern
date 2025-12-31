import os
import subprocess
import sys
import argparse
import json
import shutil
from pathlib import Path

def setup_tmp_directory(tmp_dir="tmp"):
    """Create and setup the temporary directory for processing"""
    # Clear existing tmp directory if it exists
    if os.path.exists(tmp_dir):
        shutil.rmtree(tmp_dir)
    os.makedirs(tmp_dir, exist_ok=True)
    print(f"Created clean temporary directory: {tmp_dir}")
    return os.path.abspath(tmp_dir)

def run_mfa_alignment(input_dir, output_dir, temp_dir, language):
    """Run the Montreal Forced Aligner alignment command with specified language"""
    # Format the language model names
    lang_model = f"{language}_mfa"

    mfa_command = [
        "mfa", "align",
        input_dir,
        lang_model,  # Dictionary
        lang_model,  # Acoustic model
        output_dir,
        "--temp_directory", temp_dir,
        "--beam", "400",
        "--retry_beam", "1000",
        "--clean",
        "--verbose"
    ]

    print(f"\nRunning MFA alignment command for {language}:")
    print(' '.join(mfa_command))
    print(f"Using temporary directory: {temp_dir}")

    try:
        # Run with full output capture for debugging
        process = subprocess.Popen(
            mfa_command,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
            universal_newlines=True
        )

        # Stream output in real-time for better debugging
        print("\nMFA Output:")
        print("-" * 80)
        for line in process.stdout:
            sys.stdout.write(line)
            sys.stdout.flush()
        print("-" * 80)

        process.wait()

        if process.returncode != 0:
            print(f"\nMFA alignment failed with return code: {process.returncode}")
            return False

        print(f"\nMFA alignment for {language} completed successfully")
        return True

    except Exception as e:
        print(f"\nUnexpected error during MFA alignment: {str(e)}")
        return False

def find_audio_file(input_dir):
    """Find the first audio file in the input directory"""
    audio_extensions = ['.wav', '.mp3', '.flac', '.ogg', '.m4a']
    for file in os.listdir(input_dir):
        ext = os.path.splitext(file)[1].lower()
        if ext in audio_extensions:
            return os.path.join(input_dir, file)
    raise FileNotFoundError(f"No audio file found in {input_dir}. Looking for files with extensions: {', '.join(audio_extensions)}")

def extract_pitch_data(audio_file, tmp_dir, interval_ms=10):
    """Extract pitch data from audio file"""
    pitch_file = os.path.join(tmp_dir, "pitch.txt")
    from pitch_from_audio import extract_pitch_at_intervals

    print(f"\nStep 1.5: Extracting pitch data from audio...")
    try:
        extract_pitch_at_intervals(audio_file, interval_ms, pitch_file)
        print(f"Pitch data extracted successfully to {pitch_file}")
        return pitch_file
    except Exception as e:
        print(f"Warning: Failed to extract pitch: {e}")
        print("Continuing without pitch data...")
        return None

def main():
    parser = argparse.ArgumentParser(description='Process audio for Synthesizer V')
    parser.add_argument('--input_dir', type=str, required=True,
                        help='Directory containing audio and text files')
    parser.add_argument('--output_svp', type=str, default='output.svp',
                        help='Output SVP file path')
    parser.add_argument('--tmp_dir', type=str, default='tmp',
                        help='Temporary directory for processing')
    parser.add_argument('--dict_file', type=str, default='dict.txt',
                        help='Dictionary file for phoneme mapping')
    parser.add_argument('--pitch_interval', type=int, default=10,
                        help='Pitch extraction interval in milliseconds (default: 10ms)')
    parser.add_argument('--language', type=str, default='russian',
                        help='Language for MFA alignment (default: russian)')
    parser.add_argument('--debug', action='store_true',
                        help='Run additional validation tests (for debugging only)')

    args = parser.parse_args()

    # Run validation tests if in debug mode
    if args.debug:
        try:
            from tests.test import run_all_tests
            print("=== RUNNING DEBUG VALIDATION TESTS ===")
            if not run_all_tests(args):
                print("\nDebug tests failed. Fix the issues above and try again.")
                return 1
            print("=== DEBUG VALIDATION TESTS PASSED ===\n")
        except ImportError:
            print("Warning: Could not import test module. Continuing without validation.")

    # Setup temporary directory
    tmp_dir = setup_tmp_directory(args.tmp_dir)

    # Create MFA-specific temp directory
    mfa_temp_dir = os.path.join(tmp_dir, "mfa_temp")
    os.makedirs(mfa_temp_dir, exist_ok=True)

    # Find audio file in input directory
    try:
        audio_file = find_audio_file(args.input_dir)
        print(f"\nFound audio file: {audio_file}")
    except FileNotFoundError as e:
        print(e)
        return 1

    # Define paths for intermediate files
    mfa_output_dir = os.path.join(tmp_dir, "mfa_output")
    os.makedirs(mfa_output_dir, exist_ok=True)

    # Get base name without extension for TextGrid file
    audio_base = os.path.splitext(os.path.basename(audio_file))[0]
    textgrid_file = os.path.join(mfa_output_dir, f"{audio_base}.TextGrid")
    words_json = os.path.join(tmp_dir, "words.json")
    phones_json = os.path.join(tmp_dir, "phones.json")
    remapped_phones_json = os.path.join(tmp_dir, "remapped_phones.json")

    # Step 1: Extract pitch data first
    pitch_file = extract_pitch_data(audio_file, tmp_dir, args.pitch_interval)

    # Step 2: Run MFA alignment with specified language
    print(f"\nStep 2: Running MFA alignment for {args.language}...")
    if not run_mfa_alignment(args.input_dir, mfa_output_dir, mfa_temp_dir, args.language):
        print(f"\nMFA alignment for {args.language} failed. Please check the output above for errors.")
        return 1

    # Verify TextGrid file was created
    if not os.path.exists(textgrid_file):
        print(f"\nError: TextGrid file not found at {textgrid_file}")
        print("Checking MFA output directory contents:")
        for file in os.listdir(mfa_output_dir):
            print(f"  - {file}")

        # Check if there are any .TextGrid files with different naming
        textgrid_files = [f for f in os.listdir(mfa_output_dir) if f.endswith('.TextGrid')]
        if textgrid_files:
            print("\nFound these TextGrid files instead:")
            for f in textgrid_files:
                print(f"  - {f}")
            print("\nThis might be a naming issue. Trying to use the first TextGrid file found.")
            textgrid_file = os.path.join(mfa_output_dir, textgrid_files[0])
        else:
            print("\nNo TextGrid files found in output directory. MFA alignment likely failed.")
            return 1

    print(f"\nFound TextGrid file: {textgrid_file}")

    # Step 3: Parse the TextGrid output
    print("\nStep 3: Parsing TextGrid file...")
    from parse_output import parse_textgrid_with_silence
    parse_textgrid_with_silence(textgrid_file, words_json, phones_json)

    # Step 4: Remap phones using dictionary
    print("\nStep 4: Remapping phonemes...")
    if not os.path.exists(args.dict_file):
        print(f"Error: Dictionary file not found at {args.dict_file}")
        print("Please create a dict.txt file with phoneme mappings.")
        return 1
    from clean_phonemes import remap_phones
    remap_phones(phones_json, args.dict_file, remapped_phones_json)

    # Step 5: Convert to SVP format with pitch data
    print("\nStep 5: Converting to SVP format...")
    with open(remapped_phones_json, 'r', encoding='utf-8') as f:
        phonemes = json.load(f)

    from pitch_phonemes_to_synthv import convert_phonemes_to_svp
    convert_phonemes_to_svp(
        phonemes,
        output_file=args.output_svp,
        pitch_file_path=pitch_file if pitch_file and os.path.exists(pitch_file) else None
    )

    print(f"\nProcessing complete! Output saved to {args.output_svp}")

    # Ask if user wants to keep tmp files
    response = input("\nDo you want to keep the temporary files for debugging? (y/n): ").strip().lower()
    if response != 'y':
        print("Cleaning up temporary files...")
        try:
            shutil.rmtree(tmp_dir)
            print(f"Removed temporary directory: {tmp_dir}")
        except Exception as e:
            print(f"Warning: Could not remove temporary directory: {e}")

    return 0

if __name__ == "__main__":
    sys.exit(main())
