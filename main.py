import streamlit as st
import pandas as pd
from google_sheet_client import GoogleSheetClient
from scoring_engine import ScoringEngine
from utils import parse_job_description, prepare_export_data, calculate_years_experience
from datetime import datetime
from nlp_matcher import NLPMatcher

def suggest_positions(technical_skills):
    """Suggest potential positions based on technical skills"""
    positions = set()  # Using set to avoid duplicates

    # Convert skills list to lowercase for matching
    skills = [skill.lower() for skill in technical_skills]

    # Backend Development
    if any(x in skills for x in ['python', 'java', 'nodejs', 'django', 'flask', 'fastapi', 'spring', 'express.js', 'nestjs']):
        if any(x in skills for x in ['postgresql', 'mongodb', 'mysql', 'database', 'typeorm', 'prisma']):
            positions.add("Back-End Developer")
            positions.add("Software Engineer")

    # Frontend Development
    if any(x in skills for x in ['react', 'angular', 'vue', 'javascript', 'typescript', 'html', 'css', 'nextjs']):
        positions.add("Front-End Developer")
        if any(x in skills for x in ['ui', 'ux', 'design']):
            positions.add("UI Developer")

    # Full Stack
    if any(x in skills for x in ['react', 'angular', 'vue', 'nextjs']) and \
       any(x in skills for x in ['python', 'nodejs', 'java', 'express.js', 'nestjs']):
        positions.add("Full Stack Developer")
        positions.add("Software Engineer")

    # DevOps/Cloud/Platform
    if any(x in skills for x in ['aws', 'azure', 'gcp', 'kubernetes', 'docker', 'terraform', 'ci/cd']):
        positions.add("DevOps Engineer")
        positions.add("Cloud Engineer")
        positions.add("Platform Engineer")
        if 'kubernetes' in skills:
            positions.add("Site Reliability Engineer")

    # Security Engineering
    if any(x in skills for x in ['security', 'oauth2', 'jwt', 'authentication', 'authorization', 'rbac']):
        positions.add("Security Engineer")
        positions.add("Application Security Engineer")
        if any(x in skills for x in ['aws', 'azure', 'gcp']):
            positions.add("Cloud Security Engineer")

    # API/Integration/Architecture
    if any(x in skills for x in ['rest', 'api', 'graphql', 'grpc', 'microservices', 'event-driven']):
        positions.add("API Integration Engineer")
        if 'microservices' in skills or 'event-driven' in skills:
            positions.add("Software Architect")
            positions.add("Solutions Architect")

    # Mobile Development
    if 'react native' in skills:
        positions.add("Mobile Developer")
        positions.add("React Native Developer")
    if 'android' in skills or 'kotlin' in skills:
        positions.add("Android Developer")
    if 'ios' in skills or 'swift' in skills:
        positions.add("iOS Developer")

    # Emerging Tech
    if 'web3' in skills or 'blockchain' in skills:
        positions.add("Blockchain Developer")
        positions.add("Web3 Developer")
    if any(x in skills for x in ['serverless', 'lambda']):
        positions.add("Serverless Developer")
        positions.add("Cloud Developer")

    return sorted(list(positions)) if positions else ["Entry Level Developer"]

