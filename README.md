# Vocalistener Modern 

**Modern singing-to-synth converter for Vocaloid & SynthV.**

Provide an audio clip of your singing and the exact lyrics text. The tool performs **forced alignment** matching audio phonemes precisely to lyrics using Montreal Forced Aligner (MFA). Then extracts pitch, timing, and phonemes to generate a native .vsqx (Vocaloid) or .svp (SynthV) save file. Open it in your preferred software for further editing with any voicebank.

## Key Features
- **Forced Alignment Explained**: MFA analyzes audio against lyrics to timestamp each phoneme (sound unit like "ah" or "ih"). We map MFA's output to SynthV/Vocaloid phonemes via any dictionary provided under `res/language/soft.txt`, for example `res/russian/synthv.txt`. If a language you want to use for doesn't has a dict file nor even a folder, you need to make it manually, even if a language is supported by SynthV . Edit it freely if alignments don't match your vocals.
- **Language Flexibility**: Supports any MFA language (Russian, German, etc.), even if not native to SynthV; bypassing official voicebank limits.
- **Output**: Ready-to-edit save files for seamless workflow continuation.

## Roadmap
- July 2025: Started development, failed miserably with my initial approach.
- September 2025: Figured out the direction.
- December 30 2025: First prototype for SynthV working.

## Installation
- Download and unpack this repo
- Install Conda for Python. (Miniconda will do fine)
- Before next command, if you have Nvidia GPU you should remove the cpu part from the line 
`  - conda-forge::kalpy=*=cpu*` from `environment.yml` (I don't have any idea about AMD GPUs. I only know MFA uses CUDA by default)
- Create conda enviroment
`conda env create -f environment.yml`
- Now, before you launch any code make sure you are in the enviroment. You can enter it by running
`conda activate lib/` or `. run.sh` in a bash terminal
- Next, you will need to install mfa language packets (russian for example)
`mfa model download acoustic russian_mfa`
`mfa model download dictionary russian_mfa`
- Now you can run `python src/main.py` to see all flags, for example you can run:
`python src/main.py --input_dir tests/testinput --output_svp svp.svp --dict_file res/russian/synthv.txt --language russian`


## License
MIT for free modyfying and distribution

Most of the code in repo was written by an AI

*Not a port of original VocaListener (Nagoya IT, ~2007), a fresh Python implementation.*
