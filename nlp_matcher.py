import re
import math
import streamlit as st
from collections import Counter

class NLPMatcher:
    def __init__(self):
        # Define skill variations and synonyms
        self.skill_variations = {
            'restful api': ['rest api', 'restful', 'rest', 'api development', 'web api', 'http api'],
            'aws': ['amazon web services', 'amazon aws', 'aws cloud'],
            'docker': ['containerization', 'containers', 'docker containers'],
            'kubernetes': ['k8s', 'container orchestration', 'kubernetes cluster'],
            'postgresql': ['postgres', 'psql', 'database functions', 'database triggers'],
            'mongodb': ['mongo', 'nosql', 'document database'],
            'python': ['py', 'python3', 'django', 'fastapi', 'flask'],
            'javascript': ['js', 'ecmascript', 'react', 'node.js'],
            'typescript': ['ts'],
            'github actions': ['github workflows', 'gh actions', 'ci/cd'],
            'testing': ['unit testing', 'integration testing', 'test automation', 'pytest'],
            'webhooks': ['webhook integration', 'web hooks', 'event hooks'],
            'microservices': ['microservice architecture', 'service oriented', 'distributed systems'],
            'api': ['api development', 'api integration', 'rest api', 'graphql', 'grpc']
        }

        # Technical skills patterns with broader matches
        self.tech_skills_patterns = {
            'programming': r'\b(python|django|fastapi|flask|java(?:script)?|typescript|go(?:lang)?|ruby|php|swift|kotlin|scala|rust|c\+\+|c#|perl|r|matlab)\b',
            'web_tech': r'\b(django rest framework|react(?:\.js)?|angular(?:js)?|vue(?:\.js)?|express(?:\.js)?|node(?:\.js)?|next(?:\.js)?|nuxt|gatsby|svelte)\b',
            'databases': r'\b(post(?:gres)?(?:sql)?|mysql|mongo(?:db)?|redis|elastic(?:search)?|cassandra|dynamo(?:db)?|oracle|database functions|triggers|orm)\b',
            'cloud': r'\b(aws|amazon|azure|gcp|google cloud|kubernetes|k8s|docker|terraform|ansible|argo(?:cd)?|cloudformation|openstack|heroku)\b',
            'testing': r'\b(unit test|integration test|pytest|selenium|cypress|jest|mocha|chai|testing|test automation|playwright|testcafe)\b',
            'devops': r'\b(ci/cd|jenkins|travis|circle(?:ci)?|git(?:hub)?|gitlab|bitbucket|iac|helm|github actions|terraform|cloudformation)\b',
            'data_science': r'\b(scikit[-\s]?learn|pandas|numpy|matplotlib|tensorflow|pytorch|machine learning|deep learning|statistical analysis)\b',
            'api': r'\b(rest(?:ful)?(?:\s+)?api|api development|graphql|webhook|http[s]?|grpc|soap|openapi|swagger|api integration|3rd party api)\b',
            'architecture': r'\b(microservices|event[-\s]driven|service[-\s]oriented|distributed systems|scalable|high[-\s]availability)\b'
        }

    def extract_technical_skills(self, text):
        """Extract technical skills from text using enhanced pattern matching"""
        if not text:
            return []

        text = text.lower()
        found_skills = set()

        # Extract skills using patterns
        for category, pattern in self.tech_skills_patterns.items():
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for match in matches:
                skill = match.group(0).lower().strip()
                # Clean up the skill name
                skill = re.sub(r'\s+', ' ', skill)
                found_skills.add(skill)

        # Add variations and related skills
        expanded_skills = set()
        for skill in found_skills:
            expanded_skills.add(skill)
            # Check variations and synonyms
            for base_skill, variations in self.skill_variations.items():
                if skill in variations or skill == base_skill:
                    expanded_skills.add(base_skill)
                    expanded_skills.update(variations)

        # Clean and normalize skills
        normalized_skills = set()
        for skill in expanded_skills:
            normalized = self.normalize_skill_name(skill)
            if normalized:
                normalized_skills.add(normalized)

        return sorted(list(normalized_skills))

    def match_skills(self, candidate_skills, required_skills):
        """Match candidate skills against required skills with context awareness"""
        if not candidate_skills or not required_skills:
            return 0, []

        matched_skills = []
        total_score = 0

        # Debug logging
        st.write("\nMatching skills:")
        st.write("Candidate skills:", ", ".join(candidate_skills))
        st.write("Required skills:", ", ".join(required_skills))

        for req_skill in required_skills:
            req_lower = req_skill.lower().strip()

            # Direct match
            if req_lower in [s.lower() for s in candidate_skills]:
                matched_skills.append(req_skill)
                total_score += 1
                continue

            # Check variations and related skills
            matched = False
            for cand_skill in candidate_skills:
                cand_lower = cand_skill.lower()

                # Check if the skills are variations of each other
                if req_lower in self.skill_variations:
                    if cand_lower in self.skill_variations[req_lower]:
                        matched_skills.append(req_skill)
                        total_score += 1
                        matched = True
                        break

                # Check if candidate skill contains required skill
                if req_lower in cand_lower or any(var in cand_lower for var in self.skill_variations.get(req_lower, [])):
                    matched_skills.append(req_skill)
                    total_score += 0.8
                    matched = True
                    break

            if not matched:
                # Try fuzzy matching with context
                best_match = self.find_best_match(req_skill, candidate_skills)
                if best_match[1] >= 0.7:  # Higher threshold for fuzzy matches
                    matched_skills.append(req_skill)
                    total_score += best_match[1]

        avg_score = (total_score / len(required_skills)) * 100 if required_skills else 0
        return avg_score, list(set(matched_skills))

    def normalize_skill_name(self, skill):
        """Normalize skill names to standard format"""
        if not isinstance(skill, str):
            return ''

        skill = skill.lower().strip()
        skill = re.sub(r'\s+', ' ', skill)
        skill = skill.replace('-', ' ')

        # Remove common prefixes/suffixes
        skill = re.sub(r'^(?:experienced in |proficient in |knowledge of |expertise in )', '', skill)
        skill = re.sub(r'(?:development|programming|engineer)$', '', skill)

        # Standardize common variations
        replacements = {
            'restful': 'restful api',
            'rest': 'restful api',
            'api development': 'restful api',
            'web api': 'restful api',
            'js': 'javascript',
            'py': 'python',
            'postgres': 'postgresql',
            'k8s': 'kubernetes'
        }

        return replacements.get(skill, skill).strip()

    def find_best_match(self, skill, candidates):
        """Find the best matching skill from candidates"""
        best_match = (None, 0)
        skill_lower = skill.lower()

        for candidate in candidates:
            candidate_lower = candidate.lower()

            # Check for exact match
            if skill_lower == candidate_lower:
                return (candidate, 1.0)

            # Check variations
            if skill_lower in self.skill_variations:
                if candidate_lower in self.skill_variations[skill_lower]:
                    return (candidate, 1.0)

            # Calculate similarity score
            similarity = self.get_skill_similarity(skill_lower, candidate_lower)
            if similarity > best_match[1]:
                best_match = (candidate, similarity)

        return best_match

    def get_skill_similarity(self, skill1, skill2):
        """Compute similarity between two skills"""
        if not skill1 or not skill2:
            return 0.0

        # Normalize skills
        skill1 = self.normalize_skill_name(skill1)
        skill2 = self.normalize_skill_name(skill2)

        # Exact match
        if skill1 == skill2:
            return 1.0

        # Check variations
        if skill1 in self.skill_variations and skill2 in self.skill_variations[skill1]:
            return 1.0

        # Partial match
        if skill1 in skill2 or skill2 in skill1:
            return 0.8

        # Levenshtein distance as last resort
        return 1.0 - (self._levenshtein_distance(skill1, skill2) / max(len(skill1), len(skill2)))

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

    def tokenize(self, text):
        return text.lower().split()