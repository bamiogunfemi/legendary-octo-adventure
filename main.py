import streamlit as st
import pandas as pd
from google_sheet_client import GoogleSheetClient
from scoring_engine import ScoringEngine
from utils import parse_job_description, prepare_export_data
import json

def main():
    st.set_page_config(page_title="CV Evaluator", layout="wide")
    st.title("CV Evaluator")

    # Initialize components
    google_client = GoogleSheetClient()
    scoring_engine = ScoringEngine()

    # Sidebar for job description input
    st.sidebar.header("Job Description")
    jd_text = st.sidebar.text_area(
        "Enter Job Description",
        height=300,
        help="Enter the complete job description including role, required skills, experience, and certifications"
    )

    # Google Sheet input
    st.sidebar.header("CV Source")
    sheet_id = st.sidebar.text_input(
        "Google Sheet ID",
        help="Enter the ID from the Google Sheet URL"
    )
    sheet_range = st.sidebar.text_input(
        "Sheet Range",
        value="A1:Z1000",
        help="Enter the range of cells to process"
    )

    if st.sidebar.button("Evaluate CVs"):
        if not jd_text or not sheet_id:
            st.error("Please provide both job description and Google Sheet ID")
            return

        try:
            with st.spinner("Fetching CV data..."):
                # Parse job requirements
                job_requirements = parse_job_description(jd_text)
                st.sidebar.write("Parsed Job Requirements:", job_requirements)

                # Fetch CV data
                cv_data = google_client.get_sheet_data(sheet_id, sheet_range)

                if cv_data.empty:
                    st.error("No data found in the specified sheet range")
                    return

                # Process each CV
                results = []
                for _, row in cv_data.iterrows():
                    # Create CV dictionary with basic info
                    cv_dict = {
                        'name': str(row.get('Name', row.get('name', ''))).strip(),
                        'email': str(row.get('Email', row.get('email', ''))).strip(),
                        'current_role': str(row.get('Current Role', row.get('current_role', ''))).strip(),
                        'years_experience': str(row.get('Years of Experience', row.get('years_experience', 0))).strip(),
                        'skills': [],
                        'certifications': []
                    }

                    # Process skills
                    skills = row.get('Skills', row.get('skills', ''))
                    if isinstance(skills, str) and skills.strip():
                        cv_dict['skills'] = [s.strip() for s in skills.split(',') if s.strip()]

                    # Process certifications
                    certifications = row.get('Certifications', row.get('certifications', ''))
                    if isinstance(certifications, str) and certifications.strip():
                        cv_dict['certifications'] = [c.strip() for c in certifications.split(',') if c.strip()]

                    # Evaluate CV
                    result = scoring_engine.evaluate_cv(cv_dict, job_requirements)

                    # Combine basic info with evaluation results
                    evaluation = {
                        'name': cv_dict['name'],
                        'email': cv_dict['email'],
                        'current_role': cv_dict['current_role'],
                        'overall_score': result['overall_score'],
                        'skills_score': result['skills_score'],
                        'experience_score': result['experience_score'],
                        'alignment_score': result['alignment_score']
                    }

                    # Add reasons for not suitable candidates
                    if 'reasons' in result and result['reasons']:
                        evaluation['reasons_not_suitable'] = '\n'.join(result['reasons'])
                    else:
                        evaluation['reasons_not_suitable'] = ''

                    results.append(evaluation)

                # Prepare results for display
                results_df = prepare_export_data(results)

                # Display results
                st.header("Evaluation Results")

                # Summary metrics
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("Total CVs Processed", len(results))
                with col2:
                    suitable_count = len(results_df[results_df['status'] != 'Not Suitable'])
                    st.metric("Suitable Candidates", suitable_count)
                with col3:
                    avg_score = results_df['overall_score'].mean()
                    st.metric("Average Score", f"{avg_score:.2f}")

                # Detailed results table
                st.write("### Detailed Results")
                st.dataframe(
                    results_df,
                    column_config={
                        "name": "Name",
                        "email": "Email",
                        "current_role": "Current Role",
                        "overall_score": st.column_config.NumberColumn("Overall Score", format="%.2f"),
                        "status": "Status",
                        "reasons_not_suitable": st.column_config.TextColumn("Reasons (if not suitable)")
                    }
                )

                # Export option
                csv = results_df.to_csv(index=False)
                st.download_button(
                    label="Download Results CSV",
                    data=csv,
                    file_name="cv_evaluation_results.csv",
                    mime="text/csv"
                )

        except Exception as e:
            st.error(f"An error occurred: {str(e)}")

if __name__ == "__main__":
    main()