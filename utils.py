import pandas as pd
import streamlit as st
import re

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
        'name', 'email', 'years_experience',
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

    return export_df[columns_order]