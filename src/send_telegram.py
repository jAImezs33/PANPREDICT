import os
import logging
import pandas as pd
from dotenv import load_dotenv
import gspread
from google.oauth2.service_account import Credentials
import telegram
import asyncio



def get_forecast_from_gsheets(sheet_id: str) -> pd.DataFrame:
    """Fetches the latest forecast data from the Google Sheet."""
    logging.info("Fetching forecast from Google Sheets...")
    try:
        creds_json_str = os.getenv('GOOGLE_SERVICE_ACC_JSON')
        if not creds_json_str:
            logging.error("GOOGLE_SERVICE_ACC_JSON environment variable not set.")
            return pd.DataFrame()

        import json
        creds_dict = json.loads(creds_json_str)
        creds = Credentials.from_service_account_info(
            creds_dict,
            scopes=["https://www.googleapis.com/auth/spreadsheets.readonly"]
        )
        client = gspread.authorize(creds)

        spreadsheet = client.open_by_key(sheet_id)
        worksheet = spreadsheet.worksheet("Pronóstico")
        
        data = worksheet.get_all_records()
        df = pd.DataFrame(data)
        logging.info(f"Successfully fetched {len(df)} rows from Google Sheets.")
        return df

    except gspread.exceptions.SpreadsheetNotFound:
        logging.error(f"Spreadsheet with ID '{sheet_id}' not found.")
        return pd.DataFrame()
    except gspread.exceptions.WorksheetNotFound:
        logging.error("Worksheet 'Pronóstico' not found.")
        return pd.DataFrame()
    except Exception as e:
        logging.error(f"An error occurred while fetching data from Google Sheets: {e}")
        return pd.DataFrame()

async def send_telegram_message(token: str, chat_id: str, message: str):
    """Sends a message to a Telegram chat using the specified bot token."""
    logging.info(f"Sending message to chat ID {chat_id}...")
    try:
        bot = telegram.Bot(token=token)
        await bot.send_message(chat_id=chat_id, text=message, parse_mode='Markdown')
        logging.info("Message sent successfully.")
    except Exception as e:
        logging.error(f"Failed to send Telegram message: {e}")

async def main():
    """Main function to read forecast and send notification."""
    # --- Configuration ---
    telegram_token = os.getenv('TELEGRAM_TOKEN')
    chat_id = os.getenv('CHAT_ID')
    sheet_id = os.getenv('GOOGLE_SHEET_ID')

    if not all([telegram_token, chat_id, sheet_id]):
        logging.error("Missing one or more required environment variables: TELEGRAM_TOKEN, CHAT_ID, GOOGLE_SHEET_ID")
        return

    # --- Get Forecast ---
    forecast_df = get_forecast_from_gsheets(sheet_id)
    if forecast_df.empty:
        logging.error("Could not retrieve forecast data. Aborting notification.")
        return

    # --- Format Message ---
    # Get tomorrow's forecast (the first row)
    tomorrow_forecast = forecast_df.iloc[0]
    
    message_lines = ["*🥖 Pronóstico para mañana:*"]
    
    # Add a list of products to the message, excluding the 'Fecha' column
    products = [col for col in forecast_df.columns if col != 'Fecha']
    for product in products:
        if product in tomorrow_forecast and pd.notna(tomorrow_forecast[product]) and tomorrow_forecast[product] != '':
            try:
                units = int(float(tomorrow_forecast[product]))
                message_lines.append(f"• {product.capitalize()}: *{units} uds*")
            except (ValueError, TypeError):
                logging.warning(f"Could not parse units for {product}: '{tomorrow_forecast[product]}'")

    message = "\n".join(message_lines)

    # --- Send Notification ---
    await send_telegram_message(telegram_token, chat_id, message)


