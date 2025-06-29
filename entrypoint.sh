#!/bin/sh

# Exit immediately if a command exits with a non-zero status.
set -e

# Run the main forecasting script
echo "Starting the forecast process..."
python src/main.py

# Run the Telegram notification script
echo "Sending Telegram notification..."
python src/send_telegram.py

echo "Process finished successfully."
