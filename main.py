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
                    cv_dict = row.to_dict()

                    # Safely convert skills and certifications to lists
                    skills = cv_dict.get('skills', '')
                    certifications = cv_dict.get('certifications', '')

                    cv_dict['skills'] = [s.strip() for s in str(skills).split(',') if s.strip()] if skills else []
                    cv_dict['certifications'] = [c.strip() for c in str(certifications).split(',') if c.strip()] if certifications else []

                    # Add basic info first
                    evaluation = {
                        'name': str(row.get('name', '')),
                        'email': str(row.get('email', '')),
                        'current_role': str(row.get('current_role', ''))
                    }

                    # Evaluate CV
                    result = scoring_engine.evaluate_cv(cv_dict, job_requirements)
                    evaluation.update(result)

                    # Format reasons if present
                    if 'reasons' in result:
                        evaluation['reasons_not_suitable'] = '\n'.join(result['reasons'])

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