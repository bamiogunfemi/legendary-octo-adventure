import streamlit as st
import pandas as pd
from google_sheet_client import GoogleSheetClient
from scoring_engine import ScoringEngine
from utils import parse_job_description, prepare_export_data, calculate_years_experience
from nlp_matcher import NLPMatcher
from deepseek_evaluator import DeepseekEvaluator
from mastersheet_processor import process_mastersheet

def main():
    st.set_page_config(page_title="CV Evaluator", layout="wide")
    st.title("CV Evaluator")
    
    # Add tab functionality to switch between regular evaluation and mastersheet processing
    tab1, tab2 = st.tabs(["CV Evaluation", "Mastersheet Processing"])
    
    # Display Google Sheet service account info
    st.sidebar.info("""
    **Important:** To access your Google Sheet, share it with the following email (with Editor access):
    
    cv-evaluator@cv-evaluator-384506.iam.gserviceaccount.com
    """)
    
    # Initialize components
    google_client = GoogleSheetClient()
    scoring_engine = ScoringEngine()
    nlp_matcher = NLPMatcher()
    
    # Google Sheet ID input (shared between tabs)
    sheet_id = st.sidebar.text_input(
        "Google Sheet ID",
        value="1dbzN4UScPgEYeqmp_MQgYghOq2vnzjJqs-dUgsj_Dq4",
        help="Enter the ID from the Google Sheet URL"
    )
    
    # Mastersheet Processing Tab
    with tab2:
        st.header("Mastersheet Processing")
        st.write("""
        This feature will process your mastersheet with over 2,000 rows to extract:
        - Technical skills from each CV
        - Suggested roles based on these skills
        - Calculated years of experience
        
        Results will be added as new columns to your Google Sheet.
        """)
        
        # Add instructions about sheet name
        st.info("""
        **Important**: You need to use the actual name of your sheet. For example, if your 
        first sheet is named "Sheet1", you should use "Sheet1!A1:Z5000".
        """)
        
        # Sheet range for mastersheet
        mastersheet_range = st.text_input(
            "Sheet Range (include Sheet name)",
            value="Cleaned Data!A1:Z5000",
            help="Format: 'YourSheetName!A1:Z5000'. Include all columns with CVs. The sheet name must match exactly.",
            key="mastersheet_range"
        )
        
        # Output range for mastersheet
        output_range = st.text_input(
            "Output Range (where to write results)",
            value="Cleaned Data!AA1",
            help="First cell where extracted data columns will be written (e.g., 'Sheet1!AA1'). Use the same sheet name as above.",
            key="output_range"
        )
        
        # Option to include headers
        include_headers = st.checkbox(
            "Include Headers/Titles",
            value=True,
            help="Uncheck this if you don't want column titles to be included in the output (useful when appending to existing data)."
        )
        
        # Use a form for the button to ensure proper handling
        with st.form(key="mastersheet_form"):
            submit_button = st.form_submit_button(label="Process Mastersheet")
            
            if submit_button:
                print("Process Mastersheet button clicked!")
                if not sheet_id:
                    st.error("Please provide a Google Sheet ID")
                    print("Error: No sheet_id provided")
                else:
                    # Call the mastersheet processing function
                    print(f"Calling process_mastersheet with: {sheet_id}, {mastersheet_range}, {output_range}")
                    try:
                        process_mastersheet(sheet_id, mastersheet_range, output_range, include_headers)
                    except Exception as e:
                        st.error(f"Error processing mastersheet: {str(e)}")
                        print(f"Exception in process_mastersheet: {str(e)}")
    
    # CV Evaluation Tab
    with tab1:
        st.header("CV Evaluation Against Job Requirements")
        
        # Sidebar for job description input
        st.sidebar.header("Job Description")
        role = st.sidebar.text_input(
            "Role Title",
            value="",
            help="Enter the role title"
        )
        
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
        
        # CV Source input
        st.sidebar.header("CV Source")
        sheet_range = st.sidebar.text_input(
            "Sheet Range",
            value="A1:Z1000",
            help="Enter the range of cells to process (e.g., 'Sheet1!A1:Z1000')"
        )
        
        cv_column = st.sidebar.text_input(
            "CV Link Column Letter",
            value="G",
            help="Enter the column letter (e.g., 'G') where CV links are located. This overrides automatic column name detection."
        )
        
        # Output sheet settings
        st.sidebar.header("Results Output")
        save_to_sheet = st.sidebar.checkbox(
            "Save Results to Google Sheet", 
            value=False,
            help="Enable to save evaluation results to a sheet in the same spreadsheet"
        )
        
        output_sheet = st.sidebar.text_input(
            "Output Sheet Name",
            value="Evaluation_Results",
            help="Name of the sheet where results will be saved (will be created if it doesn't exist)"
        )
        
        # Evaluate button
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
                        
                        # Try different possible column names for first and last name
                        first_name_cols = ['FIRST NAME', 'First Name', 'first name', 'First_Name', 'first_name', 'FirstName']
                        last_name_cols = ['LAST NAME', 'Last Name', 'last name', 'Last_Name', 'last_name', 'LastName']
                        
                        # Get first name using various possible column names
                        first_name = ''
                        for col in first_name_cols:
                            if col in row:
                                first_name = row.get(col, '')
                                break
                        
                        # Get last name using various possible column names
                        last_name = ''
                        for col in last_name_cols:
                            if col in row:
                                last_name = row.get(col, '')
                                break
                        
                        # Combine to create full name
                        cv_name = f"{first_name} {last_name}".strip()
                        if not cv_name:
                            # If no name columns found, check for a full name column
                            name_cols = ['NAME', 'Name', 'name', 'Full Name', 'full name', 'FullName']
                            for col in name_cols:
                                if col in row:
                                    cv_name = row.get(col, '')
                                    break
                        
                        # Check if we should use the column letter specified by the user
                        cv_link = ''
                        
                        # Convert column letter to index (0-based)
                        if cv_column:
                            try:
                                # Convert column letter to index (A=0, B=1, C=2, etc.)
                                col_letter = cv_column.upper()
                                col_index = 0
                                for char in col_letter:
                                    col_index = col_index * 26 + (ord(char) - ord('A'))
                                
                                # Get CV link from the specified column if it exists
                                if col_index < len(row) and isinstance(row.iloc[col_index], str):
                                    cv_link = str(row.iloc[col_index]).strip()
                                elif col_index < len(row.index):
                                    # Try using the column name approach as a fallback
                                    column_name = row.index[col_index]
                                    cv_link = str(row.get(column_name, '')).strip()
                            except Exception as e:
                                print(f"Error using column letter {cv_column}: {str(e)}")
                                # Continue to the fallback method
                        
                        # Fall back to column name approach if still no link found
                        if not cv_link:
                            cv_link_cols = [
                                'UPLOAD YOUR CV HERE', 'CV Link', 'cv link', 'CV URL', 'Resume Link', 
                                'resume link', 'CV', 'Resume', 'Upload CV'
                            ]
                            
                            for col in cv_link_cols:
                                if col in row:
                                    cv_link = str(row.get(col, '')).strip()
                                    if cv_link:  # If we found a non-empty link, use it
                                        break
                        
                        # Try different possible column names for experience date
                        exp_date_cols = [
                            'Experience Start Date', 'Start Date', 'Work Start Date', 
                            'Career Start', 'Job Start Date', 'experience_start_date'
                        ]
                        
                        start_date_str = ''
                        for col in exp_date_cols:
                            if col in row:
                                start_date_str = row.get(col, '')
                                if start_date_str:  # If we found a non-empty date, use it
                                    break
                        
                        # Calculate years of experience and get CV content
                        years_exp, _, cv_content = calculate_years_experience(
                            cv_url=cv_link,
                            start_date_str=start_date_str
                        )
                        
                        # Try different possible column names for email
                        email_cols = ['EMAIL', 'Email', 'email', 'E-mail', 'e-mail', 'Contact Email']
                        
                        email = ''
                        for col in email_cols:
                            if col in row:
                                email = str(row.get(col, '')).strip()
                                if email:  # If we found a non-empty email, use it
                                    break
                        
                        # Try to get years of experience from the spreadsheet if available
                        sheet_years_cols = ['HOW MANY YEARS EXPERIENCE DO YOU HAVE?', 'Years Experience', 'Experience (Years)', 'Years']
                        sheet_years = None
                        
                        for col in sheet_years_cols:
                            if col in row:
                                try:
                                    # Try to extract a number from the cell
                                    years_str = str(row.get(col, '')).strip()
                                    if years_str:
                                        # Extract digits from the string (e.g., "5 years" -> 5)
                                        import re
                                        digits = re.findall(r'\d+', years_str)
                                        if digits:
                                            sheet_years = float(digits[0])
                                            break
                                except:
                                    # If conversion fails, continue to the next column
                                    pass
                        
                        # If we have years from the sheet and not from CV parsing, use that
                        if sheet_years is not None and (years_exp == 0 or years_exp is None):
                            years_exp = sheet_years
                                    
                        # Create CV dictionary
                        cv_dict = {
                            'name': cv_name or "None",
                            'email': email or "None",
                            'cv_link': cv_link or "None",
                            'years_experience': years_exp,
                            'cv_text': cv_content if isinstance(cv_content, str) else str(cv_content)
                        }
                        
                        # Evaluate CV
                        result = scoring_engine.evaluate_cv(cv_dict, job_requirements)
                        
                        # Get suggested positions
                        from mastersheet_processor import suggest_positions
                        
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
                    
                    # Apply conditional formatting
                    def color_score(val):
                        if val >= 80:  # Top candidates
                            return 'background-color: #d4edda; color: #155724'  # Green
                        elif val < 40:  # Unsuitable candidates
                            return 'background-color: #f8d7da; color: #721c24'  # Red
                        else:
                            return ''
                    
                    # Apply the styling
                    styled_df = results_df.style.applymap(color_score, subset=['overall_score'])
                    
                    st.dataframe(
                        styled_df,
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
                                "Detailed Analysis",
                                help="Comprehensive evaluation including both algorithmic scoring and AI analysis"
                            )
                        }
                    )
                    
                    # Export options
                    export_col1, export_col2 = st.columns(2)
                    with export_col1:
                        csv = results_df.to_csv(index=False)
                        st.download_button(
                            label="Download Results CSV",
                            data=csv,
                            file_name="cv_evaluation_results.csv",
                            mime="text/csv"
                        )
                    
                    # Save to Google Sheet if enabled
                    if save_to_sheet:
                        with export_col2:
                            try:
                                # Format the output range
                                output_range = f"{output_sheet}!A1"
                                
                                # Write to the Google Sheet
                                with st.spinner("Saving results to Google Sheet..."):
                                    google_client.write_to_sheet(sheet_id, output_range, results_df)
                                    st.success(f"Results successfully saved to sheet '{output_sheet}'")
                            except Exception as e:
                                st.error(f"Failed to save results: {str(e)}")
                                st.info("Make sure you've shared your sheet with edit permissions to the Service Account Email above.")
            
            except Exception as e:
                st.error(f"An error occurred: {str(e)}")

if __name__ == "__main__":
    main()
