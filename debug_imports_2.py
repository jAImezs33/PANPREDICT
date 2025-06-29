import sys

print("--- Starting import test ---")
sys.stdout.flush()

try:
    print("Importing argparse...")
    import argparse
    print("...OK")
    sys.stdout.flush()

    print("Importing os...")
    import os
    print("...OK")
    sys.stdout.flush()

    print("Importing logging...")
    import logging
    print("...OK")
    sys.stdout.flush()

    print("Importing dotenv...")
    from dotenv import load_dotenv
    print("...OK")
    sys.stdout.flush()

    print("Importing asyncio...")
    import asyncio
    print("...OK")
    sys.stdout.flush()

    print("Importing pandas...")
    import pandas
    print("...OK")
    sys.stdout.flush()

    print("Importing gspread...")
    import gspread
    print("...OK")
    sys.stdout.flush()

    print("Importing requests...")
    import requests
    print("...OK")
    sys.stdout.flush()

    print("Importing telegram...")
    import telegram
    print("...OK")
    sys.stdout.flush()

    print("Importing statsforecast...")
    from statsforecast import StatsForecast
    print("...OK")
    sys.stdout.flush()

    print("Importing src.main...")
    from src.main import save_to_gsheets
    print("...OK")
    sys.stdout.flush()

    print("Importing src.send_telegram...")
    from src.send_telegram import get_forecast_from_gsheets
    print("...OK")
    sys.stdout.flush()

    print("--- All imports successful ---")
    sys.stdout.flush()

except Exception as e:
    import traceback
    print(f"An error occurred: {e}")
    traceback.print_exc()
    sys.stdout.flush()
