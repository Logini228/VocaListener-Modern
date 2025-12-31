import os
import subprocess
import sys
from pathlib import Path

def validate_corpus_structure(input_dir):
    """Check that the input directory has proper MFA corpus structure"""
    print(f"\nValidating corpus structure in: {input_dir}")

    # Check for required files
    audio_files = [f for f in os.listdir(input_dir) if f.lower().endswith(('.wav', '.mp3', '.flac'))]
    text_files = [f for f in os.listdir(input_dir) if f.lower().endswith('.txt')]

    print(f"Found {len(audio_files)} audio files and {len(text_files)} text files")

    # Verify matching pairs
    valid = True
    for audio in audio_files:
        base_name = os.path.splitext(audio)[0]
        text_file = base_name + '.txt'
        if text_file not in text_files:
            print(f"  ERROR: Missing text file for {audio} - expected {text_file}")
            valid = False

    if not audio_files:
        print("  ERROR: No audio files found in input directory")
        valid = False

    if not valid:
        print("\nMFA requires a specific directory structure:")
        print("  - Each audio file must have a corresponding .txt file with the same name")
        print("  - Example: 'audio.wav' must have 'audio.txt' in the same directory")
        print("  - Text files should contain the transcription of the audio")

    return valid

def check_mfa_models(language):
    """Verify that required MFA models are installed for the specified language"""
    try:
        result = subprocess.run(["mfa", "model", "list"], capture_output=True, text=True, check=True)
        output = result.stdout.lower()

        # Format the language model names based on the language parameter
        lang_model = f"{language}_mfa"
        required_models = [
            f"{lang_model} (dictionary)",
            f"{lang_model} (g2p)",
            f"{lang_model} (acoustic)"
        ]

        missing = []

        for model in required_models:
            if model not in output:
                missing.append(model)

        if missing:
            print(f"\nWARNING: Missing required MFA models for {language}:")
            for model in missing:
                print(f"  - {model}")
            print(f"\nTo install missing models, run these commands:")
            print(f"  mfa model download dictionary {lang_model}")
            print(f"  mfa model download g2p {lang_model}")
            print(f"  mfa model download acoustic {lang_model}")
            return False

        print(f"✓ All required MFA models for {language} are installed")
        return True

    except subprocess.CalledProcessError as e:
        print(f"Error checking MFA models: {e.stderr}")
        return False
    except Exception as e:
        print(f"Unexpected error checking MFA models: {e}")
        return False

def check_environment():
    """Check that required packages are available"""
    required_packages = ['librosa', 'soundfile', 'numpy', 'tqdm']
    missing_packages = []

    for package in required_packages:
        try:
            __import__(package)
        except ImportError:
            missing_packages.append(package)

    if missing_packages:
        print("\nERROR: Missing required Python packages:")
        for package in missing_packages:
            print(f"  - {package}")
        print("\nPlease install them using:")
        print("  conda install " + " ".join(missing_packages))
        return False

    print("✓ All required Python packages are installed")
    return True

def check_mfa_installation():
    """Check if MFA is properly installed and accessible"""
    try:
        result = subprocess.run(["mfa", "--version"], capture_output=True, text=True, check=True)
        print(f"\n✓ MFA is installed. Version: {result.stdout.strip()}")
        return True
    except subprocess.CalledProcessError as e:
        print(f"\nERROR: MFA installation check failed: {e.stderr}")
        return False
    except FileNotFoundError:
        print("\nERROR: MFA command not found. Please ensure MFA is installed and in your PATH.")
        return False
    except Exception as e:
        print(f"\nERROR: Unexpected error checking MFA installation: {e}")
        return False

def run_all_tests(args):
    """Run all validation tests"""
    all_passed = True

    # Test 1: Environment check
    print("\n[Test 1/5] Checking Python environment...")
    if not check_environment():
        all_passed = False

    # Test 2: MFA installation check
    print("\n[Test 2/5] Checking MFA installation...")
    if not check_mfa_installation():
        all_passed = False

    # Test 3: MFA models check
    print(f"\n[Test 3/5] Checking MFA models for {args.language}...")
    if not check_mfa_models(args.language):
        all_passed = False

    # Test 4: Corpus structure validation
    print("\n[Test 4/5] Validating corpus structure...")
    if not validate_corpus_structure(args.input_dir):
        all_passed = False

    # Test 5: Dictionary file check
    print("\n[Test 5/5] Checking dictionary file...")
    if not os.path.exists(args.dict_file):
        print(f"\nERROR: Dictionary file not found at {args.dict_file}")
        all_passed = False
    else:
        print(f"✓ Dictionary file found at {args.dict_file}")

    return all_passed
