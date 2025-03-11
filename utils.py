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
            'required_years': 0
        }

        current_section = None
        in_requirements = False
        skills_section = False

        for line in lines:
            line = line.strip()
            if not line:
                continue

            lower_line = line.lower()

            # Role detection - look for specific sections
            if 'about the role' in lower_line:
                # Get the next non-empty line as the role
                for next_line in lines[lines.index(line) + 1:]:
                    if next_line.strip():
                        job_requirements['role'] = next_line.strip()
                        st.sidebar.info(f"✅ Detected Role: {job_requirements['role']}")
                        break
                continue

            # Mark requirements section
            if 'about you' in lower_line:
                in_requirements = True
                continue

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

                    # Extract the actual skill
                    if 'proficient in' in skill_line.lower():
                        skill = skill_line.split('proficient in')[-1]
                    elif 'experience with' in skill_line.lower():
                        skill = skill_line.split('experience with')[-1]
                    elif 'experience in' in skill_line.lower():
                        skill = skill_line.split('experience in')[-1]
                    elif 'knowledge of' in skill_line.lower():
                        skill = skill_line.split('knowledge of')[-1]
                    else:
                        skill = skill_line

                    # Clean up the skill
                    skill = skill.strip(' .,')
                    if skill and len(skill) > 2:
                        job_requirements['required_skills'].append(skill)

        # Clean up skills list
        cleaned_skills = []
        for skill in job_requirements['required_skills']:
            # Remove parentheses and their contents
            skill = re.sub(r'\(.*?\)', '', skill)
            # Remove everything after period or comma
            skill = re.sub(r'[.,].*$', '', skill)
            skill = skill.strip()
            if skill and len(skill) > 2:  # Only add non-empty skills
                cleaned_skills.append(skill)

        job_requirements['required_skills'] = cleaned_skills

        # Default to "Backend Integration Engineer" if no role detected
        if not job_requirements['role'] and "backend integration engineer" in jd_text.lower():
            job_requirements['role'] = "Backend Integration Engineer"
            st.sidebar.info(f"✅ Detected Role: {job_requirements['role']}")

        # Allow custom years of experience override
        custom_years = st.sidebar.number_input(
            "Override required years of experience",
            min_value=0,
            max_value=20,
            value=job_requirements['required_years'],
            help="Set your preferred years of experience requirement"
        )
        if custom_years != job_requirements['required_years']:
            job_requirements['required_years'] = custom_years
            st.sidebar.info(f"✅ Updated Experience Requirement: {custom_years} years")

        # Show parsed requirements
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
            'required_years': 0
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