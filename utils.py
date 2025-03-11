import pandas as pd
import streamlit as st
import re
from PyPDF2 import PdfReader
from datetime import datetime
import io
import requests
from docx import Document
import mimetypes

def parse_document_for_experience(cv_url):
    """Parse PDF/DOC CV to extract first non-freelance experience date"""
    try:
        # Download file with redirects
        response = requests.get(cv_url, allow_redirects=True, verify=False)
        if response.status_code != 200:
            st.warning(f"Could not download file from URL: {cv_url}")
            return None

        # Get filename from content-disposition header or URL
        content_disp = response.headers.get('content-disposition')
        if content_disp:
            fname = re.findall("filename=(.+)", content_disp)[0]
        else:
            fname = cv_url.split('/')[-1]

        # Determine file type from filename or content
        file_type = None
        if fname.lower().endswith('.pdf'):
            file_type = 'pdf'
        elif fname.lower().endswith(('.doc', '.docx')):
            file_type = 'doc'
        else:
            # Try to determine from content
            content_type = response.headers.get('content-type', '').lower()
            if 'pdf' in content_type:
                file_type = 'pdf'
            elif 'word' in content_type or 'msword' in content_type:
                file_type = 'doc'

        if not file_type:
            st.warning(f"Could not determine file type for: {fname}")
            return None

        # Extract text based on file type
        file_content = io.BytesIO(response.content)
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
            st.warning(f"Error parsing {file_type.upper()} file: {str(e)}")
            return None

        if not text.strip():
            st.warning("No text content found in the document")
            return None

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
                                return datetime.strptime(date_str, '%m/%Y')
                            else:
                                return datetime.strptime(date_str, '%Y')
                        except ValueError:
                            continue

        return None
    except Exception as e:
        st.warning(f"Error processing document: {str(e)}")
        return None

def calculate_years_experience(cv_url=None, start_date_str=None):
    """Calculate years of experience from CV or start date"""
    try:
        # Try to get start date from CV first
        if cv_url and cv_url.strip():
            start_date = parse_document_for_experience(cv_url)
            if start_date:
                years_exp = (datetime.now() - start_date).days / 365.25
                return round(years_exp, 1)

        # Fallback to start date from sheet
        if start_date_str and not pd.isna(start_date_str):
            start_date = pd.to_datetime(start_date_str)
            years_exp = (datetime.now() - start_date).days / 365.25
            return round(years_exp, 1)

        return 0
    except Exception as e:
        st.warning(f"Error calculating experience: {str(e)}")
        return 0

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
        'name', 'email', 'cv_link', 'years_experience', 'skills',
        'overall_score', 'status',
        'skills_score', 'experience_score',
        'alignment_score', 'reasons_not_suitable'
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

    # Reorder columns and fill any missing columns with empty strings
    for col in columns_order:
        if col not in export_df.columns:
            export_df[col] = ''

    #Update years_experience column using new function
    export_df['years_experience'] = export_df['cv_link'].apply(calculate_years_experience)

    return export_df[columns_order]