import streamlit as st
import pandas as pd
from google_sheet_client import GoogleSheetClient
from scoring_engine import ScoringEngine
from utils import parse_job_description, prepare_export_data, calculate_years_experience
from datetime import datetime
import nlp_matcher # Added import for nlp_matcher

def main():
    st.set_page_config(page_title="CV Evaluator", layout="wide")
    st.title("CV Evaluator")

    # Initialize components
    google_client = GoogleSheetClient()
    scoring_engine = ScoringEngine()

    # Sidebar for job description input
    st.sidebar.header("Job Description")
    role = st.sidebar.text_input(
        "Role Title",
        value="Backend Integration Engineer",
        help="Enter the role title"
    )

    # Default job description from your text
    default_jd = """About You
    • python
    • RESTful API
    • webhooks
    • AWS, GCP and Azure 
    • ArgoCD, Kubernetes & docker
    • postgres and mongodb
    • testing 
    • Github Actions

Nice to have
   • Golang 
   • including IaC (Terraform, CloudFormation)
    """

    jd_text = st.sidebar.text_area(
        "Enter Job Description",
        value=default_jd,
        height=300,
        help="Enter the complete job description including required skills and experience"
    )

    # Years of experience input
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

    if st.sidebar.button("Evaluate CVs"):
        if not jd_text or not sheet_id:
            st.error("Please provide both job description and Google Sheet ID")
            return

        try:
            with st.spinner("Fetching CV data..."):
                # Parse job requirements
                job_requirements = parse_job_description(jd_text, years_exp)
                job_requirements['role'] = role

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

                    cv_name = f"{row.get('FIRST NAME', '')} {row.get('LAST NAME', '')}"
                    cv_link = str(row.get('UPLOAD YOUR CV HERE', '')).strip()

                    # Create an expander for each CV to contain the details
                    with st.expander(f"Processing CV {index + 1}: {cv_name}", expanded=True):
                        st.write(f"**CV Link:** {cv_link}")

                        # Log additional CV information if available
                        if 'PHONE' in row:
                            st.write(f"**Phone:** {row.get('PHONE', '')}")
                        if 'EMAIL' in row:
                            st.write(f"**Email:** {row.get('EMAIL', '')}")

                    # Calculate years of experience and get first line
                    years_exp, first_line, cv_content = calculate_years_experience(
                        cv_url=cv_link,
                        start_date_str=row.get('Experience Start Date', '')
                    )

                    # Extract technical skills and display them
                    if isinstance(cv_content, str) and cv_content:
                        extracted_skills = nlp_matcher.extract_technical_skills(cv_content)
                        st.write("\nAll Technical Skills Found:", ", ".join(extracted_skills))

                    # Create CV dictionary
                    cv_dict = {
                        'name': cv_name,
                        'email': str(row.get('EMAIL', '')).strip(),
                        'cv_link': cv_link,
                        'first_line': first_line,
                        'years_experience': years_exp,
                        'cv_text': cv_content if isinstance(cv_content, str) else str(cv_content)
                    }

                    # Debug logging for CV content
                    st.write("\nDebug - CV Content Type:", type(cv_content))
                    st.write("Debug - CV Text in Dictionary:", bool(cv_dict['cv_text']))
                    st.write("Debug - CV Text Length:", len(cv_dict['cv_text']) if cv_dict['cv_text'] else 0)

                    # Evaluate CV
                    result = scoring_engine.evaluate_cv(cv_dict, job_requirements)

                    # Compile results
                    evaluation = {
                        'name': cv_dict['name'],
                        'email': cv_dict['email'],
                        'cv_link': cv_dict['cv_link'],
                        'first_line': cv_dict['first_line'],
                        'years_experience': years_exp,
                        'technical_skills': ", ".join(result.get('technical_skills', [])),  # All technical skills
                        'required_skills': ", ".join(result.get('matched_required_skills', [])),  # Required skills found
                        'nice_to_have_skills': ", ".join(result.get('matched_nice_to_have', [])),  # Nice-to-have skills
                        'missing_skills': ", ".join(result.get('missing_critical_skills', [])),  # Missing skills
                        'overall_score': result['overall_score'],
                        'document_errors': cv_content if cv_content and isinstance(cv_content, str) and "Error" in cv_content else '',
                        'notes': result.get('evaluation_notes', '')
                    }

                    # Add to results
                    results.append(evaluation)

                # Hide progress bar
                progress_bar.empty()

                # Sort results by overall score
                results_df = pd.DataFrame(results)
                results_df = results_df.sort_values('overall_score', ascending=False)

                # Display results
                st.header("Evaluation Results")

                # Summary metrics
                col1, col2, col3, col4 = st.columns(4)
                with col1:
                    st.metric("CVs Processed", len(results))
                with col2:
                    suitable_count = len(results_df[results_df['overall_score'] >= 60])
                    st.metric("Suitable Candidates", suitable_count)
                with col3:
                    avg_score = results_df['overall_score'].mean()
                    st.metric("Average Score", f"{avg_score:.1f}")
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
                        "first_line": "First Line of CV",
                        "years_experience": st.column_config.NumberColumn(
                            "Years of Experience",
                            format="%.1f"
                        ),
                        "technical_skills": st.column_config.TextColumn(
                            "All Technical Skills",
                            help="All technical skills found in the CV"
                        ),
                        "required_skills": st.column_config.TextColumn(
                            "Required Skills Found",
                            help="Skills from the job requirements found in the CV"
                        ),
                        "nice_to_have_skills": st.column_config.TextColumn(
                            "Nice-to-Have Skills",
                            help="Additional desired skills found in the CV"
                        ),
                        "missing_skills": st.column_config.TextColumn(
                            "Missing Required Skills",
                            help="Required skills not found in the CV"
                        ),
                        "overall_score": st.column_config.NumberColumn(
                            "Match Score (%)",
                            format="%.1f"
                        ),
                        "document_errors": "CV Processing Issues",
                        "notes": "Evaluation Notes"
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