import streamlit as st
import pandas as pd
import time
from datetime import datetime
import re

from google_sheet_client import GoogleSheetClient
from nlp_matcher import NLPMatcher
from utils import get_google_drive_file_url, parse_document_for_experience, calculate_years_experience

def suggest_positions(technical_skills):
    """Suggest potential positions based on technical skills"""
    positions = set()  # Using set to avoid duplicates

    # Convert skills list to lowercase for matching
    skills = [skill.lower() for skill in technical_skills]

    # Backend Development
    if any(x in skills for x in ['python', 'java', 'nodejs', 'django', 'flask', 'fastapi', 'spring', 'express.js', 'nestjs']):
        if any(x in skills for x in ['postgresql', 'mongodb', 'mysql', 'database', 'typeorm', 'prisma']):
            positions.add("Back-End Developer")
            positions.add("Software Engineer")

    # Frontend Development
    if any(x in skills for x in ['react', 'angular', 'vue', 'javascript', 'typescript', 'html', 'css', 'nextjs']):
        positions.add("Front-End Developer")
        if any(x in skills for x in ['ui', 'ux', 'design']):
            positions.add("UI Developer")

    # Full Stack
    if any(x in skills for x in ['react', 'angular', 'vue', 'nextjs']) and \
       any(x in skills for x in ['python', 'nodejs', 'java', 'express.js', 'nestjs']):
        positions.add("Full Stack Developer")
        positions.add("Software Engineer")

    # DevOps/Cloud/Platform
    if any(x in skills for x in ['aws', 'azure', 'gcp', 'kubernetes', 'docker', 'terraform', 'ci/cd']):
        positions.add("DevOps Engineer")
        positions.add("Cloud Engineer")
        positions.add("Platform Engineer")
        if 'kubernetes' in skills:
            positions.add("Site Reliability Engineer")

    # Security Engineering
    if any(x in skills for x in ['security', 'oauth2', 'jwt', 'authentication', 'authorization', 'rbac']):
        positions.add("Security Engineer")
        positions.add("Application Security Engineer")
        if any(x in skills for x in ['aws', 'azure', 'gcp']):
            positions.add("Cloud Security Engineer")

    # API/Integration/Architecture
    if any(x in skills for x in ['rest', 'api', 'graphql', 'grpc', 'microservices', 'event-driven']):
        positions.add("API Integration Engineer")
        if 'microservices' in skills or 'event-driven' in skills:
            positions.add("Software Architect")
            positions.add("Solutions Architect")

    # Mobile Development
    if 'react native' in skills:
        positions.add("Mobile Developer")
        positions.add("React Native Developer")
    if 'android' in skills or 'kotlin' in skills:
        positions.add("Android Developer")
    if 'ios' in skills or 'swift' in skills:
        positions.add("iOS Developer")

    # WordPress and CMS Development
    if any(x in skills for x in ['wordpress', 'wp', 'woocommerce', 'elementor']):
        positions.add("WordPress Developer")
        positions.add("CMS Developer")
        if 'php' in skills:
            positions.add("PHP Developer")
        if any(x in skills for x in ['theme', 'plugin']):
            positions.add("WordPress Theme Developer")
            positions.add("WordPress Plugin Developer")
    
    # Design-related roles
    if any(x in skills for x in ['ui', 'ux', 'user interface', 'user experience', 'figma', 'sketch', 'adobe xd']):
        positions.add("UI/UX Designer")
        positions.add("User Experience Designer")
        positions.add("User Interface Designer")
        
    if any(x in skills for x in ['photoshop', 'illustrator', 'indesign', 'adobe creative suite']):
        positions.add("Graphic Designer")
        
    if any(x in skills for x in ['ui', 'ux', 'design']) and any(x in skills for x in ['html', 'css', 'sass', 'less']):
        positions.add("UI Developer")
        positions.add("Front-End Designer")
    
    # Web Design specific roles
    if any(x in skills for x in ['web design', 'responsive design', 'mobile design']):
        positions.add("Web Designer")
    
    # If Webflow, Wix, or similar tools are mentioned
    if any(x in skills for x in ['webflow', 'wix', 'squarespace', 'shopify']):
        positions.add("No-Code Developer")
        positions.add("Web Designer")

    # Emerging Tech
    if 'web3' in skills or 'blockchain' in skills:
        positions.add("Blockchain Developer")
        positions.add("Web3 Developer")
    if any(x in skills for x in ['serverless', 'lambda']):
        positions.add("Serverless Developer")
        positions.add("Cloud Developer")

    return sorted(list(positions)) if positions else ["Entry Level Developer"]

