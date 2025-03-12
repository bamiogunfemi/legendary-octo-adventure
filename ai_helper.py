import nltk
from nltk.tokenize import word_tokenize, sent_tokenize
from nltk.corpus import stopwords
from nltk.stem import WordNetLemmatizer
import re
import streamlit as st
from nlp_matcher import NLPMatcher

# Initialize NLTK data
try:
    nltk.data.find('tokenizers/punkt')
except LookupError:
    nltk.download('punkt', quiet=True)
try:
    nltk.data.find('corpora/stopwords')
except LookupError:
    nltk.download('stopwords', quiet=True)
try:
    nltk.data.find('corpora/wordnet')
except LookupError:
    nltk.download('wordnet', quiet=True)

class AIHelper:
    def __init__(self):
        self.nlp_matcher = NLPMatcher()
        self.stop_words = set(stopwords.words('english'))
        self.lemmatizer = WordNetLemmatizer()

    def analyze_cv_content(self, cv_text, job_requirements):
        """
        Analyze CV content using NLTK to extract skills and match with requirements.
        """
        try:
            # Log the analysis start
            st.write("\nStarting CV Analysis...")

            # Extract all technical skills from CV
            technical_skills = self.nlp_matcher.extract_technical_skills(cv_text)

            # Get required and nice-to-have skills
            required_skills = job_requirements.get('required_skills', [])
            nice_to_have_skills = job_requirements.get('nice_to_have_skills', [])

            # Match skills using NLP matcher
            skill_match_score, matched_skills = self.nlp_matcher.match_skills(
                technical_skills,
                required_skills
            )

            # Get matched required skills
            matched_required = [match['matched'] for match in matched_skills]

            # Match nice-to-have skills
            _, nice_to_have_matches = self.nlp_matcher.match_skills(
                technical_skills,
                nice_to_have_skills
            )
            matched_nice_to_have = [match['matched'] for match in nice_to_have_matches]

            # Find missing critical skills
            missing_critical = list(set(required_skills) - set(matched_required))

            # Generate analysis notes
            analysis_notes = []
            if matched_required:
                analysis_notes.append(f"Matched {len(matched_required)} out of {len(required_skills)} required skills")
            if matched_nice_to_have:
                analysis_notes.append(f"Has {len(matched_nice_to_have)} nice-to-have skills")
            if missing_critical:
                analysis_notes.append(f"Missing {len(missing_critical)} critical skills")

            # Prepare result
            result = {
                "technical_skills_found": technical_skills,
                "matched_required_skills": matched_required,
                "matched_nice_to_have": matched_nice_to_have,
                "missing_critical_skills": missing_critical,
                "skill_match_score": skill_match_score,
                "analysis_notes": analysis_notes
            }

            # Log the analysis results
            st.write("\nAnalysis Results:")
            st.write("Technical Skills Found:", result['technical_skills_found'])
            st.write("Skills Match Score:", result['skill_match_score'])
            st.write("Analysis Notes:", result['analysis_notes'])

            return result

        except Exception as e:
            st.error(f"Error in CV analysis: {str(e)}")
            return {
                "technical_skills_found": [],
                "matched_required_skills": [],
                "matched_nice_to_have": [],
                "missing_critical_skills": [],
                "skill_match_score": 0,
                "analysis_notes": [f"Error in analysis: {str(e)}"]
            }