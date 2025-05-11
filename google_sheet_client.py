from google.oauth2.credentials import Credentials
from google.oauth2 import service_account
from googleapiclient.discovery import build
import pandas as pd
import os
import json
import re
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
            # Check if range starts with a non-first row
            skip_header = False
            match = re.search(r'!([A-Z]+)(\d+)', range_name)
            if match:
                row_num = int(match.group(2))
                if row_num > 1:
                    # Range doesn't start at row 1, so we don't expect headers
                    skip_header = True
                    print(f"Range starts at row {row_num}, will skip header processing")
            
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
            if skip_header:
                # If range doesn't start with row 1, treat all values as data (no headers)
                # Use column letters as headers (A, B, C, etc.)
                df = pd.DataFrame(values)
                headers = [chr(65 + i) for i in range(df.shape[1])]  # A, B, C, ...
                df.columns = headers
            elif len(values) > 1:
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
            error_msg = str(e)
            
            # Check for common errors and provide helpful messages
            if "Unable to parse range" in error_msg:
                sheet_name_error = "Error: Sheet name may be incorrect. Please check that the sheet name matches exactly."
                st.error(sheet_name_error)
                st.info("In Google Sheets, check the tabs at the bottom of your spreadsheet to see the exact sheet names.")
                raise Exception(f"{sheet_name_error} Original error: {error_msg}")
            elif "not found" in error_msg.lower():
                access_error = "Error accessing Google Sheet. Please verify the Sheet ID is correct."
                st.error(access_error)
                raise Exception(f"{access_error} Original error: {error_msg}")
            else:
                access_error = f"Error accessing Google Sheet. Make sure you've shared the sheet with the service account email shown above."
                st.error(access_error)
                raise Exception(f"Error fetching sheet data: {error_msg}")
            
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
            # Check if we're writing to a range that doesn't start at row 1
            # or if we have a special _NOHEADER indicator
            skip_header = False
            
            # Check for explicit _NOHEADER indicator
            if "_NOHEADER" in sheet_range:
                skip_header = True
                # Remove the indicator for actual API calls
                sheet_range = sheet_range.replace("_NOHEADER", "")
                print(f"Explicit _NOHEADER flag detected. Headers will be skipped.")
            
            # Also check based on row number
            match = re.search(r'!([A-Z]+)(\d+)', sheet_range)
            if match:
                row_num = int(match.group(2))
                if row_num > 1:
                    # Range doesn't start at row 1, don't include headers
                    skip_header = True
                    print(f"Output range starts at row {row_num}, will skip writing headers")
            
            # Prepare the values to write
            if skip_header:
                # Just add data rows without headers
                values = []
                for _, row in data_frame.iterrows():
                    values.append(row.tolist())
            else:
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
            error_msg = str(e)
            
            # Check for common errors and provide more helpful messages
            if "Unable to parse range" in error_msg:
                sheet_name_error = "Error: Sheet name may be incorrect in the output range. Please check that the sheet name matches exactly."
                st.error(sheet_name_error)
                st.info("In Google Sheets, check the tabs at the bottom of your spreadsheet to see the exact sheet names.")
                raise Exception(f"{sheet_name_error} Original error: {error_msg}")
            elif "not found" in error_msg.lower():
                access_error = "Error accessing Google Sheet. Please verify the Sheet ID is correct."
                st.error(access_error)
                raise Exception(f"{access_error} Original error: {error_msg}")
            elif "permission" in error_msg.lower() or "forbidden" in error_msg.lower():
                permission_error = "Error: Insufficient permissions to write to the sheet."
                st.error(permission_error)
                st.info(f"Make sure you've shared the sheet with EDITOR access to: {self.service_account_email}")
                raise Exception(f"{permission_error} Original error: {error_msg}")
            else:
                st.error(f"Error writing to Google Sheet: {error_msg}")
                raise Exception(f"Error writing to sheet: {error_msg}")
