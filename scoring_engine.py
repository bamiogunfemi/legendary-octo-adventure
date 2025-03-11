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

    def score_skills_match(self, candidate_skills, required_skills, cv_text=None, nice_to_have_skills=None):
        """Score skills match using advanced NLP with bonus for nice-to-have skills"""
        try:
            if not candidate_skills and not cv_text:
                return 0, "No skills provided"

            # Extract technical skills from CV text if available
            extracted_skills = []
            if cv_text:
                extracted_skills = self.nlp_matcher.extract_technical_skills(cv_text)

            # Combine extracted skills with provided skills
            all_candidate_skills = list(set(
                [s.strip().lower() for s in candidate_skills if s.strip()] +
                [s.strip().lower() for s in extracted_skills if s.strip()]
            ))

            # Clean and normalize required skills
            required_skills = [s.strip().lower() for s in required_skills if s.strip()]
            nice_to_have_skills = [s.strip().lower() for s in (nice_to_have_skills or [])] if nice_to_have_skills else []

            if not required_skills:
                return 50, "No required skills specified"

            # Get required skills match score
            match_score, matched_skills = self.nlp_matcher.match_skills(
                all_candidate_skills,
                required_skills
            )

            # Calculate bonus points for nice-to-have skills (up to 20% bonus)
            bonus_score = 0
            if nice_to_have_skills:
                _, nice_to_have_matches = self.nlp_matcher.match_skills(
                    all_candidate_skills,
                    nice_to_have_skills
                )
                # Each nice-to-have skill adds up to 5 points (max 20)
                bonus_score = min(len(nice_to_have_matches) * 5, 20)

            # Apply bonus score
            final_score = min(match_score + bonus_score, 100)

            # Return all found skills for display
            return final_score, {
                'matched_required': [m['matched'] for m in matched_skills],
                'all_skills': all_candidate_skills,
                'score_details': f"Matched {len(matched_skills)} out of {len(required_skills)} required skills"
            }

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
            notes = []

            # Check core role alignment
            alignment_score = self.check_core_alignment(
                cv_data.get('current_role', ''),
                job_requirements.get('role', '')
            )

            # Skills evaluation with detailed matching
            skills_score, skills_result = self.score_skills_match(
                cv_data.get('skills', []),
                job_requirements.get('required_skills', []),
                cv_data.get('cv_text', ''),
                job_requirements.get('nice_to_have_skills', [])
            )

            # Process skill matching results
            matched_required = []
            matched_nice_to_have = []
            missing_critical = []

            if isinstance(skills_result, dict):
                all_skills = set(skills_result.get('all_skills', []))
                required_skills = set(job_requirements.get('required_skills', []))
                nice_to_have = set(job_requirements.get('nice_to_have_skills', []))

                # Find matched and missing skills
                matched_required = list(all_skills.intersection(required_skills))
                matched_nice_to_have = list(all_skills.intersection(nice_to_have))
                missing_critical = list(required_skills - all_skills)

                # Add to notes
                if matched_required:
                    notes.append(f"Matches {len(matched_required)} required skills")
                if matched_nice_to_have:
                    notes.append(f"Has {len(matched_nice_to_have)} nice-to-have skills")
                if missing_critical:
                    notes.append(f"Missing {len(missing_critical)} critical skills")

            if skills_score < 50:
                reasons.append(f"Skills: Missing critical skills")

            # Experience evaluation
            exp_score, exp_reason = self.score_experience_match(
                cv_data.get('years_experience', 0),
                job_requirements.get('required_years', 1)
            )
            if exp_score < 50:
                reasons.append(f"Experience: {exp_reason}")
            else:
                notes.append(exp_reason)

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
                'matched_required_skills': matched_required,
                'matched_nice_to_have': matched_nice_to_have,
                'missing_critical_skills': missing_critical,
                'evaluation_notes': '; '.join(notes),
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
                'matched_required_skills': [],
                'matched_nice_to_have': [],
                'missing_critical_skills': [],
                'evaluation_notes': f'Error during evaluation: {str(e)}',
                'reasons': ['Error during evaluation: ' + str(e)]
            }