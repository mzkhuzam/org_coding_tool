# test_setup.py
import streamlit as st
import gspread
import json
import pandas as pd

print(f"🔍 Testing setup...")
print(f"gspread version: {gspread.__version__}")

try:
    # Load secrets
    GOOGLE_CREDENTIALS = st.secrets["GOOGLE_CREDENTIALS"]
    GOOGLE_SHEET_URL = st.secrets["GOOGLE_SHEET_URL"]
    INPUT_SHEET_NAME = st.secrets["INPUT_SHEET_NAME"]
    
    print("✅ Secrets loaded")
    
    # Parse credentials
    creds_dict = json.loads(GOOGLE_CREDENTIALS)
    print("✅ Credentials parsed")
    
    # Create client
    gc = gspread.service_account_from_dict(creds_dict)
    print("✅ gspread client created")
    
    # Open sheet
    sheet = gc.open_by_url(GOOGLE_SHEET_URL)
    print(f"✅ Sheet opened: {sheet.title}")
    
    # Get worksheet
    worksheet = sheet.worksheet(INPUT_SHEET_NAME)
    print(f"✅ Worksheet found: {worksheet.title}")
    
    # Get data
    data = worksheet.get_all_records()
    print(f"✅ Data loaded: {len(data)} rows")
    
    print("\n🎉 All tests passed!")
    
except Exception as e:
    print(f"❌ ERROR: {e}")
    import traceback
    traceback.print_exc()