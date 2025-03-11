from google.oauth2.credentials import Credentials
from google.oauth2 import service_account
from googleapiclient.discovery import build
import pandas as pd
import os
import json
import streamlit as st

class GoogleSheetClient:
    def __init__(self):
        self.SCOPES = ['https://www.googleapis.com/auth/spreadsheets.readonly']
        self.credentials = None
        self.service_account_email = None
        self.initialize_credentials()

    def initialize_credentials(self):
        """Initialize Google Sheets API credentials from environment variables"""
        creds_json = os.getenv('GOOGLE_CREDENTIALS')
        if not creds_json:
            st.sidebar.error("⚠️ Google credentials not found. Set the GOOGLE_CREDENTIALS environment variable.")
            st.sidebar.info("To set up Google credentials, go to the Secrets tool in Replit and add your service account JSON as GOOGLE_CREDENTIALS.")
            raise ValueError("Google credentials not found in environment variables")

        try:
            creds_dict = json.loads(creds_json)
            self.service_account_email = creds_dict.get('client_email')
            st.sidebar.info(f"🔑 Service Account Email (share your sheet with this email):\n\n{self.service_account_email}")

            self.credentials = service_account.Credentials.from_service_account_info(
                creds_dict, scopes=self.SCOPES)

        except json.JSONDecodeError:
            raise ValueError("Invalid JSON format in Google credentials")
        except Exception as e:
            raise ValueError(f"Error initializing credentials: {str(e)}")

    def get_sheet_data(self, spreadsheet_id, range_name):
        """Fetch data from Google Sheets"""
        if not self.credentials:
            raise ValueError("Credentials not initialized")

        try:
            service = build('sheets', 'v4', credentials=self.credentials)
            sheet = service.spreadsheets()
            result = sheet.values().get(
                spreadsheetId=spreadsheet_id,
                range=range_name
            ).execute()

            values = result.get('values', [])
            if not values:
                st.warning("No data found in the specified sheet range")
                return pd.DataFrame()

            df = pd.DataFrame(values[1:], columns=values[0])
            return df

        except Exception as e:
            st.error(f"Error accessing Google Sheet. Make sure you've shared the sheet with the service account email shown above.")
            raise Exception(f"Error fetching sheet data: {str(e)}")