def process_mastersheet(sheet_id, sheet_range, output_range, include_headers=True):
    """
    Process a large mastersheet and extract skills, suggested roles, and calculated years of experience
    Then update the original sheet with this information
    
    Args:
        sheet_id: Google Sheet ID
        sheet_range: Range to read from (e.g., 'mastersheet!A1:Z2000')
        output_range: Range where results will be written (e.g., 'mastersheet!AA1')
        include_headers: Whether to include header/title row in the output (default: True)
    """
    print("Starting process_mastersheet function")
    # Header was moved from here to main.py tab2
    
    try:
        # Initialize components
        google_client = GoogleSheetClient()
        nlp_matcher = NLPMatcher()
        
        # Fetch data from mastersheet
        with st.spinner("Fetching data from mastersheet..."):
            data = google_client.get_sheet_data(sheet_id, sheet_range)
            
            if data.empty:
                st.error("No data found in the specified sheet range")
                return
            
            st.success(f"Loaded {len(data)} rows from mastersheet")
            st.write("Sample data (first 5 rows):")
            st.dataframe(data.head(5))
        
        # Process each CV
        # Set up progress tracking
        total_cvs = len(data)
        progress_bar = st.progress(0)
        progress_text = st.empty()
        processed_counter = st.empty()
        current_status = st.empty()
        
        # Create empty columns for results if they don't exist
        for col in ['Extracted Skills', 'Suggested Roles', 'Calculated YOE', 'Processing Reason']:
            if col not in data.columns:
                data[col] = None
        
        # Count all rows to process
        rows_to_process = len(data)
        st.info(f"Processing all {rows_to_process} rows, regardless of current 'Extracted Skills' value")
        
        # Reset counters for actual processing
        processed_count = 0
        
        for index, row in data.iterrows():
                
            # Update progress indicators
            processed_count += 1
            progress = processed_count / rows_to_process if rows_to_process > 0 else 0
            progress_bar.progress(progress)
            progress_text.text(f"Processing CV {processed_count} of {rows_to_process} (row {index + 1})")
            processed_counter.text(f"Processed: {processed_count} / {rows_to_process}")
            
            # Display available columns for debugging (only for the first row)
            if processed_count == 1:
                print(f"Available columns in row: {list(row.keys())}")
                st.info(f"Available columns in the sheet: {list(row.keys())}")
                
            # Use column index/letter instead of column name
            # First, check if the user wants to specify a specific CV column
            cv_column_index = None
            
            # Check if output range is specified with a column letter and row number
            match = re.search(r'([A-Z]+)(\d+)', output_range)
            if match:
                try:
                    # Get the column letter from the output range
                    output_col_letter = match.group(1)
                    
                    # For CV column, we'll use a fixed offset from output column
                    # If output column is H, we'll use D for CV by default (4 columns earlier)
                    # This can be easily modified later based on user feedback
                    
                    # Convert output column letter to index
                    output_col_index = 0
                    for char in output_col_letter.upper():
                        output_col_index = output_col_index * 26 + (ord(char) - ord('A'))
                    
                    # User specified that CV links are in column G
                    cv_column_index = 6  # Column G (index 6, since 0-based)
                    
                    # Show which column is being used for CV links
                    if processed_count == 1:
                        cv_col_letter = chr(cv_column_index + ord('A'))
                        st.info(f"Looking for CV links in column {cv_col_letter} (index {cv_column_index})")
                except Exception as e:
                    print(f"Error parsing column letter: {str(e)}")
                    # Default to column D (index 3) if there's an error
                    cv_column_index = 3
                    if processed_count == 1:
                        st.info("Using default column D for CV links")
                    
            # Direct column letter approach - get CV from column
            cv_link = ''
            matched_col = None
            
            # First try with the specified index if available
            if cv_column_index is not None and cv_column_index < len(row):
                cv_link = str(row.iloc[cv_column_index]).strip()
                matched_col = f"Column {chr(cv_column_index + ord('A'))}"
                print(f"Trying CV link from column index {cv_column_index} (Column G): '{cv_link}'")
                
                # For rows that start at high numbers, the values might just be empty strings
                # This is a problem especially with Cleaned Data!A3000:Z5900 ranges
                if not cv_link or cv_link == 'nan':
                    # Try to access the column by its name if named columns exist
                    try:
                        if 'G' in row.index:
                            cv_link = str(row['G']).strip()
                            matched_col = "Column G (by name)"
                            print(f"Using column G by name: '{cv_link}'")
                    except Exception as e:
                        print(f"Error accessing column G by name: {str(e)}")
                        
                    # If still no CV link found, try direct array access instead of DataFrame methods
                    # This is a more direct approach when DataFrame indexing is confusing
                    if not cv_link or cv_link == 'nan':
                        try:
                            raw_values = row.values
                            if len(raw_values) > 6:  # If we have at least 7 columns (G is at index 6)
                                cv_link = str(raw_values[6]).strip()
                                matched_col = "Column G (raw array index 6)"
                                print(f"Using raw array access for column G: '{cv_link}'")
                        except Exception as e:
                            print(f"Error with raw array access: {str(e)}")
                
            # If no link found with specified index, try the old column name approach as fallback
            if not cv_link:
                cv_link_cols = [
                    'UPLOAD YOUR CV HERE', 'CV Link', 'cv link', 'CV URL', 'Resume Link', 
                    'resume link', 'CV', 'Resume', 'Upload CV', 'Upload Your CV', 'CV/Resume', 
                    'CV/Resume Link', 'Attachment', 'Document'
                ]
                
                for col in cv_link_cols:
                    if col in row and row[col]:
                        cv_link = str(row[col]).strip()
                        matched_col = col
                        if cv_link:  # If we found a non-empty link, use it
                            break
            
            if cv_link:
                # Check if it's a valid CV link (not just any text)
                is_valid_link = cv_link.startswith('http') and ('drive.google.com' in cv_link or 'docs.google.com' in cv_link)
                
                if not is_valid_link:
                    reason = f"Found text in CV column but it's not a valid link: '{cv_link[:30]}...'"
                    current_status.text(reason)
                    data.at[index, 'Extracted Skills'] = "Error: Invalid link format"
                    data.at[index, 'Suggested Roles'] = "Error: Invalid link format"
                    data.at[index, 'Processing Reason'] = reason
                    continue
                
                current_status.text(f"Processing CV link from column '{matched_col}': {cv_link}")
                try:
                    # Calculate years of experience and get CV content
                    years_exp, _, cv_content = calculate_years_experience(cv_url=cv_link)
                    
                    # Extract skills
                    current_status.text(f"Extracting skills from CV...")
                    if cv_content:
                        # Check if content was actually obtained (not just whitespace)
                        if cv_content.strip():
                            technical_skills = nlp_matcher.extract_technical_skills(cv_content)
                            
                            if technical_skills:
                                # Calculate suggested roles
                                suggested_positions = suggest_positions(technical_skills)
                                
                                # Update the dataframe with extracted information
                                data.at[index, 'Extracted Skills'] = ", ".join(technical_skills)
                                data.at[index, 'Suggested Roles'] = ", ".join(suggested_positions) if suggested_positions else "None"
                                data.at[index, 'Calculated YOE'] = float(years_exp) if years_exp is not None else None
                                data.at[index, 'Processing Reason'] = "Successfully processed"
                            else:
                                reason = "CV content found but no technical skills detected"
                                data.at[index, 'Extracted Skills'] = "None"
                                data.at[index, 'Suggested Roles'] = "None" 
                                data.at[index, 'Processing Reason'] = reason
                        else:
                            reason = "CV content was empty or whitespace only"
                            data.at[index, 'Extracted Skills'] = "None"
                            data.at[index, 'Suggested Roles'] = "None"
                            data.at[index, 'Processing Reason'] = reason
                    else:
                        reason = "Could not extract content from CV file"
                        data.at[index, 'Extracted Skills'] = "None"
                        data.at[index, 'Suggested Roles'] = "None" 
                        data.at[index, 'Processing Reason'] = reason
                except Exception as e:
                    error_msg = str(e)
                    reason = f"Error: {error_msg[:100]}"
                    current_status.text(f"Error processing CV: {reason}")
                    data.at[index, 'Extracted Skills'] = "None"
                    data.at[index, 'Suggested Roles'] = "None"
                    data.at[index, 'Processing Reason'] = reason
            else:
                # If we have reached this point, no CV link column was found or the value was empty
                if processed_count == 1:
                    # Show a helpful message about column names we're looking for
                    st.warning(f"""
                    No CV link column found. The system looks for these column names:
                    {', '.join(cv_link_cols)}
                    
                    Available columns in your sheet: {list(row.keys())}
                    """)
                
                reason = "No CV link found in this row"
                current_status.text(reason)
                data.at[index, 'Extracted Skills'] = "None"
                data.at[index, 'Suggested Roles'] = "None"
                data.at[index, 'Processing Reason'] = reason
            
            # Add a small delay to avoid rate limits
            time.sleep(0.1)
        
        # Clear progress indicators
        progress_bar.empty()
        progress_text.empty()
        processed_counter.empty()
        current_status.empty()
        
        # Display processed data
        st.subheader("Processed Data")
        st.dataframe(data)
        
        # Save back to Google Sheet
        try:
            st.subheader("Saving Results")
            with st.spinner("Updating Google Sheet with extracted information..."):
                # Determine columns to write back
                columns_to_update = ['Extracted Skills', 'Suggested Roles', 'Calculated YOE', 'Processing Reason']
                update_df = data[columns_to_update]
                
                # Show user whether headers will be included
                if include_headers:
                    st.info("Including headers/titles in the output")
                else:
                    st.info("Skipping headers/titles in the output (as specified)")
                
                # Hack: For custom header handling when the write_to_sheet doesn't respect include_headers directly
                # We'll manipulate the output range if headers should be skipped
                actual_output_range = output_range
                if not include_headers:
                    # Extract the sheet name and starting cell from the output range
                    match = re.search(r'([^!]+)!([A-Z]+)(\d+)', output_range)
                    if match:
                        sheet_name = match.group(1)
                        col_letter = match.group(2)
                        row_num = int(match.group(3))
                        
                        # If we're modifying row 1, we need a special indicator
                        if row_num == 1:
                            # Append a special parameter that will be detected in google_sheet_client.py
                            actual_output_range = f"{sheet_name}!{col_letter}{row_num}_NOHEADER"
                
                # Write to Google Sheet
                google_client.write_to_sheet(sheet_id, actual_output_range, update_df)
                st.success("Successfully updated the mastersheet with extracted information!")
                
                # Offer download of processed data
                csv = data.to_csv(index=False)
                st.download_button(
                    label="Download Processed Data as CSV",
                    data=csv,
                    file_name="mastersheet_processed.csv",
                    mime="text/csv"
                )
        except Exception as e:
            st.error(f"Failed to update mastersheet: {str(e)}")
            st.info("Make sure you've shared your sheet with edit permissions to the Service Account Email.")
            
    except Exception as e:
        st.error(f"An error occurred during mastersheet processing: {str(e)}")
