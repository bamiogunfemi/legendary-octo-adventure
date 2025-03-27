from google.oauth2.credentials import Credentials
from google.oauth2 import service_account
from googleapiclient.discovery import build
import pandas as pd
import os
import json
import streamlit as st

class GoogleSheetClient:
    def __init__(self):
        # Update scope to allow both reading and writing
        self.SCOPES = ['https://www.googleapis.com/auth/spreadsheets']
        self.credentials = None
        self.service_account_email = None
        self.initialize_credentials()

    def initialize_credentials(self):
        """Initialize Google Sheets API credentials from environment variables"""
        creds_json = os.getenv('GOOGLE_CREDENTIALS')
        if not creds_json:
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

            # Make the data frame creation more flexible
            if len(values) > 1:
                # If there are headers and data rows
                headers = values[0]
                data = values[1:]
                
                # Create dataframe and handle the case when columns don't match
                # by setting columns explicitly and filling missing values
                df = pd.DataFrame(data)
                
                # If number of headers is less than number of columns, add generic headers
                if len(headers) < df.shape[1]:
                    for i in range(len(headers), df.shape[1]):
                        headers.append(f"Column{i+1}")
                
                # If number of headers is more than columns, truncate to match
                if len(headers) > df.shape[1]:
                    headers = headers[:df.shape[1]]
                    
                # Set the column names
                df.columns = headers
                
            else:
                # Only headers, no data rows
                df = pd.DataFrame(columns=values[0] if values else [])
                
            return df

        except Exception as e:
            st.error(f"Error accessing Google Sheet. Make sure you've shared the sheet with the service account email shown above.")
            raise Exception(f"Error fetching sheet data: {str(e)}")
            
    def write_to_sheet(self, spreadsheet_id, sheet_range, data_frame):
        """Write DataFrame data to a Google Sheet
        
        Args:
            spreadsheet_id (str): The ID of the Google Sheet
            sheet_range (str): The range to write to (e.g., 'Results!A1')
            data_frame (pd.DataFrame): The DataFrame containing results
            
        Returns:
            bool: True if successful, raises exception otherwise
        """
        if not self.credentials:
            raise ValueError("Credentials not initialized")
            
        try:
            # Create headers and data
            headers = data_frame.columns.tolist()
            values = [headers]  # Start with headers as first row
            
            # Add data rows
            for _, row in data_frame.iterrows():
                values.append(row.tolist())
                
            # Connect to the API
            service = build('sheets', 'v4', credentials=self.credentials)
            sheet = service.spreadsheets()
            
            # Clear the existing data in the range
            try:
                sheet.values().clear(
                    spreadsheetId=spreadsheet_id,
                    range=sheet_range
                ).execute()
            except Exception as e:
                # If clearing fails (e.g., new sheet), continue anyway
                pass
                
            # Write the data
            result = sheet.values().update(
                spreadsheetId=spreadsheet_id,
                range=sheet_range,
                valueInputOption="RAW",
                body={"values": values}
            ).execute()
            
            return True
            
        except Exception as e:
            st.error(f"Error writing to Google Sheet: {str(e)}")
            raise Exception(f"Error writing to sheet: {str(e)}")
