#!/bin/bash

# 1. Start the Telegram Bot in the background
# The bot uses polling, so it needs to run continuously.
python3 bot.py &

# 2. Start the Streamlit Admin Dashboard in the foreground
# Cloud Run expects a service listening on $PORT (default 8080).
# We bind Streamlit to this port so the container stays healthy.
streamlit run admin_dashboard.py --server.port=${PORT:-8080} --server.address=0.0.0.0
