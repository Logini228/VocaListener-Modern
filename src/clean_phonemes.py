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

def load_mapping_dict(dict_filename):
    """
    Reads the dict.txt and creates a lookup dictionary.
    Format: symbol | mapped_symbol | language
    """
    mapping = {}
    try:
        with open(dict_filename, 'r', encoding='utf-8') as f:
            for line in f:
                # Skip empty lines or comments
                if not line.strip() or line.startswith('#'):
                    continue
                # Split the line by the pipe symbol
                parts = line.split('|')
                if len(parts) == 3:
                    original = parts[0].strip()
                    new_val = parts[1].strip()
                    lang = parts[2].strip()
                    # Handle the special case for space/silence if needed
                    if original == "":
                        original = " "
                    mapping[original] = {
                        "symbol": new_val,
                        "language": lang
                    }
    except FileNotFoundError:
        print(f"Warning: {dict_filename} not found. No mapping will occur.")
    except Exception as e:
        print(f"Error loading dictionary: {e}")
    return mapping

def remap_phones(input_json, map_file, output_json):
    # 1. Load the map
    conversion_map = load_mapping_dict(map_file)

    # 2. Load the phones data
    try:
        with open(input_json, 'r', encoding='utf-8') as f:
            phones_list = json.load(f)

        print(f"Loaded {len(phones_list)} phonemes from {input_json}")

        new_data = []

        # 3. Process each phone
        for item in phones_list:
            original_phone = item.get("phoneme", " ")

            # Check if this phone exists in our map
            if original_phone in conversion_map:
                mapped_info = conversion_map[original_phone]
                new_phoneme = mapped_info["symbol"]
                new_language = mapped_info["language"]
            else:
                # Fallback if not found in dict.txt
                new_phoneme = original_phone
                new_language = "Japanese"
                print(f"Warning: Phoneme '{original_phone}' not found in dictionary, using default mapping")

            # 4. Build the new object structure
            new_entry = {
                "phoneme": new_phoneme,
                "language": new_language,
                "start_time": item["start_time"],
                "end_time": item["end_time"]
            }
            new_data.append(new_entry)

        # 5. Save the result
        with open(output_json, 'w', encoding='utf-8') as f:
            json.dump(new_data, f, indent=4, ensure_ascii=False)
        print(f"Success! Created {output_json} with {len(new_data)} remapped phonemes")

        return new_data

    except Exception as e:
        print(f"An error occurred while remapping phones: {e}")
        raise

def main():
    parser = argparse.ArgumentParser(description='Remap phonemes using dictionary')
    parser.add_argument('--input', type=str, required=True, help='Input phones JSON file')
    parser.add_argument('--dict', type=str, required=True, help='Dictionary file for mapping')
    parser.add_argument('--output', type=str, default='remapped_phones.json', help='Output remapped phones JSON file')

    args = parser.parse_args()
    remap_phones(args.input, args.dict, args.output)

if __name__ == "__main__":
    main()