def main():
    st.set_page_config(page_title="CV Evaluator", layout="wide")
    st.title("CV Evaluator")

    # Initialize components
    google_client = GoogleSheetClient()
    scoring_engine = ScoringEngine()
    nlp_matcher = NLPMatcher()

    # Sidebar for job description input
    st.sidebar.header("Job Description")
    role = st.sidebar.text_input(
        "Role Title",
        value="",
        help="Enter the role title"
    )

    # Default job description
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
        value="",
        height=300,
        help="Enter the complete job description including required skills and experience"
    )

    # Years of experience input
    years_exp = st.sidebar.number_input(
        "Required Years of Experience",
        min_value=0,
        max_value=20,
        value=5,
        help="Set the minimum years of experience required"
    )

    # Google Sheet input
    st.sidebar.header("CV Source")
    sheet_id = st.sidebar.text_input(
        "Google Sheet ID",
        value="",
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
            # Parse job requirements
            job_requirements = parse_job_description(jd_text, years_exp)
            job_requirements['role'] = role

            # Create a placeholder for the loading spinner
            with st.spinner("Evaluating CVs..."):
                # Fetch CV data
                cv_data = google_client.get_sheet_data(sheet_id, sheet_range)

                if cv_data.empty:
                    st.error("No data found in the specified sheet range")
                    return

                # Process each CV
                results = []
                total_cvs = len(cv_data)
                progress_bar = st.progress(0)
                progress_text = st.empty()

                for index, row in cv_data.iterrows():
                    # Update progress
                    progress = (index + 1) / total_cvs
                    progress_bar.progress(progress)
                    progress_text.text(f"Processing CV {index + 1} of {total_cvs}")

                    cv_name = f"{row.get('FIRST NAME', '')} {row.get('LAST NAME', '')}"
                    cv_link = str(row.get('UPLOAD YOUR CV HERE', '')).strip()

                    # Calculate years of experience and get CV content
                    years_exp, _, cv_content = calculate_years_experience(
                        cv_url=cv_link,
                        start_date_str=row.get('Experience Start Date', '')
                    )

                    # Create CV dictionary
                    cv_dict = {
                        'name': cv_name or "None",
                        'email': str(row.get('EMAIL', '')).strip() or "None",
                        'cv_link': cv_link or "None",
                        'years_experience': years_exp,
                        'cv_text': cv_content if isinstance(cv_content, str) else str(cv_content)
                    }

                    # Evaluate CV
                    result = scoring_engine.evaluate_cv(cv_dict, job_requirements)

                    # Compile results
                    evaluation = {
                        'name': cv_dict['name'],
                        'email': cv_dict['email'],
                        'cv_link': cv_dict['cv_link'],
                        'years_experience': years_exp,
                        'technical_skills': ", ".join(result.get('technical_skills', [])) or "None",
                        'required_skills': ", ".join(result.get('matched_required_skills', [])) or "None",
                        'nice_to_have_skills': ", ".join(result.get('matched_nice_to_have', [])) or "None",
                        'missing_required_skills': ", ".join(result.get('missing_critical_skills', [])) or "None",
                        'missing_nice_to_have': ", ".join(result.get('missing_nice_to_have', [])) or "None",
                        'overall_score': result['overall_score'],
                        'skills_score': result['skills_score'],
                        'experience_score': result['experience_score'],
                        'suggested_positions': ", ".join(suggest_positions(result.get('technical_skills', []))) or "None",
                        'evaluation_notes': result.get('evaluation_notes', '')
                    }

                    # Add to results
                    results.append(evaluation)

                # Clear progress indicators
                progress_bar.empty()
                progress_text.empty()

                # Sort results by overall score
                results_df = pd.DataFrame(results)
                results_df = results_df.sort_values('overall_score', ascending=False)

                # Display results
                st.header("Evaluation Results")

                # Summary metrics
                col1, col2, col3, col4, col5 = st.columns(5)
                with col1:
                    st.metric("CVs Processed", len(results))
                with col2:
                    suitable_count = len(results_df[results_df['overall_score'] >= 60])
                    st.metric("Suitable Candidates", suitable_count)
                with col3:
                    avg_score = results_df['overall_score'].mean()
                    st.metric("Average Score", f"{avg_score:.1f}")
                with col4:
                    avg_skills = results_df['skills_score'].mean()
                    st.metric("Avg Skills Score", f"{avg_skills:.1f}")
                with col5:
                    avg_exp = results_df['experience_score'].mean()
                    st.metric("Avg Experience Score", f"{avg_exp:.1f}")

                # Detailed results table
                st.write("### Detailed Results")
                st.dataframe(
                    results_df,
                    column_config={
                        "name": "Name",
                        "email": "Email",
                        "cv_link": st.column_config.LinkColumn("CV Link"),
                        "years_experience": st.column_config.NumberColumn(
                            "Years of Experience",
                            format="%.1f"
                        ),
                        "technical_skills": st.column_config.TextColumn(
                            "Technical Skills",
                            help="All technical skills found in the CV"
                        ),
                        "required_skills": st.column_config.TextColumn(
                            "Required Skills Found",
                            help="Skills from the job requirements found in the CV"
                        ),
                        "nice_to_have_skills": st.column_config.TextColumn(
                            "Nice-to-Have Skills Found",
                            help="Additional desired skills found in the CV"
                        ),
                        "missing_required_skills": st.column_config.TextColumn(
                            "Missing Required Skills",
                            help="Required skills not found in the CV"
                        ),
                        "missing_nice_to_have": st.column_config.TextColumn(
                            "Missing Nice-to-Have Skills",
                            help="Nice-to-have skills not found in the CV"
                        ),
                        "skills_score": st.column_config.NumberColumn(
                            "Skills Score",
                            format="%.1f",
                            help="Score based on technical skills match (0-100)"
                        ),
                        "experience_score": st.column_config.NumberColumn(
                            "Experience Score",
                            format="%.1f",
                            help="Score based on experience match (0-100)"
                        ),
                        "overall_score": st.column_config.NumberColumn(
                            "Overall Score",
                            format="%.1f",
                            help="Final score (average of Skills and Experience scores)"
                        ),
                        "suggested_positions": st.column_config.TextColumn(
                            "Suggested Positions",
                            help="Potential roles based on technical skills"
                        ),
                        "evaluation_notes": st.column_config.TextColumn(
                            "Score Breakdown",
                            help="Detailed breakdown of scoring components"
                        )
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