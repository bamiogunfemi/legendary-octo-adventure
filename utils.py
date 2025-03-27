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
import dateparser

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
    """Parse PDF/DOC CV to extract first professional experience date and text content"""
    try:
        if not cv_url or not cv_url.strip():
            return None, None, "No CV URL provided"

        if 'drive.google.com' in cv_url:
            # Handle Google Drive files
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

                # Get the file metadata first
                file_metadata = service.files().get(fileId=file_id, fields='mimeType').execute()
                mime_type = file_metadata.get('mimeType', '')

                # Get the file content
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

        # Process the file based on type
        text = ""
        try:
            # Check if it's a PDF
            if content.startswith(b'%PDF'):
                pdf_reader = PdfReader(io.BytesIO(content))
                for page in pdf_reader.pages:
                    page_text = page.extract_text()
                    if page_text:
                        # Clean up text: remove extra whitespace and normalize line breaks
                        page_text = re.sub(r'\s+', ' ', page_text)
                        page_text = page_text.replace('\n\n', '\n').strip()
                        text += page_text + "\n"
            # Check if it's a DOCX
            elif content.startswith(b'PK\x03\x04'):
                doc = Document(io.BytesIO(content))
                for para in doc.paragraphs:
                    text += para.text + "\n"
            else:
                return None, None, "Unsupported file format"

            # Clean up text
            text = re.sub(r'\s+', ' ', text)  # Normalize whitespace
            text = text.replace('•', '\n•')  # Preserve bullet points
            text = re.sub(r'([.!?])\s*', r'\1\n', text)  # Split sentences
            text = re.sub(r'\n\s*\n', '\n', text)  # Remove empty lines
            text = text.strip()

            if not text:
                return None, None, "No text content found in document"

            # Get the first non-empty line
            first_line = None
            lines = text.split('\n')
            for line in lines:
                if line.strip():
                    first_line = line.strip()
                    break

            if not first_line:
                return None, None, "No readable content found"

            return None, first_line, text

        except Exception as e:
            return None, None, f"Error processing document: {str(e)}"

    except Exception as e:
        return None, None, f"Error processing document: {str(e)}"

def calculate_years_experience(cv_url=None, start_date_str=None):
    """Calculate years of experience from CV or start date"""
    try:
        # Try to get experience from CV content first
        if cv_url and cv_url.strip():
            try:
                # Parse CV content
                _, first_line, cv_content = parse_document_for_experience(cv_url)

                if not cv_content:
                    return 0, None, "No CV content available"

                # Define exclusion patterns for non-professional positions
                exclusion_patterns = [
                    r'freelance', r'freelancing', r'education',
                    r'university', r'college', r'school',
                    r'certificate', r'certification', r'training',
                    r'intern', r'internship', r'student',
                    r'hons\.?', r'b\.?sc\.?', r'bachelor',
                    r'm\.?sc\.?', r'master', r'ph\.?d\.?'
                ]
                exclusion_pattern = '|'.join(exclusion_patterns)

                # Define experience section keywords
                exp_keywords = [
                    'experience', 'work history', 'employment',
                    'professional background', 'career',
                    'work experience', 'professional experience'
                ]

                # Look for experience sections and dates
                cv_text = cv_content.lower()
                earliest_date = None
                current_section = ""
                in_education_section = False

                for line in cv_text.split('\n'):
                    line = line.strip()

                    # Skip empty lines
                    if not line:
                        continue

                    # Check if we're entering an education section
                    if re.search(r'education|qualifications|academic|degree|university|college', line.lower()):
                        in_education_section = True
                        continue

                    # Check if we're in an experience section
                    if any(keyword in line for keyword in exp_keywords):
                        current_section = "experience"
                        in_education_section = False
                        continue

                    # Skip if not in experience section or if in education section
                    if current_section != "experience" or in_education_section:
                        continue

                    # Skip non-professional positions
                    if re.search(exclusion_pattern, line.lower()):
                        continue

                    # Extract dates using various patterns
                    date_patterns = [
                        r'(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|Jul(?:y)?|Aug(?:ust)?|Sep(?:tember)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)[,\s]+\d{4}',
                        r'\d{1,2}/\d{4}',
                        r'\d{1,2}-\d{4}',
                        r'(?:19|20)\d{2}'  # Year pattern limited to reasonable range
                    ]

                    for pattern in date_patterns:
                        matches = re.finditer(pattern, line)
                        for match in matches:
                            date_str = match.group(0)
                            parsed_date = dateparser.parse(date_str)
                            if parsed_date:
                                # Additional check to ensure we're not in an academic context
                                if not any(academic_term in line.lower() for academic_term in [
                                    'graduated', 'degree', 'diploma', 'thesis', 'dissertation',
                                    'academic', 'studied', 'completed', 'coursework'
                                ]):
                                    if not earliest_date or parsed_date < earliest_date:
                                        earliest_date = parsed_date

                if earliest_date:
                    # Calculate years from earliest date to 2025
                    target_date = datetime(2025, 3, 12)  # Current date (2025)
                    years_exp = (target_date - earliest_date).days / 365.25
                    return round(years_exp, 1), first_line, cv_content

            except Exception as e:
                return 0, None, f"Error processing CV: {str(e)}"

        # Fallback to start date from sheet
        if start_date_str and not pd.isna(start_date_str):
            try:
                start_date = pd.to_datetime(start_date_str)
                target_date = datetime(2025, 3, 12)  # Current date (2025)
                years_exp = (target_date - start_date).days / 365.25
                return round(years_exp, 1), None, None
            except Exception as e:
                return 0, None, f"Invalid date format: {str(e)}"

        return 0, None, "No valid professional experience dates found"
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
    export_df = export_df.round(1)

    # Reorder columns to show candidate info first
    columns_order = [
        'name', 'email', 'cv_link', 'first_line', 'years_experience',
        'required_skills', 'nice_to_have_skills', 'missing_skills',
        'overall_score', 'document_errors', 'notes', 'reasons_not_suitable'
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
