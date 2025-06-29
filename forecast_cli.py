import argparse
import os
import logging
import asyncio
import pandas as pd
from datetime import timedelta
from dotenv import load_dotenv

print("--- DEBUG: Initial imports OK ---", flush=True)

try:
    print("--- DEBUG: Importing sys and setting path...", flush=True)
    import sys
    sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))
    print("--- DEBUG: Path set.", flush=True)

    print("--- DEBUG: Importing dotenv...", flush=True)
    from dotenv import load_dotenv
    print("--- DEBUG: Imported dotenv.", flush=True)

    print("--- DEBUG: Importing from src.main...", flush=True)
    from src.main import (
        load_data,
        preprocess_data,
        create_features_df,
        train_and_forecast,
        save_to_gsheets
    )
    print("--- DEBUG: Imported from src.main.", flush=True)

    print("--- DEBUG: Importing from src.send_telegram...", flush=True)
    from src.send_telegram import get_forecast_from_gsheets, send_telegram_message
    print("--- DEBUG: Imported from src.send_telegram.", flush=True)

    print("--- DEBUG: All local and library imports OK ---", flush=True)
except ImportError as e:
    print(f"--- DEBUG: FAILED TO IMPORT: {e} ---", flush=True)
    sys.exit(1)
except Exception as e:
    print(f"--- DEBUG: An unexpected error occurred during imports: {e}", flush=True)
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Load environment variables from .env file
print("--- DEBUG: Calling load_dotenv() ---", flush=True)
load_dotenv()
print("--- DEBUG: load_dotenv() finished ---", flush=True)

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
print("--- DEBUG: Logging configured ---", flush=True)

def run_forecast_pipeline(csv_path: str, sheet_id: str, retrain: bool):
    """Executes the full forecasting pipeline."""
    print("--- DEBUG: Entering run_forecast_pipeline ---")
    logging.info("--- Starting Forecast Pipeline via CLI ---")
    
    # 1. Load Data
    print("--- DEBUG: Step 1: Loading data ---")
    raw_data = load_data(csv_path)
    if raw_data.empty:
        logging.error("Pipeline stopped: No data loaded.")
        return
    print("--- DEBUG: Step 1: Data loaded successfully ---")

    # 2. Preprocess Data
    print("--- DEBUG: Step 2: Preprocessing data ---")
    processed_data = preprocess_data(raw_data)
    if processed_data.empty:
        logging.error("Pipeline stopped: Preprocessing failed.")
        return
    print("--- DEBUG: Step 2: Data preprocessed successfully ---")

    # 3. Create Features
    print("--- DEBUG: Step 3: Creating features ---")
    HORIZON = 8
    start_date = processed_data['ds'].min()
    end_date = processed_data['ds'].max() + pd.Timedelta(days=HORIZON)
    
    # The features dataframe must have unique_id and ds to be merged correctly
    unique_ids = processed_data['unique_id'].unique()
    features_df = create_features_df(start_date, end_date)
    
    # Filter features for the unique_ids present in the data
    X_df_full = features_df[features_df['unique_id'].isin(unique_ids)]
    print("--- DEBUG: Step 3: Features created successfully ---")

    # 4. Train and Forecast
    print("--- DEBUG: Step 4: Training and forecasting ---")
    forecast = train_and_forecast(processed_data, X_df=X_df_full, h=HORIZON, retrain=retrain)
    print("--- DEBUG: Step 4: Forecasting complete ---")

    # 5. Save Results
    print("--- DEBUG: Step 5: Saving results ---")
    if not forecast.empty and sheet_id:
        save_to_gsheets(forecast, sheet_id)
    else:
        logging.warning("Forecast is empty or Google Sheet ID is not provided. Skipping save.")
    print("--- DEBUG: Step 5: Results saved (or skipped) ---")
    print("--- DEBUG: Exiting run_forecast_pipeline ---")

    logging.info("--- Forecast Pipeline Finished ---")


async def run_telegram_notification(sheet_id: str, token: str, chat_id: str):
    """Runs the Telegram notification part."""
    logging.info("--- Starting Telegram Notification via CLI ---")
    
    forecast_df = get_forecast_from_gsheets(sheet_id)
    if forecast_df.empty:
        logging.error("Could not retrieve forecast data. Aborting notification.")
        return

    tomorrow_forecast = forecast_df.iloc[0]
    message_lines = ["*🥖 Pronóstico para mañana:*"]
    products = [col for col in forecast_df.columns if col != 'Fecha']
    for product in products:
        if product in tomorrow_forecast and pd.notna(tomorrow_forecast[product]) and str(tomorrow_forecast[product]).strip() != '':
            try:
                units = int(float(tomorrow_forecast[product]))
                message_lines.append(f"• {product.capitalize()}: *{units} uds*")
            except (ValueError, TypeError):
                logging.warning(f"Could not parse units for {product}: '{tomorrow_forecast[product]}'")

    message = "\n".join(message_lines)

    await send_telegram_message(token, chat_id, message)
    logging.info("--- Telegram Notification Finished ---")


def main():
    """Main function for the command-line interface."""
    print("--- DEBUG: Entered main() function ---", flush=True)
    load_dotenv()

    parser = argparse.ArgumentParser(description="Pan-Predict 90: Bakery Sales Forecasting Tool")
    parser.add_argument('--csv', type=str, required=True, help="Path to the input CSV file with sales data.")
    parser.add_argument('--sheet-id', type=str, default=os.getenv('GOOGLE_SHEET_ID'), help="Google Sheet ID to save the forecast. Overrides .env variable.")
    parser.add_argument('--retrain', action='store_true', help="Force the model to be retrained, ignoring any saved model.")
    parser.add_argument('--send', action='store_true', help="Send a Telegram notification with tomorrow's forecast after running.")

    args = parser.parse_args()

    if not args.sheet_id:
        logging.error("A Google Sheet ID is required. Provide it via --sheet-id or GOOGLE_SHEET_ID in .env file.")
        return

    # Run the main forecast pipeline
    run_forecast_pipeline(args.csv, args.sheet_id, args.retrain)

    # If --send flag is used, run the notification part
    if args.send:
        telegram_token = os.getenv('TELEGRAM_TOKEN')
        chat_id = os.getenv('CHAT_ID')
        if not all([telegram_token, chat_id]):
            logging.error("To send a notification, TELEGRAM_TOKEN and CHAT_ID must be configured in the .env file.")
        else:
            asyncio.run(run_telegram_notification(args.sheet_id, telegram_token, chat_id))

if __name__ == "__main__":
    print("--- DEBUG: Script execution started in __main__ ---", flush=True)
    main()
    print("--- DEBUG: Script execution finished in __main__ ---", flush=True)
