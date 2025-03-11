import pandas as pd
import streamlit as st
import re
from PyPDF2 import PdfReader
from datetime import datetime
import io
import requests
from docx import Document
import mimetypes
import os
import json
from google.oauth2.credentials import Credentials
from google.oauth2 import service_account
from googleapiclient.discovery import build

def get_google_drive_file_url(url):
    """Convert Google Drive share URL to direct download URL"""
    try:
        # Extract file ID from various Google Drive URL formats
        file_id = None

        # Handle direct export URLs first
        if 'uc?export=download&id=' in url:
            file_id = url.split('id=')[1].split('&')[0]
        # Handle web viewer URLs
        elif 'open?id=' in url:
            file_id = url.split('open?id=')[1].split('&')[0]
        elif '/file/d/' in url:
            file_id = url.split('/file/d/')[1].split('/')[0]
        elif 'id=' in url:
            file_id = url.split('id=')[1].split('&')[0]

        if not file_id:
            st.warning(f"Could not extract file ID from URL: {url}")
            return None

        # Return direct view URL instead of download URL
        return f"https://drive.google.com/file/d/{file_id}/view"
    except Exception as e:
        st.warning(f"Error processing Google Drive URL: {str(e)}")
        return None

def parse_document_for_experience(cv_url):
    """Parse PDF/DOC CV to extract first non-freelance experience date"""
    try:
        # Check if it's a Google Drive URL
        if not cv_url or not cv_url.strip():
            return None, None, "No CV URL provided"

        if 'drive.google.com' in cv_url:
            # Extract file ID and download content using Google Drive API
            if '/file/d/' in cv_url:
                file_id = cv_url.split('/file/d/')[1].split('/')[0]
            else:
                file_id = cv_url.split('id=')[1].split('&')[0]

            # Use the direct download API endpoint
            creds_json = os.getenv('GOOGLE_CREDENTIALS')
            if not creds_json:
                return None, None, "Google credentials not found"

            try:
                creds_dict = json.loads(creds_json)
                credentials = service_account.Credentials.from_service_account_info(
                    creds_dict, scopes=['https://www.googleapis.com/auth/drive.readonly']
                )

                # Build the Drive API service
                service = build('drive', 'v3', credentials=credentials)

                # Get the file using Drive API
                request = service.files().get_media(fileId=file_id)
                file_buffer = io.BytesIO()
                downloader = request.execute()
                file_buffer.write(downloader)
                file_buffer.seek(0)
                content = file_buffer.read()

            except json.JSONDecodeError:
                return None, None, "Invalid JSON format in Google credentials"
            except Exception as e:
                return None, None, f"Error accessing Google Drive: {str(e)}"

        else:
            # For non-Google Drive URLs
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                'Accept': 'application/pdf,application/msword,application/vnd.openxmlformats-officedocument.wordprocessingml.document'
            }
            try:
                response = requests.get(cv_url, headers=headers, verify=False)
                if response.status_code != 200:
                    return None, None, f"Failed to download file: Status {response.status_code}"
                content = response.content
            except Exception as e:
                return None, None, f"Download error: {str(e)}"

        # Check file signatures
        file_type = None
        if content.startswith(b'%PDF'):
            file_type = 'pdf'
        elif content.startswith(b'PK\x03\x04'):  # docx file signature
            file_type = 'doc'
        else:
            content_type = response.headers.get('content-type', '').lower() if 'response' in locals() else ''
            if 'pdf' in content_type:
                file_type = 'pdf'
            elif 'word' in content_type or 'msword' in content_type:
                file_type = 'doc'

        if not file_type:
            return None, None, "Unsupported file format"

        # Process the file
        file_content = io.BytesIO(content)
        text = ""

        try:
            if file_type == 'pdf':
                pdf_reader = PdfReader(file_content)
                for page in pdf_reader.pages:
                    text += page.extract_text()
            elif file_type == 'doc':
                doc = Document(file_content)
                for para in doc.paragraphs:
                    text += para.text + '\n'
        except Exception as e:
            return None, None, f"Error parsing {file_type.upper()} file: {str(e)}"

        if not text.strip():
            return None, None, "No text content found in document"

        # Get the first non-empty line
        first_line = None
        for line in text.split('\n'):
            if line.strip():
                first_line = line.strip()
                break

        if not first_line:
            first_line = "No readable content found"

        # Look for experience section and dates
        experience_patterns = [
            r"(?:Experience|Work History|Employment|Career History)",
            r"(\d{1,2}/\d{4})\s*[-–]\s*(?:Present|\d{1,2}/\d{4})",
            r"(\d{4})\s*[-–]\s*(?:Present|\d{4})"
        ]

        # Find first non-freelance role date
        lines = text.split('\n')
        current_section = ""
        for line in lines:
            # Check if this is the experience section
            if any(re.search(pattern, line, re.IGNORECASE) for pattern in [experience_patterns[0]]):
                current_section = "experience"
                continue

            if current_section == "experience":
                # Skip if it's a freelance role
                if re.search(r"freelance|contract", line, re.IGNORECASE):
                    continue

                # Look for date patterns
                for pattern in experience_patterns[1:]:
                    match = re.search(pattern, line)
                    if match:
                        date_str = match.group(1)
                        # Convert to datetime
                        try:
                            if '/' in date_str:
                                return datetime.strptime(date_str, '%m/%Y'), first_line, None
                            else:
                                return datetime.strptime(date_str, '%Y'), first_line, None
                        except ValueError:
                            continue

        return None, first_line, "No valid experience dates found"
    except Exception as e:
        return None, None, f"Error processing document: {str(e)}"

