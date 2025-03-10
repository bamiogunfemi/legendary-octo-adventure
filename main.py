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
                
                # Fetch CV data
                cv_data = google_client.get_sheet_data(sheet_id, sheet_range)
                
                if cv_data.empty:
                    st.error("No data found in the specified sheet range")
                    return
                
                # Process each CV
                results = []
                for _, row in cv_data.iterrows():
                    cv_dict = row.to_dict()
                    # Convert skills and certifications to lists
                    cv_dict['skills'] = row.get('skills', '').split(',')
                    cv_dict['certifications'] = row.get('certifications', '').split(',')
                    
                    # Evaluate CV
                    evaluation = scoring_engine.evaluate_cv(cv_dict, job_requirements)
                    
                    # Add candidate info
                    evaluation.update({
                        'name': row.get('name', ''),
                        'email': row.get('email', ''),
                        'current_role': row.get('current_role', '')
                    })
                    
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
                st.dataframe(results_df)
                
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
