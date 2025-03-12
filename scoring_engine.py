import pandas as pd
import nltk
from nltk.tokenize import word_tokenize
from nltk.corpus import stopwords
import re
from nlp_matcher import NLPMatcher
from ai_helper import AIHelper
import streamlit as st

class ScoringEngine:
    def __init__(self):
        self.nlp_matcher = NLPMatcher()
        self.ai_helper = AIHelper()
        self.stop_words = set(stopwords.words('english'))

    def evaluate_cv(self, cv_data, job_requirements):
        """Main evaluation function with detailed reasoning"""
        try:
            # Get CV text
            cv_text = cv_data.get('cv_text', '')

            # Debug: Log CV text length
            st.write(f"\nProcessing CV text: {len(cv_text)} characters")
            if cv_text:
                st.write("First 200 characters of CV text:")
                st.write(cv_text[:200] + "..." if len(cv_text) > 200 else cv_text)
            else:
                st.warning("No CV text content available for analysis")
                return {
                    'overall_score': 0,
                    'matched_required_skills': [],
                    'matched_nice_to_have': [],
                    'missing_critical_skills': [],
                    'evaluation_notes': 'No CV content available for analysis',
                    'reasons': ['No CV content available']
                }

            # Use AI to analyze CV content
            ai_analysis = self.ai_helper.analyze_cv_content(cv_text, job_requirements)

            # Calculate experience score
            exp_score = 100 if cv_data.get('years_experience', 0) >= job_requirements.get('required_years', 0) else 50

            # Calculate overall score
            overall_score = (ai_analysis['skill_match_score'] * 0.7 + exp_score * 0.3)

            # Compile results
            result = {
                'overall_score': overall_score,
                'matched_required_skills': ai_analysis['matched_required_skills'],
                'matched_nice_to_have': ai_analysis['matched_nice_to_have'],
                'missing_critical_skills': ai_analysis['missing_critical_skills'],
                'evaluation_notes': '; '.join(ai_analysis['analysis_notes']),
                'reasons': []
            }

            # Add failure reasons if score is low
            if overall_score < 60:
                if ai_analysis['skill_match_score'] < 60:
                    result['reasons'].append(f"Missing critical skills: {', '.join(ai_analysis['missing_critical_skills'])}")
                if exp_score < 60:
                    result['reasons'].append("Insufficient years of experience")

            # Debug: Log evaluation results
            st.write("\nEvaluation Results:")
            st.write(f"Overall Score: {overall_score}")
            st.write(f"Matched Required Skills: {result['matched_required_skills']}")
            st.write(f"Missing Critical Skills: {result['missing_critical_skills']}")

            return result

        except Exception as e:
            st.error(f"Error in evaluate_cv: {str(e)}")
            return {
                'overall_score': 0,
                'matched_required_skills': [],
                'matched_nice_to_have': [],
                'missing_critical_skills': [],
                'evaluation_notes': f'Error during evaluation: {str(e)}',
                'reasons': ['Error during evaluation: ' + str(e)]
            }