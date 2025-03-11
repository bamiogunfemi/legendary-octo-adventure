import pandas as pd
import nltk
from nltk.tokenize import word_tokenize
from nltk.corpus import stopwords
import re
from nlp_matcher import NLPMatcher

class ScoringEngine:
    def __init__(self):
        # Initialize NLP matcher
        self.nlp_matcher = NLPMatcher()
        self.stop_words = set(stopwords.words('english'))

    def preprocess_text(self, text):
        """Preprocess text for analysis"""
        if not isinstance(text, str):
            return ""
        text = text.lower()
        text = re.sub(r'[^\w\s]', ' ', text)
        tokens = word_tokenize(text)
        tokens = [t for t in tokens if t not in self.stop_words]
        return " ".join(tokens)

    def check_core_alignment(self, candidate_role, required_role):
        """Check core role alignment using advanced NLP"""
        try:
            alignment_score, reason = self.nlp_matcher.match_role(
                str(candidate_role),
                str(required_role)
            )
            return alignment_score
        except Exception as e:
            print(f"Error in core alignment check: {str(e)}")
            return 0

    def score_skills_match(self, candidate_skills, required_skills):
        """Score skills match using advanced NLP"""
        try:
            if not candidate_skills or not required_skills:
                return 0, "No skills provided"

            # Clean and normalize skills
            candidate_skills = [s.strip() for s in candidate_skills if s.strip()]
            required_skills = [s.strip() for s in required_skills if s.strip()]

            if not required_skills:
                return 50, "No required skills specified"

            # Get advanced NLP match score
            match_score, matched_skills = self.nlp_matcher.match_skills(
                candidate_skills,
                required_skills
            )

            # Generate detailed feedback
            if match_score >= 80:
                return match_score, "Strong match with required skills"
            elif match_score >= 60:
                return match_score, f"Partial match with {len(matched_skills)} out of {len(required_skills)} required skills"
            else:
                missing_skills = set(required_skills) - {m['matched'] for m in matched_skills}
                return match_score, f"Missing key skills: {', '.join(missing_skills)}"

        except Exception as e:
            print(f"Error in skills match: {str(e)}")
            return 0, "Error evaluating skills"

    def score_experience_match(self, years_exp, required_years):
        """Score experience match"""
        try:
            years_exp = float(str(years_exp).replace('+', '')) if years_exp else 0
            required_years = float(str(required_years).replace('+', '')) if required_years else 1
        except (ValueError, TypeError):
            return 0, "Invalid years format"

        if years_exp >= required_years:
            return 100, f"Meets required {required_years} years of experience"
        elif years_exp >= required_years * 0.75:
            return 75, f"Close to required experience ({years_exp}/{required_years} years)"
        elif years_exp >= required_years * 0.5:
            return 50, f"Partial experience ({years_exp}/{required_years} years)"
        else:
            return 25, f"Insufficient experience ({years_exp}/{required_years} years)"

    def evaluate_cv(self, cv_data, job_requirements):
        """Main evaluation function with detailed reasoning"""
        try:
            reasons = []

            # Check core role alignment with advanced NLP
            alignment_score = self.check_core_alignment(
                cv_data.get('current_role', ''),
                job_requirements.get('role', '')
            )

            # Skills evaluation with advanced NLP
            skills_score, skills_reason = self.score_skills_match(
                cv_data.get('skills', []),
                job_requirements.get('required_skills', [])
            )
            if skills_score < 50:
                reasons.append(f"Skills: {skills_reason}")

            # Experience evaluation
            exp_score, exp_reason = self.score_experience_match(
                cv_data.get('years_experience', 0),
                job_requirements.get('required_years', 1)
            )
            if exp_score < 50:
                reasons.append(f"Experience: {exp_reason}")

            # Apply alignment cap if needed
            if alignment_score < 50:
                reasons.append(f"Role Alignment: Current role ({cv_data.get('current_role', 'Not specified')}) differs significantly from required role ({job_requirements.get('role', 'Not specified')})")
                skills_score = min(skills_score, 50)
                exp_score = min(exp_score, 50)

            # Calculate overall score
            overall_score = (skills_score + exp_score) / 2

            result = {
                'overall_score': overall_score,
                'skills_score': skills_score,
                'experience_score': exp_score,
                'alignment_score': alignment_score,
                'reasons': reasons if reasons else []
            }

            return result

        except Exception as e:
            print(f"Error in evaluate_cv: {str(e)}")
            return {
                'overall_score': 0,
                'skills_score': 0,
                'experience_score': 0,
                'alignment_score': 0,
                'reasons': ['Error during evaluation: ' + str(e)]
            }