def calculate_years_experience(cv_url=None, start_date_str=None):
    """Calculate years of experience from CV or start date"""
    try:
        # Try to get start date from CV first
        if cv_url and cv_url.strip():
            start_date, first_line, error = parse_document_for_experience(cv_url)
            if start_date:
                years_exp = (datetime.now() - start_date).days / 365.25
                return round(years_exp, 1), first_line, None
            elif error:
                return 0, first_line, error

        # Fallback to start date from sheet
        if start_date_str and not pd.isna(start_date_str):
            try:
                start_date = pd.to_datetime(start_date_str)
                years_exp = (datetime.now() - start_date).days / 365.25
                return round(years_exp, 1), None, None
            except Exception as e:
                return 0, None, f"Invalid date format: {str(e)}"

        return 0, None, "No experience date provided"
    except Exception as e:
        return 0, None, f"Error calculating experience: {str(e)}"

def extract_skills_from_text(text):
    """Extract actual skills from descriptive text"""
    # Common prefixes to remove
    prefixes = [
        'proficient in', 'experience with', 'experience in',
        'knowledge of', 'hands-on experience with', 'expertise in',
        'background in', 'skilled in', 'understanding of'
    ]

    # Clean the text
    text = text.lower()
    for prefix in prefixes:
        if text.startswith(prefix):
            text = text[len(prefix):].strip()

    # Remove common suffixes
    text = re.sub(r'\s*\([^)]*\)', '', text)  # Remove parenthetical content
    text = re.sub(r'(?:^|\s)(?:and|&|,)\s*', ',', text)  # Convert connectors to commas

    # Split by commas and clean each part
    skills = [s.strip(' .,') for s in text.split(',')]
    return [s for s in skills if s and len(s) > 2]

