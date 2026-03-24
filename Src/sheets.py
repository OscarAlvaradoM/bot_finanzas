# sheets.py
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from config import GOOGLE_CREDS_PATH, GOOGLE_SHEET_NAME, GOOGLE_WORKSHEET_NAME
    
def init_gsheet():
    scope = [
        "https://spreadsheets.google.com/feeds", 
        "https://www.googleapis.com/auth/drive"
    ]
    creds = ServiceAccountCredentials.from_json_keyfile_name(GOOGLE_CREDS_PATH, scope)
    client = gspread.authorize(creds)
    return client.open(GOOGLE_SHEET_NAME).worksheet(GOOGLE_WORKSHEET_NAME)
