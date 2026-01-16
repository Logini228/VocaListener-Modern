# Vocalistener Modern 

**Modern singing-to-synth converter for Vocaloid & SynthV.**

Provide an audio clip of your singing and the exact lyrics text. The tool performs **forced alignment** matching audio phonemes precisely to lyrics using Montreal Forced Aligner (MFA). Then extracts pitch, timing, and phonemes to generate a native .vsqx (Vocaloid) or .svp (SynthV) save file. Open it in your preferred software for further editing with any voicebank.

## Key Features
- **Forced Alignment Explained**: MFA analyzes audio against lyrics to timestamp each phoneme (sound unit like "ah" or "ih"). We map MFA's output to SynthV/Vocaloid phonemes via any dictionary provided under `res/language/soft.txt`, for example `res/russian/synthv.txt`. If a language you want to use for doesn't has a dict file nor even a folder, you need to make it manually, even if a language is supported by SynthV . Edit it freely if alignments don't match your vocals.
- **Language Flexibility**: Supports any MFA language (Russian, German, etc.), even if not native to SynthV; bypassing official voicebank limits.
- **Output**: Ready-to-edit save files for seamless workflow continuation.

## History
- July 2025: Started development, failed miserably with my initial approach.
- September 2025: Figured out the direction.
- December 2025: First prototype for SynthV working.


## Installation Steps

1. **Download and unpack** the repository.
2. **Install Conda** for Python (Miniconda is recommended).
   - **Note**: If you have an **Nvidia GPU**, remove the `cpu` part from the line:
     ```
     - conda-forge::kalpy=*=cpu*
     ```
     in the `environment.yml` file.
3. **Create the Conda environment**:
   ```
   conda env create -f environment.yml
   ```
4. **Activate the environment** before running any code:
   ```
   conda activate lib/
   ```
5. **Install MFA language packets** (for example, Russian):
   ```
   mfa model download acoustic russian_mfa
   mfa model download dictionary russian_mfa
   ```
   You can find the full languages list in this [repo](https://github.com/MontrealCorpusTools/mfa-models/tree/main/dictionary)
6. **Run the GUI**:
   ```
   . run.sh
   ```

## License
MIT for free modyfying and distribution

Most of the code in repo was written by an AI

*Not a port of original VocaListener (Nagoya IT, ~2007), a fresh Python implementation.*
