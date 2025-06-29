import os
import os
import json
import gspread
import pandas as pd
import requests
import certifi
from dotenv import load_dotenv
from google.oauth2.service_account import Credentials

# --- SSL Fix for macOS with LibreSSL ---
# Force Python to use the certifi certificate bundle.
cert_path = certifi.where()
os.environ['SSL_CERT_FILE'] = cert_path
os.environ['REQUESTS_CA_BUNDLE'] = cert_path
print(f"--- SSL FIX: Forcing use of certifi bundle at {cert_path} ---")
# --- End SSL Fix ---

def test_gsheets_connection():
    """A simple script to test writing data to Google Sheets."""
    print("--- Starting Google Sheets Connection Test ---")

    # 1. Load Environment Variables
    print("1. Loading environment variables from .env file...")
    load_dotenv()
    sheet_id = os.getenv("GOOGLE_SHEET_ID")
    creds_json_str = os.getenv('GOOGLE_SERVICE_ACC_JSON')

    if not sheet_id or not creds_json_str:
        print("\n[ERROR] GOOGLE_SHEET_ID and GOOGLE_SERVICE_ACC_JSON must be set in the .env file.")
        return

    print("   - Environment variables loaded.")

    # 2. Authenticate with Google API
    try:
        print("2. Authenticating with Google Sheets API...")
        creds_dict = json.loads(creds_json_str)
        creds = Credentials.from_service_account_info(
            creds_dict,
            scopes=["https://www.googleapis.com/auth/spreadsheets"]
        )

        # Create a requests session with a timeout and custom User-Agent
        session = requests.Session()
        session.timeout = 15.0
        # Mimic curl's User-Agent to bypass potential filtering
        session.headers['User-Agent'] = 'curl/8.7.1'
        # The session will automatically use the SSL env vars set above
        client = gspread.Client(auth=creds, session=session)

        print("   - Authentication successful. (Request timeout set to 15s)")
    except Exception as e:
        print(f"\n[ERROR] An error occurred during authentication or client setup: {e}")
        print("   - Please check the content of your GOOGLE_SERVICE_ACC_JSON variable.")
        return

    # 3. Open Spreadsheet and Worksheet
    try:
        print(f"3. Opening spreadsheet with ID: {sheet_id[:10]}...")
        spreadsheet = client.open_by_key(sheet_id)
        sheet_name = "Windsurf-Debug-Test"
        print(f"   - Checking for worksheet named '{sheet_name}'...")
        try:
            worksheet = spreadsheet.worksheet(sheet_name)
            print("   - Found existing worksheet. Clearing it...")
            worksheet.clear()
        except gspread.WorksheetNotFound:
            print("   - Worksheet not found. Creating it...")
            worksheet = spreadsheet.add_worksheet(title=sheet_name, rows="100", cols="20")
        print("   - Worksheet is ready.")
    except gspread.exceptions.SpreadsheetNotFound:
        print(f"\n[ERROR] Spreadsheet with ID '{sheet_id}' not found.")
        print("   - Please ensure the service account email has been shared with the sheet.")
        return
    except Exception as e:
        print(f"\n[ERROR] Could not open spreadsheet or worksheet: {e}")
        return

    # 4. Write Data to Sheet
    try:
        print("4. Preparing and writing data...")
        sample_data = {
            'Product': ['Test A', 'Test B', 'Test C'],
            'Value': [100, 200, 300],
            'Status': ['OK', 'OK', 'OK']
        }
        df = pd.DataFrame(sample_data)
        
        headers = [df.columns.values.tolist()]
        data_to_write = df.values.tolist()
        worksheet.update('A1', headers + data_to_write)
        print("   - Data written successfully.")
    except Exception as e:
        print(f"\n[ERROR] Failed to write data to the sheet: {e}")
        return

    print("\n--- [SUCCESS] Google Sheets connection test completed successfully! ---")
    print(f"Check your Google Sheet for the '{sheet_name}' tab.")

if __name__ == "__main__":
    test_gsheets_connection()
