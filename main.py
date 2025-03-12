import streamlit as st
import pandas as pd
import nltk
from google_sheet_client import GoogleSheetClient
from scoring_engine import ScoringEngine
from utils import parse_job_description, prepare_export_data, calculate_years_experience
import os

def initialize_nltk():
    """Initialize NLTK data with proper error handling"""
    try:
        # Set NLTK data path
        nltk_data_dir = os.path.join(os.getcwd(), 'nltk_data')
        os.makedirs(nltk_data_dir, exist_ok=True)
        nltk.data.path.insert(0, nltk_data_dir)

        st.write("Starting NLTK initialization...")

        # Required NLTK packages
        packages = ['punkt', 'stopwords', 'wordnet', 'averaged_perceptron_tagger']

        # Download each package
        for package in packages:
            st.write(f"Checking/downloading NLTK package: {package}")
            try:
                nltk.data.find(f'tokenizers/{package}')
            except LookupError:
                nltk.download(package, download_dir=nltk_data_dir, quiet=True)

        st.success("✅ NLTK initialization completed successfully")
        return True
    except Exception as e:
        st.error(f"❌ Error initializing NLTK: {str(e)}")
        return False

def main():
    try:
        # Page config must be the first Streamlit command
        st.set_page_config(
            page_title="CV Evaluator",
            layout="wide",
            initial_sidebar_state="expanded"
        )

        st.write("🚀 Application startup initiated...")
        st.title("CV Evaluator")

        # Initialize NLTK before any other operations
        if not initialize_nltk():
            st.error("Failed to initialize required NLTK components. Please contact support.")
            return

        try:
            st.write("⚙️ Initializing application components...")
            # Initialize components
            google_client = GoogleSheetClient()
            scoring_engine = ScoringEngine()
            st.success("✅ Components initialized successfully")

            # Sidebar for job description input
            st.sidebar.header("Job Description")
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

            if st.sidebar.button("Evaluate First 3 CVs"):
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
                            years_exp, first_line, cv_text = calculate_years_experience(
                                cv_url=cv_link,
                                start_date_str=row.get('Experience Start Date', '')
                            )

                            # Create CV dictionary
                            cv_dict = {
                                'name': cv_name,
                                'email': str(row.get('EMAIL', '')).strip(),
                                'cv_link': cv_link,
                                'first_line': first_line,
                                'years_experience': years_exp,
                                'skills': [],
                                'cv_text': cv_text if isinstance(cv_text, str) and "CV Content:" in cv_text else ''
                            }

                            # Extract CV content from cv_text
                            if cv_dict['cv_text'] and "CV Content:" in cv_dict['cv_text']:
                                cv_dict['cv_text'] = cv_dict['cv_text'].split("CV Content:", 1)[1].strip()
                                st.write("CV Text extracted for analysis:", len(cv_dict['cv_text']), "characters")

                            # Evaluate CV
                            result = scoring_engine.evaluate_cv(cv_dict, job_requirements)

                            # Update evaluation dictionary
                            evaluation = {
                                'name': cv_dict['name'],
                                'email': cv_dict['email'],
                                'cv_link': cv_dict['cv_link'],
                                'first_line': cv_dict['first_line'],
                                'years_experience': years_exp,
                                'required_skills': ', '.join(result.get('matched_required_skills', [])),
                                'nice_to_have_skills': ', '.join(result.get('matched_nice_to_have', [])),
                                'missing_skills': ', '.join(result.get('missing_critical_skills', [])),
                                'overall_score': result['overall_score'],
                                'document_errors': cv_text if cv_text and "CV Content:" not in cv_text else '',
                                'notes': result.get('evaluation_notes', '')
                            }

                            # Add reasons for not suitable candidates
                            reasons = []
                            if cv_text and "CV Content:" not in cv_text:
                                reasons.append(f"CV Processing: {cv_text}")
                            if result['reasons']:
                                reasons.extend(result['reasons'])

                            evaluation['reasons_not_suitable'] = '\n'.join(reasons) if reasons else ''
                            results.append(evaluation)

                        # Hide progress bar
                        progress_bar.empty()

                        # Display results
                        if results:
                            # Sort results by overall score
                            results_df = pd.DataFrame(results)
                            results_df = results_df.sort_values('overall_score', ascending=False)

                            # Highlight top 5 candidates
                            results_df['is_top_5'] = False
                            results_df.loc[results_df.index[:5], 'is_top_5'] = True

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
                                st.metric("Average Score", f"{avg_score:.2f}")
                            with col4:
                                error_count = len(results_df[results_df['document_errors'].notna() & (results_df['document_errors'] != '')])
                                st.metric("CVs with Errors", error_count)

                            # Style the dataframe
                            def highlight_top_5(row):
                                return ['background-color: #90EE90' if row['is_top_5'] else '' for _ in row]

                            styled_df = results_df.style.apply(highlight_top_5, axis=1)

                            # Display detailed results
                            st.write("### Detailed Results")
                            st.dataframe(
                                styled_df,
                                column_config={
                                    "name": "Name",
                                    "email": "Email",
                                    "cv_link": st.column_config.LinkColumn("CV Link"),
                                    "first_line": st.column_config.TextColumn(
                                        "First Line of CV",
                                        help="First line extracted from the CV document"
                                    ),
                                    "years_experience": "Years of Experience",
                                    "required_skills": "Required Skills Found",
                                    "nice_to_have_skills": "Nice-to-Have Skills",
                                    "missing_skills": "Missing Critical Skills",
                                    "overall_score": st.column_config.NumberColumn(
                                        "Match Score (%)",
                                        format="%.2f"
                                    ),
                                    "document_errors": "CV Processing Issues",
                                    "notes": "Evaluation Notes",
                                    "reasons_not_suitable": st.column_config.TextColumn("Additional Reasons"),
                                    "is_top_5": None  # Hide this column
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
                        else:
                            st.warning("No results to display")

                except Exception as e:
                    st.error(f"An error occurred: {str(e)}")

        except Exception as e:
            st.error(f"❌ Component initialization error: {str(e)}")
            return

    except Exception as e:
        st.error(f"❌ Application startup error: {str(e)}")
        return

if __name__ == "__main__":
    main()