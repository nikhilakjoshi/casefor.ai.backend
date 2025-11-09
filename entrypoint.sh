#!/bin/bash

# Check if current conda environment is caseforai-backend
REQUIRED_ENV="caseforai-backend"

if [ "$CONDA_DEFAULT_ENV" != "$REQUIRED_ENV" ]; then
    echo "Current conda environment: ${CONDA_DEFAULT_ENV:-none}"
    echo "Attempting to activate $REQUIRED_ENV environment..."

    # Initialize conda for bash if not already done
    eval "$(conda shell.bash hook)"

    # Activate the required environment
    conda activate "$REQUIRED_ENV"

    # Verify activation succeeded
    if [ "$CONDA_DEFAULT_ENV" != "$REQUIRED_ENV" ]; then
        echo "Error: Failed to activate $REQUIRED_ENV environment"
        exit 1
    fi

    echo "Successfully activated $REQUIRED_ENV environment"
fi

uvicorn main:app --reload --host 0.0.0.0 --port 8000