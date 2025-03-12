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

            # Get CV text
            cv_text = cv_data.get('cv_text', '')
            if not cv_text:
                st.warning("No CV text content available for analysis")
                return self._create_empty_result("No CV content available")

            # Display required skills from job description
            st.write("\nRequired Skills:", ", ".join(job_requirements.get('required_skills', [])))

            # Extract technical skills from CV content
            extracted_skills = self.nlp_matcher.extract_technical_skills(cv_text)

            # Combine with any provided skills
            all_skills = list(set(
                extracted_skills + 
                [s.strip().lower() for s in cv_data.get('skills', []) if s.strip()]
            ))

            # Update CV data with extracted skills
            cv_data['skills'] = all_skills

            # Skills evaluation with detailed matching
            skills_score, skills_result = self.nlp_matcher.match_skills(
                all_skills,
                job_requirements.get('required_skills', [])
            )

            # Process skill matching results
            if isinstance(skills_result, list):
                matched_required = [match for match in skills_result]

                # Find missing critical skills
                required_skills = set(job_requirements.get('required_skills', []))
                missing_critical = list(required_skills - set(matched_required))

                # Check nice-to-have skills
                nice_to_have = set(job_requirements.get('nice_to_have_skills', []))
                matched_nice_to_have = list(set(all_skills) & nice_to_have)

                # Display skills matching results
                st.write("\nRequired Skills Found:", ", ".join(matched_required) if matched_required else "None")
                if missing_critical:
                    st.write("Missing Required Skills:", ", ".join(missing_critical))

                # Add to notes
                if matched_required:
                    notes.append(f"Required skills found: {', '.join(matched_required)}")
                if missing_critical:
                    notes.append(f"Missing skills: {', '.join(missing_critical)}")

            # Calculate overall score
            overall_score = (skills_score * 0.7)  # Weight skills more heavily

            # Compile results
            result = {
                'overall_score': overall_score,
                'matched_required_skills': matched_required,
                'matched_nice_to_have': matched_nice_to_have,
                'missing_critical_skills': missing_critical,
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
            'matched_required_skills': [],
            'matched_nice_to_have': [],
            'missing_critical_skills': [],
            'evaluation_notes': error_message,
            'reasons': [error_message]
        }