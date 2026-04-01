#!/usr/bin/env bash
set -e

# Start FastAPI in background
fastapi dev src/aspis/api/main.py --host 0.0.0.0 --port 8000 &

# Start Streamlit in background
streamlit run src/aspis/ui/main.py --server.address=0.0.0.0 --server.port=8501 &

# Finally, run nginx in the foreground (PID 1)
exec nginx -g "daemon off;"
