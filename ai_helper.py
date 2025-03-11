import os
import json
from openai import OpenAI
import streamlit as st

class AIHelper:
    def __init__(self):
        self.client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
        
    def analyze_cv_content(self, cv_text, job_requirements):
        """
        Analyze CV content using OpenAI to extract skills and match with requirements.
        """
        try:
            prompt = f"""
            Analyze this CV content and extract technical skills and experience.
            For the skills analysis, focus on these required skills: {', '.join(job_requirements.get('required_skills', []))}
            Nice to have skills: {', '.join(job_requirements.get('nice_to_have_skills', []))}

            CV Content:
            {cv_text}

            Provide analysis in JSON format:
            {{
                "technical_skills_found": ["list of all technical skills found"],
                "matched_required_skills": ["list of matched required skills"],
                "matched_nice_to_have": ["list of matched nice to have skills"],
                "missing_critical_skills": ["list of missing required skills"],
                "skill_match_score": float (0-100),
                "analysis_notes": ["list of important observations"]
            }}
            """

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
            
            # Log the analysis
            st.write("\nAI Analysis Results:")
            st.write("Technical Skills Found:", result['technical_skills_found'])
            st.write("Skills Match Score:", result['skill_match_score'])
            
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
