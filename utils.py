import pandas as pd
import streamlit as st

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

        for line in lines:
            line = line.strip()
            if not line:
                continue

            lower_line = line.lower()

            # Role detection
            if 'role:' in lower_line or 'position:' in lower_line or 'job title:' in lower_line:
                job_requirements['role'] = line.split(':', 1)[1].strip()
                st.sidebar.info(f"✅ Detected Role: {job_requirements['role']}")

            # Skills section detection
            elif any(keyword in lower_line for keyword in ['required skills:', 'technical skills:', 'key skills:']):
                current_section = 'skills'
                st.sidebar.info("✅ Processing Skills Section")

            # Experience detection
            elif any(keyword in lower_line for keyword in ['experience:', 'years of experience:', 'work experience:']):
                # Extract years using various formats
                numbers = ''.join(filter(str.isdigit, line))
                if numbers:
                    job_requirements['required_years'] = int(numbers)
                    st.sidebar.info(f"✅ Required Experience: {job_requirements['required_years']} years")

            # Certifications section detection
            elif any(keyword in lower_line for keyword in ['certifications:', 'certificates:', 'required certifications:']):
                current_section = 'certifications'
                st.sidebar.info("✅ Processing Certifications Section")

            # Process list items in current section
            elif line.startswith(('-', '•', '*', '→')):
                item = line.lstrip('- •*→').strip()
                if current_section == 'skills' and item:
                    job_requirements['required_skills'].append(item)
                elif current_section == 'certifications' and item:
                    job_requirements['required_certifications'].append(item)

        # Validation and feedback
        if not job_requirements['role']:
            st.sidebar.warning("⚠️ No role title detected")
        if not job_requirements['required_skills']:
            st.sidebar.warning("⚠️ No required skills detected")
        if not job_requirements['required_years']:
            st.sidebar.warning("⚠️ No years of experience requirement detected")

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