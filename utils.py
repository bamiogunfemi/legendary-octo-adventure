import pandas as pd
import streamlit as st
import re

def parse_job_description(jd_text):
    """Parse job description text into structured format"""
    try:
        lines = jd_text.strip().split('\n')

        job_requirements = {
            'role': '',
            'required_skills': [],
            'required_years': 0,
            'required_certifications': [],
            'education_requirement': '',
        }

        current_section = None
        in_requirements = False

        for line in lines:
            line = line.strip()
            if not line:
                continue

            lower_line = line.lower()

            # Role detection - look for specific sections
            if 'about the role' in lower_line:
                in_requirements = True
                continue
            elif any(x in lower_line for x in ['about you', 'requirements:', 'qualifications:']):
                in_requirements = True
                continue
            elif lower_line.endswith('role') or lower_line.endswith('position'):
                next_line_idx = lines.index(line) + 1
                if next_line_idx < len(lines):
                    job_requirements['role'] = lines[next_line_idx].strip()
                    st.sidebar.info(f"✅ Detected Role: {job_requirements['role']}")

            # Experience detection
            if in_requirements:
                # Look for years of experience patterns
                year_patterns = [
                    r'(\d+)\+?\s*(?:years?|yrs?)',
                    r'(\d+)\s*\+\s*years?',
                    r'minimum\s*(?:of\s*)?(\d+)\s*years?'
                ]

                for pattern in year_patterns:
                    match = re.search(pattern, lower_line, re.IGNORECASE)
                    if match:
                        years = int(match.group(1))
                        if years > job_requirements['required_years']:
                            job_requirements['required_years'] = years
                            st.sidebar.info(f"✅ Required Experience: {years} years")

                # Skills detection from bullet points
                if line.startswith(('•', '-', '*', '→')):
                    skill_line = line.lstrip('•-*→ \t').strip()
                    # Check if it's a skill-related bullet point
                    if any(tech_word in skill_line.lower() for tech_word in [
                        'experience', 'proficient', 'knowledge', 'understanding',
                        'expertise', 'skill', 'hands-on', 'background'
                    ]):
                        # Extract the actual skill
                        skill = skill_line.split('in')[-1].strip() if 'in' in skill_line else skill_line
                        job_requirements['required_skills'].append(skill)

        # Additional processing for skills
        # Clean up skills that might have trailing punctuation or common phrases
        cleaned_skills = []
        for skill in job_requirements['required_skills']:
            # Remove common phrases and clean up
            skill = re.sub(r'\(.*?\)', '', skill)  # Remove parentheses and their contents
            skill = re.sub(r'[.,].*$', '', skill)  # Remove everything after period or comma
            skill = skill.strip()
            if skill and len(skill) > 2:  # Only add non-empty skills
                cleaned_skills.append(skill)

        job_requirements['required_skills'] = cleaned_skills

        # Validation and feedback
        if not job_requirements['role']:
            st.sidebar.warning("⚠️ No role title detected")
        if not job_requirements['required_skills']:
            st.sidebar.warning("⚠️ No required skills detected")
        if not job_requirements['required_years']:
            st.sidebar.warning("⚠️ No years of experience requirement detected")

        # Show parsed skills
        if job_requirements['required_skills']:
            st.sidebar.info("✅ Detected Skills:")
            for skill in job_requirements['required_skills']:
                st.sidebar.markdown(f"• {skill}")

        return job_requirements

    except Exception as e:
        st.error(f"Error parsing job description: {str(e)}")
        return {
            'role': '',
            'required_skills': [],
            'required_years': 0,
            'required_certifications': [],
            'education_requirement': '',
        }

def prepare_export_data(results):
    """Prepare evaluation results for CSV export"""
    export_df = pd.DataFrame(results)
    export_df = export_df.round(2)

    # Reorder columns to show candidate info first
    columns_order = [
        'name', 'email', 'current_role',
        'overall_score', 'status',
        'skills_score', 'experience_score', 
        'education_score', 'certification_score',
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