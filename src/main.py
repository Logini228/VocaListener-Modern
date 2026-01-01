import os
import subprocess
import sys
import argparse
import json
import shutil
from pathlib import Path

def setup_tmp_directory(tmp_dir="tmp"):
    """Create and setup the temporary directory for processing"""
    if os.path.exists(tmp_dir):
        shutil.rmtree(tmp_dir)
    os.makedirs(tmp_dir, exist_ok=True)
    print(f"Created clean temporary directory: {tmp_dir}")
    return os.path.abspath(tmp_dir)

def run_mfa_alignment(input_dir, output_dir, temp_dir, language):
    """Run the Montreal Forced Aligner alignment command with specified language"""
    lang_model = f"{language}_mfa"
    mfa_command = [
        "mfa", "align",
        input_dir,
        lang_model,
        lang_model,
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
        process = subprocess.Popen(
            mfa_command,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
            universal_newlines=True
        )

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

def step1_extract_pitch(audio_file, pitch_file, interval_ms=10):
    """Step 1: Extract pitch data from audio file"""
    print(f"\nStep 1: Extracting pitch data from audio...")
    try:
        from pitch_from_audio import extract_pitch_at_intervals
        extract_pitch_at_intervals(audio_file, interval_ms, pitch_file)
        print(f"Pitch data extracted successfully to {pitch_file}")
        return True
    except Exception as e:
        print(f"Warning: Failed to extract pitch: {e}")
        print("Continuing without pitch data...")
        return False

def step2_run_mfa(args, mfa_output_dir, mfa_temp_dir, textgrid_file):
    """Step 2: Run MFA alignment and verify output"""
    print(f"\nStep 2: Running MFA alignment for {args.language}...")
    if not run_mfa_alignment(args.input_dir, mfa_output_dir, mfa_temp_dir, args.language):
        print(f"\nMFA alignment for {args.language} failed. Please check the output above for errors.")
        return False

    # Verify TextGrid file existence
    if not os.path.exists(textgrid_file):
        print(f"\nError: TextGrid file not found at {textgrid_file}")
        print("Checking MFA output directory contents:")
        for file in os.listdir(mfa_output_dir):
            print(f"  - {file}")

        textgrid_files = [f for f in os.listdir(mfa_output_dir) if f.endswith('.TextGrid')]
        if textgrid_files:
            print("\nFound these TextGrid files instead:")
            for f in textgrid_files:
                print(f"  - {f}")
            textgrid_file = os.path.join(mfa_output_dir, textgrid_files[0])
            print(f"\nUsing TextGrid file: {textgrid_file}")
        else:
            print("\nNo TextGrid files found in output directory. MFA alignment likely failed.")
            return False
    return True

def step3_parse_textgrid(textgrid_file, words_json, phones_json):
    """Step 3: Parse TextGrid file into word/phone JSONs"""
    print("\nStep 3: Parsing TextGrid file...")
    try:
        from parse_output import parse_textgrid_with_silence
        parse_textgrid_with_silence(textgrid_file, words_json, phones_json)
        if not (os.path.exists(words_json) and os.path.exists(phones_json)):
            print("Error: Failed to generate words.json or phones.json")
            return False
        return True
    except Exception as e:
        print(f"Error during TextGrid parsing: {str(e)}")
        return False

def step4_remap_phones(phones_json, dict_file, remapped_phones_json):
    """Step 4: Remap phonemes using dictionary"""
    print("\nStep 4: Remapping phonemes...")
    if not os.path.exists(dict_file):
        print(f"Error: Dictionary file not found at {dict_file}")
        print("Please create a dict.txt file with phoneme mappings.")
        return False

    try:
        from clean_phonemes import remap_phones
        remap_phones(phones_json, dict_file, remapped_phones_json)
        if not os.path.exists(remapped_phones_json):
            print("Error: Failed to generate remapped_phones.json")
            return False
        return True
    except Exception as e:
        print(f"Error during phoneme remapping: {str(e)}")
        return False

def step5_convert_to_svp(remapped_phones_json, output_svp, pitch_file=None):
    """Step 5: Convert phonemes to SVP format with pitch data"""
    print("\nStep 5: Converting to SVP format...")
    try:
        with open(remapped_phones_json, 'r', encoding='utf-8') as f:
            phonemes = json.load(f)

        from pitch_phonemes_to_synthv import convert_phonemes_to_svp
        pitch_path = pitch_file if pitch_file and os.path.exists(pitch_file) else None
        convert_phonemes_to_svp(phonemes, output_file=output_svp, pitch_file_path=pitch_path)

        if not os.path.exists(output_svp):
            print(f"Error: Failed to generate {output_svp}")
            return False
        return True
    except Exception as e:
        print(f"Error during SVP conversion: {str(e)}")
        return False

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
    parser.add_argument('--step', type=str, default='all',
                        help='Step(s) to execute (comma-separated numbers or "all"). Steps: '
                             '1=pitch extraction, 2=MFA alignment, 3=parse TextGrid, '
                             '4=remap phones, 5=convert to SVP')

    args = parser.parse_args()

    # Parse step argument
    if args.step.lower() == 'all':
        steps_to_run = {1, 2, 3, 4, 5}
    else:
        try:
            steps_to_run = set(int(step.strip()) for step in args.step.split(','))
        except ValueError:
            print(f"Invalid step specification: {args.step}")
            print("Use comma-separated numbers (e.g., '1,3,5') or 'all'")
            return 1

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

    # Setup temporary directories and find audio file
    tmp_dir = args.tmp_dir#setup_tmp_directory(args.tmp_dir)
    mfa_temp_dir = os.path.join(tmp_dir, "mfa_temp")
    os.makedirs(mfa_temp_dir, exist_ok=True)

    mfa_output_dir = os.path.join(tmp_dir, "mfa_output")
    os.makedirs(mfa_output_dir, exist_ok=True)

    try:
        audio_file = find_audio_file(args.input_dir)
        print(f"\nFound audio file: {audio_file}")
    except FileNotFoundError as e:
        print(e)
        return 1

    # Define intermediate file paths
    audio_base = os.path.splitext(os.path.basename(audio_file))[0]
    textgrid_file = os.path.join(mfa_output_dir, f"{audio_base}.TextGrid")
    words_json = os.path.join(tmp_dir, "words.json")
    phones_json = os.path.join(tmp_dir, "phones.json")
    remapped_phones_json = os.path.join(tmp_dir, "remapped_phones.json")
    pitch_file = os.path.join(tmp_dir, "pitch.txt")

    # Execute requested steps
    success = True
    if 1 in steps_to_run:
        success &= step1_extract_pitch(audio_file, pitch_file, args.pitch_interval)

    if 2 in steps_to_run:
        success &= step2_run_mfa(args, mfa_output_dir, mfa_temp_dir, textgrid_file)

    if 3 in steps_to_run:
        if not os.path.exists(textgrid_file):
            print(f"\nError: TextGrid file missing for step 3. Run step 2 first.")
            success = False
        else:
            success &= step3_parse_textgrid(textgrid_file, words_json, phones_json)

    if 4 in steps_to_run:
        if not os.path.exists(phones_json):
            print(f"\nError: phones.json missing for step 4. Run step 3 first.")
            success = False
        else:
            success &= step4_remap_phones(phones_json, args.dict_file, remapped_phones_json)

    if 5 in steps_to_run:
        if not os.path.exists(remapped_phones_json):
            print(f"\nError: remapped_phones.json missing for step 5. Run step 4 first.")
            success = False
        else:
            success &= step5_convert_to_svp(remapped_phones_json, args.output_svp, pitch_file)
            if success:
                print(f"\nProcessing complete! Output saved to {args.output_svp}")

if __name__ == "__main__":
    sys.exit(main())
