from google.oauth2.credentials import Credentials
from google.oauth2 import service_account
from googleapiclient.discovery import build
import pandas as pd
import os

class GoogleSheetClient:
    def __init__(self):
        self.SCOPES = ['https://www.googleapis.com/auth/spreadsheets.readonly']
        self.credentials = None
        self.initialize_credentials()

    def initialize_credentials(self):
        """Initialize Google Sheets API credentials from environment variables"""
        creds_json = os.getenv('GOOGLE_CREDENTIALS')
        if not creds_json:
            raise ValueError("Google credentials not found in environment variables")
        
        self.credentials = service_account.Credentials.from_service_account_info(
            eval(creds_json), scopes=self.SCOPES)

    def get_sheet_data(self, spreadsheet_id, range_name):
        """Fetch data from Google Sheets"""
        try:
            service = build('sheets', 'v4', credentials=self.credentials)
            sheet = service.spreadsheets()
            result = sheet.values().get(
                spreadsheetId=spreadsheet_id,
                range=range_name
            ).execute()
            
            values = result.get('values', [])
            if not values:
                return pd.DataFrame()
            
            df = pd.DataFrame(values[1:], columns=values[0])
            return df
            
        except Exception as e:
            raise Exception(f"Error fetching sheet data: {str(e)}")
