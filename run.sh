#!/bin/bash
# Check if we're in the correct environment
if [[ "$CONDA_DEFAULT_ENV" != *"VocaListener-Modern"* ]]; then
    echo "Activating environment..."
    source $(conda info --base)/etc/profile.d/conda.sh
    conda activate lib/
fi

# Execute the command passed to this script
exec "$@"
