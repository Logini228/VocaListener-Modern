# verify_env.py
import importlib
import sys

required_packages = [
    "numpy",
    "librosa",
    "soundfile",
    "tqdm",
    "PyQt6"
]

print(f"Python version: {sys.version}")
print("\nChecking required packages:")

for package in required_packages:
    try:
        importlib.import_module(package)
        print(f"✓ {package} is installed")
    except ImportError as e:
        print(f"✗ {package} is NOT installed: {e}")

# Check if we're in the conda environment
if "conda" in sys.version.lower():
    print("\n✓ Running in a conda environment")
else:
    print("\n! Not running in a conda environment")

# Check MFA installation
try:
    import subprocess
    result = subprocess.run(["mfa", "--version"], capture_output=True, text=True)
    print(f"\n✓ MFA is installed. Version: {result.stdout.strip()}")
except Exception as e:
    print(f"\n✗ MFA is NOT properly installed: {e}")
