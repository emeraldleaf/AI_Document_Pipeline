#!/bin/bash
# filepath: start_api.sh

echo "🚀 Starting API Server..."
cd /Users/joshuadell/Dev/AI_Document_Pipeline
source .venv/bin/activate
uvicorn api.main:app --reload --host 0.0.0.0 --port 8000