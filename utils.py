import pandas as pd
import streamlit as st
import re
from PyPDF2 import PdfReader
from datetime import datetime
import io
import requests
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

        st.write(f"Extracted Google Drive file ID: {file_id}")
        download_url = f"https://drive.google.com/uc?export=download&id={file_id}"
        st.write(f"Generated download URL: {download_url}")
        return download_url
    except Exception as e:
        st.warning(f"Error processing Google Drive URL: {str(e)}")
        return None

def parse_document_for_experience(cv_url):
    """Parse PDF/DOC CV to extract content and first non-freelance experience date"""
    try:
        if not cv_url or not cv_url.strip():
            return None, None, "No CV URL provided"

        st.write("Processing CV URL:", cv_url)

        # Convert Google Drive URL if needed
        original_url = cv_url
        if 'drive.google.com' in cv_url:
            cv_url = get_google_drive_file_url(cv_url)
            if not cv_url:
                return None, None, f"Could not process Google Drive URL: {original_url}"
            st.write("Using converted Google Drive URL:", cv_url)

        # For local testing, try to read from attached_assets
        content = None
        try:
            local_path = cv_url
            if not cv_url.startswith('attached_assets/'):
                local_path = os.path.join('attached_assets', os.path.basename(cv_url))

            st.write(f"Looking for PDF at path: {local_path}")
            if os.path.exists(local_path):
                st.write(f"✅ Found file at {local_path}")
                with open(local_path, 'rb') as file:
                    content = file.read()
                st.write(f"Successfully read {len(content)} bytes from local file")
            else:
                st.write("Local file not found, attempting download...")
                # Try as URL
                headers = {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
                }
                response = requests.get(cv_url, headers=headers, verify=False)

                # Log response details
                st.write(f"Download response status: {response.status_code}")
                st.write("Response headers:", response.headers.get('content-type', 'No content-type'))

                if response.status_code != 200:
                    return None, None, f"Failed to download file: Status {response.status_code}"

                content = response.content
                st.write(f"Downloaded {len(content)} bytes")

                # Check content type
                content_type = response.headers.get('content-type', '').lower()
                if 'pdf' not in content_type and not content.startswith(b'%PDF'):
                    st.error(f"Invalid content type: {content_type}")
                    return None, None, f"Downloaded file is not a PDF (content-type: {content_type})"

        except Exception as e:
            st.error(f"File access error: {str(e)}")
            return None, None, f"File access error: {str(e)}"

        # Process PDF content
        text = ""
        try:
            if not content:
                return None, None, "No content received from file"

            st.write("\nAttempting to parse PDF content...")

            # Validate PDF content
            if not content.startswith(b'%PDF'):
                st.error("File does not start with PDF signature")
                return None, None, "Invalid PDF format - missing PDF signature"

            pdf_reader = PdfReader(io.BytesIO(content))
            st.write(f"PDF has {len(pdf_reader.pages)} pages")
            total_chars = 0

            for page_num, page in enumerate(pdf_reader.pages, 1):
                try:
                    page_text = page.extract_text()
                    if page_text:
                        text += page_text + "\n"
                        total_chars += len(page_text)
                        st.write(f"Page {page_num}: Successfully extracted {len(page_text)} characters")
                    else:
                        st.warning(f"Page {page_num}: No text extracted")
                except Exception as e:
                    st.error(f"Error extracting text from page {page_num}: {str(e)}")

            st.write(f"\nTotal characters extracted from PDF: {total_chars}")

            if not text.strip():
                st.error("No text content could be extracted from PDF")
                return None, None, "No text content could be extracted from PDF"

            # Create the CV content with prefix
            cv_content = f"CV Content: {text}"

            # Get the first non-empty line
            first_line = None
            for line in text.split('\n'):
                if line.strip():
                    first_line = line.strip()
                    st.write("\nFirst Line:", first_line)
                    break

            st.write("\nSuccessfully extracted CV content")
            return None, first_line, cv_content

        except Exception as e:
            st.error(f"Error processing document content: {str(e)}")
            return None, None, f"Error processing document: {str(e)}"

    except Exception as e:
        st.error(f"Error in parse_document_for_experience: {str(e)}")
        return None, None, f"Error processing document: {str(e)}"

def calculate_years_experience(cv_url=None, start_date_str=None):
    """Calculate years of experience from CV or start date"""
    try:
        # Try to get start date from CV first
        if cv_url and cv_url.strip():
            st.write("Calculating experience from CV:", cv_url)
            start_date, first_line, cv_text = parse_document_for_experience(cv_url)

            if start_date:
                years_exp = (datetime.now() - start_date).days / 365.25
                st.write(f"Calculated {years_exp:.1f} years of experience")
                return round(years_exp, 1), first_line, cv_text
            elif cv_text and "CV Content:" in cv_text:
                # Even if no date found, return the CV text for skill analysis
                return 0, first_line, cv_text

        # Fallback to start date from sheet
        if start_date_str and not pd.isna(start_date_str):
            try:
                start_date = pd.to_datetime(start_date_str)
                years_exp = (datetime.now() - start_date).days / 365.25
                return round(years_exp, 1), None, None
            except Exception as e:
                return 0, None, f"Invalid date format: {str(e)}"

        return 0, None, "No valid experience date or CV content found"
    except Exception as e:
        st.error(f"Error calculating experience: {str(e)}")
        return 0, None, str(e)

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