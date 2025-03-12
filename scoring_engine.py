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

            # Extract technical skills from CV content
            extracted_skills = self.nlp_matcher.extract_technical_skills(cv_text)

            # Log extracted skills
            st.write("\nExtracted Skills:", extracted_skills)

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
                matched_required = [match['matched'] for match in skills_result]

                # Find missing critical skills
                required_skills = set(job_requirements.get('required_skills', []))
                missing_critical = list(required_skills - set(matched_required))

                # Check nice-to-have skills
                nice_to_have = set(job_requirements.get('nice_to_have_skills', []))
                matched_nice_to_have = list(set(all_skills) & nice_to_have)

                # Add to notes
                if matched_required:
                    notes.append(f"Matches {len(matched_required)} required skills")
                if matched_nice_to_have:
                    notes.append(f"Has {len(matched_nice_to_have)} nice-to-have skills")
                if missing_critical:
                    notes.append(f"Missing {len(missing_critical)} critical skills")
            else:
                matched_required = []
                matched_nice_to_have = []
                missing_critical = []

            # Parse experience from CV text
            exp_score = 100 if cv_data.get('years_experience', 0) >= job_requirements.get('required_years', 0) else 50

            # Calculate overall score
            overall_score = (skills_score * 0.7 + exp_score * 0.3)  # Weight skills more heavily

            # Compile results
            result = {
                'overall_score': overall_score,
                'matched_required_skills': matched_required,
                'matched_nice_to_have': matched_nice_to_have,
                'missing_critical_skills': missing_critical,
                'evaluation_notes': '; '.join(notes),
                'reasons': reasons if reasons else []
            }

            # Log final evaluation
            st.write("\nFinal Evaluation:")
            st.write(f"Overall Score: {overall_score:.2f}%")
            st.write("Matched Required Skills:", matched_required)
            st.write("Nice-to-have Skills:", matched_nice_to_have)
            st.write("Missing Critical Skills:", missing_critical)

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