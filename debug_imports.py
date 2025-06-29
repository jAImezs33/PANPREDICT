import sys

def run_debug():
    print("--- Starting Import Debug ---")
    
    try:
        import os
        print("[SUCCESS] Imported os")
        import pandas as pd
        print("[SUCCESS] Imported pandas")
        from dotenv import load_dotenv
        print("[SUCCESS] Imported dotenv")
        import gspread
        print("[SUCCESS] Imported gspread")
        from google.oauth2.service_account import Credentials
        print("[SUCCESS] Imported google.oauth2.service_account")
        import statsforecast
        print("[SUCCESS] Imported statsforecast")
        import prophet
        print("[SUCCESS] Imported prophet")
        import holidays
        print("[SUCCESS] Imported holidays")
        import requests
        print("[SUCCESS] Imported requests")
        import logging
        print("[SUCCESS] Imported logging")
        import pickle
        print("[SUCCESS] Imported pickle")
        import argparse
        print("[SUCCESS] Imported argparse")
        import asyncio
        print("[SUCCESS] Imported asyncio")
        print("--- All imports were successful! ---")
    except Exception as e:
        print(f"[ERROR] An exception occurred: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    run_debug()
