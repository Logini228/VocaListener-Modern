import re
import json
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

def parse_textgrid_with_silence(input_filename, words_output, phones_output):
    """
    Parses a TextGrid file, converting empty intervals ("") to space (" ").
    """
    words_data = []
    phones_data = []
    # 0 = Unknown, 1 = Words Tier, 2 = Phones Tier
    current_tier_type = 0

    try:
        with open(input_filename, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        current_interval = {}

        for line in lines:
            line = line.strip()
            if 'name = "words"' in line:
                current_tier_type = 1
                continue
            elif 'name = "phones"' in line:
                current_tier_type = 2
                continue

            if line.startswith("xmin ="):
                current_interval["xmin"] = float(line.split("=")[1].strip())
            elif line.startswith("xmax ="):
                current_interval["xmax"] = float(line.split("=")[1].strip())
            elif line.startswith("text ="):
                match = re.search(r'"(.*)"', line)
                content = match.group(1) if match else ""
                # CHANGE: If content is empty, swap it for a space
                if content == "":
                    content = " "

                # Append data based on tier type
                if current_tier_type == 1:  # Words
                    words_data.append({
                        "word": content,
                        "start_time": current_interval.get("xmin")
                    })
                elif current_tier_type == 2:  # Phones
                    phones_data.append({
                        "phoneme": content,
                        "start_time": current_interval.get("xmin"),
                        "end_time": current_interval.get("xmax")
                    })
                current_interval = {}

        with open(words_output, 'w', encoding='utf-8') as f:
            json.dump(words_data, f, indent=4, ensure_ascii=False)
        print(f"Created words file: {words_output}")

        with open(phones_output, 'w', encoding='utf-8') as f:
            json.dump(phones_data, f, indent=4, ensure_ascii=False)
        print(f"Created phones file: {phones_output}")

        return words_data, phones_data

    except Exception as e:
        print(f"Error parsing TextGrid file: {e}")
        raise

def main():
    parser = argparse.ArgumentParser(description='Parse TextGrid file with silence handling')
    parser.add_argument('--input', type=str, required=True, help='Input TextGrid file')
    parser.add_argument('--words_output', type=str, default='words.json', help='Output words JSON file')
    parser.add_argument('--phones_output', type=str, default='phones.json', help='Output phones JSON file')

    args = parser.parse_args()
    parse_textgrid_with_silence(args.input, args.words_output, args.phones_output)

if __name__ == "__main__":
    main()
