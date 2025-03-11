import streamlit as st
import pandas as pd
from google_sheet_client import GoogleSheetClient
from scoring_engine import ScoringEngine
from utils import parse_job_description, prepare_export_data, calculate_years_experience
from datetime import datetime

def calculate_years_experience(cv_url, start_date_str):
    """Calculate years of experience from start date"""
    try:
        if not start_date_str or pd.isna(start_date_str):
            return 0, ""
        start_date = pd.to_datetime(start_date_str)
        years_exp = (datetime.now() - start_date).days / 365.25
        return round(years_exp, 1), ""
    except Exception as e:
        return 0, str(e)

def main():
    st.set_page_config(page_title="CV Evaluator", layout="wide")
    st.title("CV Evaluator")

    # Initialize components
    google_client = GoogleSheetClient()
    scoring_engine = ScoringEngine()

    # Sidebar for job description input
    st.sidebar.header("Job Description")

    # Role input
    role = st.sidebar.text_input(
        "Role Title",
        value="Backend Integration Engineer",
        help="Enter the role title"
    )

    # Default job description
    default_jd = """About You
    • python
    • RESTful API.
    • webhooks.
    • AWS, GCP and Azure. 
    • ArgoCD, Kubernetes & docker.
    • postgres and mongodb.
    • testing 
    • Github Actions.


Nice to have
   • Golang 
   • including IaC (Terraform, CloudFormation).
    """

    jd_text = st.sidebar.text_area(
        "Enter Job Description",
        value=default_jd,
        height=300,
        help="Enter the complete job description including required skills and experience"
    )

    # Years of experience input before the evaluate button
    years_exp = st.sidebar.number_input(
        "Required Years of Experience",
        min_value=0,
        max_value=20,
        value=8,
        help="Set the minimum years of experience required"
    )

    # Google Sheet input
    st.sidebar.header("CV Source")
    sheet_id = st.sidebar.text_input(
        "Google Sheet ID",
        value="1IkWvsHfGW1iylm58LpYeWhsUDf30Mld5pF7WkpWlWxM",
        help="Enter the ID from the Google Sheet URL"
    )
    sheet_range = st.sidebar.text_input(
        "Sheet Range",
        value="A1:Z1000",
        help="Enter the range of cells to process"
    )

    if st.sidebar.button("Evaluate First 3 CVs"):
        if not jd_text or not sheet_id:
            st.error("Please provide both job description and Google Sheet ID")
            return

        try:
            with st.spinner("Fetching CV data..."):
                # Parse job requirements
                job_requirements = parse_job_description(jd_text, years_exp)
                job_requirements['role'] = role  # Override role with user input

                # Fetch CV data
                cv_data = google_client.get_sheet_data(sheet_id, sheet_range)

                if cv_data.empty:
                    st.error("No data found in the specified sheet range")
                    return

                # Process first 3 CVs only
                cv_data = cv_data.head(3)
                st.info(f"Processing first 3 CVs out of {len(cv_data)} total entries")

                # Process each CV
                results = []
                progress_bar = st.progress(0)

                for index, row in cv_data.iterrows():
                    # Update progress
                    progress = (index + 1) / len(cv_data)
                    progress_bar.progress(progress)

                    cv_link = str(row.get('UPLOAD YOUR CV HERE', '')).strip()
                    st.write(f"Processing CV {index + 1}: {row.get('FIRST NAME', '')} {row.get('LAST NAME', '')}")

                    # Calculate years of experience with error handling
                    years_exp, exp_error = calculate_years_experience(
                        cv_url=cv_link,
                        start_date_str=row.get('Experience Start Date', '')
                    )

                    # Create CV dictionary with basic info
                    cv_dict = {
                        'name': f"{str(row.get('FIRST NAME', '')).strip()} {str(row.get('LAST NAME', '')).strip()}",
                        'email': str(row.get('EMAIL', '')).strip(),
                        'cv_link': cv_link,
                        'years_experience': years_exp,
                        'skills': []
                    }

                    # Process skills from dedicated column
                    skills = row.get('Skills', '')
                    if isinstance(skills, str) and skills.strip():
                        cv_dict['skills'] = [s.strip() for s in skills.split(',') if s.strip()]

                    # Evaluate CV
                    result = scoring_engine.evaluate_cv(cv_dict, job_requirements)

                    # Combine basic info with evaluation results
                    evaluation = {
                        'name': cv_dict['name'],
                        'email': cv_dict['email'],
                        'cv_link': cv_dict['cv_link'],
                        'years_experience': years_exp,
                        'skills': ', '.join(cv_dict['skills']),
                        'overall_score': result['overall_score'],
                        'skills_score': result['skills_score'],
                        'experience_score': result['experience_score'],
                        'alignment_score': result['alignment_score'],
                        'document_errors': exp_error if exp_error else ''
                    }

                    # Add reasons for not suitable candidates
                    reasons = []
                    if exp_error:
                        reasons.append(f"CV Processing: {exp_error}")
                    if result['reasons']:
                        reasons.extend(result['reasons'])

                    evaluation['reasons_not_suitable'] = '\n'.join(reasons) if reasons else ''

                    results.append(evaluation)

                # Hide progress bar after completion
                progress_bar.empty()

                # Prepare results for display
                results_df = prepare_export_data(results)

                # Display results
                st.header("Evaluation Results")

                # Summary metrics
                col1, col2, col3, col4 = st.columns(4)
                with col1:
                    st.metric("CVs Processed", len(results))
                with col2:
                    suitable_count = len(results_df[results_df['status'] != 'Not Suitable'])
                    st.metric("Suitable Candidates", suitable_count)
                with col3:
                    avg_score = results_df['overall_score'].mean()
                    st.metric("Average Score", f"{avg_score:.2f}")
                with col4:
                    error_count = len(results_df[results_df['document_errors'].notna() & (results_df['document_errors'] != '')])
                    st.metric("CVs with Errors", error_count)

                # Detailed results table
                st.write("### Detailed Results")
                st.dataframe(
                    results_df,
                    column_config={
                        "name": "Name",
                        "email": "Email",
                        "cv_link": st.column_config.LinkColumn("CV Link"),
                        "years_experience": "Years of Experience",
                        "skills": "Skills",
                        "overall_score": st.column_config.NumberColumn("Overall Score", format="%.2f"),
                        "status": "Status",
                        "document_errors": "CV Processing Issues",
                        "reasons_not_suitable": st.column_config.TextColumn("Additional Reasons")
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