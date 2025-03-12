import re
import math
import streamlit as st
from collections import Counter

class NLPMatcher:
    def __init__(self):
        # Simple text processing without NLTK
        self.tokenize = lambda text: text.lower().split()

        # Enhanced technical skills patterns
        self.tech_skills_patterns = {
            'programming_languages': r'\b(python|java(?:script)?|typescript|go(?:lang)?|ruby|php|swift|kotlin|scala|rust|c\+\+|c#|perl|r|matlab)\b',
            'web_frameworks': r'\b(django|flask|fastapi|spring(?:boot)?|react(?:\.js)?|angular(?:js)?|vue(?:\.js)?|express(?:\.js)?|node(?:\.js)?)\b',
            'databases': r'\b(post(?:gres)?(?:sql)?|mysql|mongo(?:db)?|redis|elastic(?:search)?|cassandra|dynamo(?:db)?|oracle)\b',
            'cloud': r'\b(aws|amazon|azure|gcp|google cloud|kubernetes|k8s|docker|terraform|ansible|argo(?:cd)?)\b',
            'testing': r'\b(junit|pytest|selenium|cypress|jest|mocha|chai|testing|test automation)\b',
            'devops': r'\b(ci/cd|jenkins|travis|circle(?:ci)?|git(?:hub)?|gitlab|bitbucket|iac|helm|github actions)\b',
            'infrastructure': r'\b(kubernetes|docker|terraform|ansible|puppet|chef|aws|azure|gcp)\b',
            'api': r'\b(rest(?:ful)?(?:\s+)?api|api|graphql|webhook|http[s]?|grpc|soap|openapi|swagger)\b'
        }

        # Common variations mapping
        self.skill_variations = {
            'restful': ['rest', 'restful api', 'rest api'],
            'rest': ['restful', 'restful api', 'rest api'],
            'aws': ['amazon web services', 'amazon aws'],
            'docker': ['containerization', 'containers'],
            'kubernetes': ['k8s', 'container orchestration'],
            'postgresql': ['postgres', 'psql'],
            'mongodb': ['mongo', 'nosql'],
            'python': ['py', 'python3'],
            'javascript': ['js', 'ecmascript'],
            'typescript': ['ts'],
            'github actions': ['github workflows', 'gh actions']
        }

    def extract_technical_skills(self, text):
        """Extract technical skills from text using regex patterns"""
        if not text:
            return []

        text = text.lower()
        found_skills = set()

        # Extract skills using regex patterns
        for pattern in self.tech_skills_patterns.values():
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for match in matches:
                skill = match.group(0)
                skill = self.normalize_skill_name(skill)
                found_skills.add(skill)

        # Add variations of found skills
        expanded_skills = set()
        for skill in found_skills:
            expanded_skills.add(skill)
            if skill in self.skill_variations:
                expanded_skills.update(self.skill_variations[skill])

        return sorted(list(expanded_skills))

    def match_skills(self, candidate_skills, required_skills):
        """Match candidate skills against required skills with improved matching"""
        if not candidate_skills or not required_skills:
            return 0, []

        matched_skills = []
        total_score = 0

        # Normalize all skills
        normalized_candidate = [self.normalize_skill_name(skill) for skill in candidate_skills]
        normalized_required = [self.normalize_skill_name(skill) for skill in required_skills]

        for req_skill in required_skills:
            normalized_req = self.normalize_skill_name(req_skill)

            # Check direct match and variations
            found_match = False
            for cand_skill in normalized_candidate:
                # Direct match
                if normalized_req == cand_skill:
                    matched_skills.append(req_skill)
                    total_score += 1
                    found_match = True
                    break

                # Check variations
                if normalized_req in self.skill_variations:
                    if cand_skill in self.skill_variations[normalized_req]:
                        matched_skills.append(req_skill)
                        total_score += 1
                        found_match = True
                        break

                # Check if skill is part of a larger term
                if normalized_req in cand_skill or cand_skill in normalized_req:
                    matched_skills.append(req_skill)
                    total_score += 0.8  # Partial match score
                    found_match = True
                    break

            if not found_match:
                # Try fuzzy matching as a last resort
                best_match = (None, 0)
                for cand_skill in candidate_skills:
                    similarity = self.get_skill_similarity(cand_skill, req_skill)
                    if similarity > best_match[1]:
                        best_match = (cand_skill, similarity)

                if best_match[1] > 0.8:  # Higher threshold for fuzzy matching
                    matched_skills.append(req_skill)
                    total_score += best_match[1]

        avg_score = (total_score / len(required_skills)) * 100 if required_skills else 0
        return avg_score, matched_skills

    def normalize_skill_name(self, skill):
        """Normalize skill names to standard format"""
        if not isinstance(skill, str):
            return ''

        skill = skill.lower().strip()
        skill = re.sub(r'\s+', ' ', skill)  # Normalize whitespace
        skill = skill.replace('-', ' ')  # Normalize hyphens

        # Remove common prefixes/suffixes
        skill = re.sub(r'^(?:experienced in |proficient in |knowledge of |expertise in )', '', skill)
        skill = re.sub(r'(?:development|programming|engineer)$', '', skill)

        # Handle REST API variations
        if any(x in skill for x in ['rest', 'restful', 'rest api', 'restful api']):
            return 'rest api'

        return skill.strip()

    def get_skill_similarity(self, skill1, skill2):
        """Compute similarity between two skills"""
        if not skill1 or not skill2:
            return 0.0

        skill1 = self.normalize_skill_name(skill1)
        skill2 = self.normalize_skill_name(skill2)

        # Exact match
        if skill1 == skill2:
            return 1.0

        # Check variations
        if skill1 in self.skill_variations and skill2 in self.skill_variations[skill1]:
            return 1.0
        if skill2 in self.skill_variations and skill1 in self.skill_variations[skill2]:
            return 1.0

        # Partial match
        if skill1 in skill2 or skill2 in skill1:
            return 0.8

        # Basic string similarity as fallback
        max_len = max(len(skill1), len(skill2))
        if max_len == 0:
            return 0.0
        return 1.0 - (self._levenshtein_distance(skill1, skill2) / max_len)

    def _levenshtein_distance(self, s1, s2):
        """Calculate the Levenshtein distance between two strings"""
        if len(s1) < len(s2):
            return self._levenshtein_distance(s2, s1)

        if len(s2) == 0:
            return len(s1)

        previous_row = range(len(s2) + 1)
        for i, c1 in enumerate(s1):
            current_row = [i + 1]
            for j, c2 in enumerate(s2):
                insertions = previous_row[j + 1] + 1
                deletions = current_row[j] + 1
                substitutions = previous_row[j] + (c1 != c2)
                current_row.append(min(insertions, deletions, substitutions))
            previous_row = current_row

        return previous_row[-1]

    def compute_tf_idf(self, text, document_set):
        """Compute TF-IDF scores for terms"""
        # Term frequency in the text
        tf = Counter(self.tokenize(text))

        # Inverse document frequency
        idf = {}
        doc_count = len(document_set)

        for term in tf:
            doc_with_term = sum(1 for doc in document_set if term in self.tokenize(doc))
            idf[term] = math.log(doc_count / (1 + doc_with_term))

        # Compute TF-IDF
        tf_idf = {term: freq * idf[term] for term, freq in tf.items()}
        return tf_idf

    def match_role(self, candidate_role, required_role):
        """Advanced role matching using context"""
        if not candidate_role or not required_role:
            return 0, "No role information provided"

        # Preprocess roles
        candidate_tokens = set(self.tokenize(candidate_role))
        required_tokens = set(self.tokenize(required_role))

        # Direct token overlap
        overlap_score = len(candidate_tokens & required_tokens) / len(required_tokens) if required_tokens else 0

        # Context matching
        context_score = self.get_skill_similarity(candidate_role, required_role)

        # Combine scores
        final_score = (overlap_score * 0.6 + context_score * 0.4) * 100

        return final_score, "Role context match: {:.1f}%".format(final_score)

    def preprocess_text(self, text):
        """Preprocess text for comparison"""
        if not isinstance(text, str):
            return []

        text = text.lower()
        text = re.sub(r'[^\w\s]', ' ', text)
        return self.tokenize(text)