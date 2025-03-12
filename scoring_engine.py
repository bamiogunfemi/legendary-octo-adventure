import pandas as pd
import nltk
from nltk.tokenize import word_tokenize
from nltk.corpus import stopwords
import re
import streamlit as st
from nlp_matcher import NLPMatcher
from datetime import datetime
import dateparser

class ScoringEngine:
    def __init__(self):
        self.nlp_matcher = NLPMatcher()
        self.stop_words = set(stopwords.words('english'))

    def evaluate_cv(self, cv_data, job_requirements):
        """Main evaluation function with detailed reasoning"""
        try:
            reasons = []
            notes = []

            # Get CV text and debug log
            cv_text = cv_data.get('cv_text', '')
            st.write("\nProcessing CV Content (length):", len(cv_text) if cv_text else 0)

            if not cv_text:
                st.warning("No CV text content available for analysis")
                return self._create_empty_result("No CV content available")

            # Extract technical skills from CV content
            technical_skills = self.nlp_matcher.extract_technical_skills(cv_text)
            st.write("\nTechnical Skills Found:", ", ".join(technical_skills))

            # Get required and nice-to-have skills from job requirements
            required_skills = job_requirements.get('required_skills', [])
            nice_to_have_skills = job_requirements.get('nice_to_have_skills', [])

            # Display job requirements
            st.write("\nJob Requirements:")
            st.write("Required Skills:", ", ".join(required_skills))
            st.write("Nice-to-Have Skills:", ", ".join(nice_to_have_skills))

            # Match required skills
            skills_score, matched_required = self.nlp_matcher.match_skills(
                technical_skills,
                required_skills
            )

            # Match nice-to-have skills
            _, matched_nice_to_have = self.nlp_matcher.match_skills(
                technical_skills,
                nice_to_have_skills
            )

            # Find missing required skills
            missing_skills = list(set(required_skills) - set(matched_required))

            # Display skills matching results
            st.write("\nSkills Analysis:")
            st.write("Required Skills Found:", ", ".join(matched_required) if matched_required else "None")
            st.write("Nice-to-Have Skills Found:", ", ".join(matched_nice_to_have) if matched_nice_to_have else "None")
            st.write("Missing Required Skills:", ", ".join(missing_skills) if missing_skills else "None")

            # Calculate overall score based on required skills match
            overall_score = skills_score * 0.7  # Weight skills score

            # Compile results
            result = {
                'overall_score': overall_score,
                'technical_skills': technical_skills,
                'matched_required_skills': matched_required,
                'matched_nice_to_have': matched_nice_to_have,
                'missing_critical_skills': missing_skills,
                'evaluation_notes': '; '.join(notes),
                'reasons': reasons if reasons else []
            }

            return result

        except Exception as e:
            st.error(f"Error in evaluate_cv: {str(e)}")
            return self._create_empty_result(f"Error during evaluation: {str(e)}")

    def _create_empty_result(self, error_message):
        """Create an empty result with error message"""
        return {
            'overall_score': 0,
            'technical_skills': [],
            'matched_required_skills': [],
            'matched_nice_to_have': [],
            'missing_critical_skills': [],
            'evaluation_notes': error_message,
            'reasons': [error_message]
        }