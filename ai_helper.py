import os
import json
from openai import OpenAI
import streamlit as st

class AIHelper:
    def __init__(self):
        api_key = os.getenv('OPENAI_API_KEY')
        if not api_key:
            st.warning("⚠️ OpenAI API key not found. Set the OPENAI_API_KEY environment variable.")
            st.info("To set up the OpenAI API key, go to the Secrets tool in Replit and add OPENAI_API_KEY.")
        self.client = OpenAI(api_key=api_key)

    def analyze_cv_content(self, cv_text, job_requirements):
        """
        Analyze CV content using OpenAI to extract skills and match with requirements.
        """
        try:
            # Log the analysis start
            st.write("\nStarting AI Analysis...")

            prompt = f"""
            You are an expert technical recruiter. Analyze this CV content and extract technical skills and experience.

            Required Skills to Match: {', '.join(job_requirements.get('required_skills', []))}
            Nice to Have Skills: {', '.join(job_requirements.get('nice_to_have_skills', []))}

            CV Content:
            {cv_text}

            Analyze the CV content for technical skills and provide structured output in this JSON format:
            {{
                "technical_skills_found": ["list of all technical skills found"],
                "matched_required_skills": ["list of required skills found in CV"],
                "matched_nice_to_have": ["list of nice to have skills found in CV"],
                "missing_critical_skills": ["list of required skills NOT found in CV"],
                "skill_match_score": float (0-100),
                "analysis_notes": ["list of key observations about the candidate"]
            }}

            Guidelines:
            1. Be thorough in identifying both explicit and implicit skills
            2. Consider variations of skill names (e.g., "React.js" vs "React")
            3. Look for experience level indicators
            4. Calculate skill_match_score based on required skills coverage
            """

            # Call OpenAI API with JSON response format
            response = self.client.chat.completions.create(
                model="gpt-4o",  # the newest OpenAI model is "gpt-4o" which was released May 13, 2024
                messages=[{
                    "role": "system",
                    "content": "You are an expert technical recruiter specialized in evaluating CVs."
                }, {
                    "role": "user",
                    "content": prompt
                }],
                response_format={"type": "json_object"}
            )

            # Parse the JSON response
            result = json.loads(response.choices[0].message.content)

            # Log the analysis results
            st.write("\nAI Analysis Results:")
            st.write("Technical Skills Found:", result['technical_skills_found'])
            st.write("Skills Match Score:", result['skill_match_score'])
            st.write("Analysis Notes:", result['analysis_notes'])

            return result

        except Exception as e:
            st.error(f"Error in AI analysis: {str(e)}")
            return {
                "technical_skills_found": [],
                "matched_required_skills": [],
                "matched_nice_to_have": [],
                "missing_critical_skills": [],
                "skill_match_score": 0,
                "analysis_notes": [f"Error in analysis: {str(e)}"]
            }