def parse_job_description(jd_text, custom_years=None):
    """Parse job description text into structured format"""
    try:
        lines = jd_text.strip().split('\n')

        job_requirements = {
            'role': '',
            'required_skills': [],
            'nice_to_have_skills': [],
            'required_years': custom_years if custom_years is not None else 0
        }

        current_section = None
        in_requirements = False
        skills_section = False
        nice_to_have_section = False

        for line in lines:
            line = line.strip()
            if not line:
                continue

            lower_line = line.lower()

            # Role detection
            if 'about the role' in lower_line:
                # Get the next non-empty line as the role
                for next_line in lines[lines.index(line) + 1:]:
                    if next_line.strip():
                        job_requirements['role'] = next_line.strip()
                        st.sidebar.info(f"✅ Detected Role: {job_requirements['role']}")
                        break
                continue

            # Mark requirements sections
            if any(section in lower_line for section in ['about you', 'requirements', 'skills needed', 'technical skills']):
                in_requirements = True
                skills_section = True
                nice_to_have_section = False
                continue

            if 'nice to have' in lower_line:
                skills_section = False
                nice_to_have_section = True
                continue

            # Skills detection from bullet points or lists
            if line.startswith(('•', '-', '*', '→')):
                skill_line = line.lstrip('•-*→ \t').strip()

                if skills_section:  # Required skills section
                    extracted_skills = extract_skills_from_text(skill_line)
                    job_requirements['required_skills'].extend(extracted_skills)
                elif nice_to_have_section:  # Nice to have skills section
                    extracted_skills = extract_skills_from_text(skill_line)
                    job_requirements['nice_to_have_skills'].extend(extracted_skills)

        # Handle simple list format
        if not job_requirements['required_skills']:
            # Try to extract as a simple list of technologies
            all_text = ' '.join(lines)
            tech_list = re.findall(r'[A-Za-z0-9]+(?:\.[A-Za-z0-9]+)*', all_text)
            common_techs = {'python', 'java', 'javascript', 'golang', 'react', 'node', 'aws', 'gcp', 'azure',
                          'kubernetes', 'docker', 'terraform', 'jenkins', 'git', 'mongodb', 'postgresql',
                          'mysql', 'redis', 'elasticsearch', 'kafka', 'rabbitmq', 'graphql', 'rest'}
            tech_skills = [tech for tech in tech_list if tech.lower() in common_techs]
            job_requirements['required_skills'].extend(tech_skills)

        # Remove duplicates while preserving order
        job_requirements['required_skills'] = list(dict.fromkeys(job_requirements['required_skills']))
        job_requirements['nice_to_have_skills'] = list(dict.fromkeys(job_requirements['nice_to_have_skills']))

        # Default to "Backend Integration Engineer" if no role detected
        if not job_requirements['role'] and "backend integration engineer" in jd_text.lower():
            job_requirements['role'] = "Backend Integration Engineer"
            st.sidebar.info(f"✅ Detected Role: {job_requirements['role']}")

        # Show parsed skills
        if job_requirements['required_skills']:
            st.sidebar.info("✅ Required Skills:")
            for skill in job_requirements['required_skills']:
                st.sidebar.markdown(f"• {skill}")

        if job_requirements['nice_to_have_skills']:
            st.sidebar.info("✅ Nice to Have Skills:")
            for skill in job_requirements['nice_to_have_skills']:
                st.sidebar.markdown(f"• {skill}")

        return job_requirements

    except Exception as e:
        st.error(f"Error parsing job description: {str(e)}")
        return {
            'role': '',
            'required_skills': [],
            'nice_to_have_skills': [],
            'required_years': custom_years if custom_years is not None else 0
        }

def prepare_export_data(results):
    """Prepare evaluation results for CSV export"""
    export_df = pd.DataFrame(results)
    export_df = export_df.round(2)

    # Reorder columns to show candidate info first
    columns_order = [
        'name', 'email', 'cv_link', 'current_role', 'years_experience', 'skills',
        'overall_score', 'status',
        'skills_score', 'experience_score',
        'alignment_score', 'reasons_not_suitable', 'document_errors'
    ]

    # Create status column
    export_df['status'] = export_df['overall_score'].apply(
        lambda x: 'Highly Suitable' if x >= 80
        else 'Suitable' if x >= 60
        else 'Not Suitable'
    )

    # Ensure reasons are only shown for not suitable candidates
    if 'reasons_not_suitable' in export_df.columns:
        export_df.loc[export_df['status'] != 'Not Suitable', 'reasons_not_suitable'] = ''

    # Add a column for document parsing errors if not present
    if 'document_errors' not in export_df.columns:
        export_df['document_errors'] = ''

    # Ensure all columns are present and in the right order
    for col in columns_order:
        if col not in export_df.columns:
            export_df[col] = ''

    return export_df[columns_order]