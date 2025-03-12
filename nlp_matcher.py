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
            'programming_languages': r'\b(python|java(?:script)?|typescript|go(?:lang)?|ruby|php|swift|kotlin|scala|rust|c\+\+|c#|perl|r|matlab|cobol|assembly|haskell|f#|clojure|erlang)\b',
            'web_frameworks': r'\b(django|flask|fastapi|spring(?:boot)?|react(?:\.js)?|angular(?:js)?|vue(?:\.js)?|express(?:\.js)?|node(?:\.js)?|next(?:\.js)?|nuxt|gatsby|svelte)\b',
            'databases': r'\b(post(?:gres)?(?:sql)?|mysql|mongo(?:db)?|redis|elastic(?:search)?|cassandra|dynamo(?:db)?|oracle|cockroach(?:db)?|neo4j|sqlite|mariadb)\b',
            'cloud': r'\b(aws|amazon|azure|gcp|google cloud|kubernetes|k8s|docker|terraform|ansible|argo(?:cd)?|cloudformation|openstack)\b',
            'testing': r'\b(junit|pytest|selenium|cypress|jest|mocha|chai|testing|test automation|playwright|testcafe)\b',
            'devops': r'\b(ci/cd|jenkins|travis|circle(?:ci)?|git(?:hub)?|gitlab|bitbucket|iac|helm|github actions|spinnaker|harness)\b',
            'infrastructure': r'\b(kubernetes|docker|terraform|ansible|puppet|chef|aws|azure|gcp|prometheus|grafana|istio|consul)\b',
            'api': r'\b(rest(?:ful)?|api|graphql|webhook|http[s]?|grpc|soap|openapi|swagger)\b',
            'security': r'\b(oauth|jwt|saml|ssl|tls|vpn|encryption|authentication|authorization|firewall)\b',
            'data_science': r'\b(tensorflow|pytorch|keras|scikit-learn|pandas|numpy|matplotlib|tableau|power bi|machine learning|deep learning)\b'
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

        # Additional common tech terms
        common_tech_terms = {
            'rest', 'restful', 'api', 'graphql', 'microservices', 'oauth',
            'jwt', 'saml', 'http', 'https', 'webhooks', 'soa',
            'soap', 'grpc', 'openapi', 'swagger', 'postman',
            'iac', 'github actions', 'argocd', 'kubernetes',
            'docker', 'aws', 'azure', 'gcp', 'testing', 'ci/cd',
            'machine learning', 'deep learning', 'nlp', 'computer vision',
            'data science', 'big data', 'cloud computing', 'devops',
            'microservices', 'serverless', 'blockchain', 'web3',
            'cybersecurity', 'networking', 'infrastructure'
        }

        # Simple word matching
        words = self.tokenize(text)
        for i, word in enumerate(words):
            if word in common_tech_terms:
                found_skills.add(word)
            # Check for multi-word terms
            if i < len(words) - 1:
                two_words = f"{word} {words[i+1]}"
                if two_words in common_tech_terms:
                    found_skills.add(two_words)
            if i < len(words) - 2:
                three_words = f"{word} {words[i+1]} {words[i+2]}"
                if three_words in common_tech_terms:
                    found_skills.add(three_words)

        return sorted(list(found_skills))

    def match_skills(self, candidate_skills, required_skills):
        """Match candidate skills against required skills"""
        if not candidate_skills or not required_skills:
            return 0, []

        matched_skills = []
        total_score = 0

        # Normalize skills
        normalized_candidate = [self.normalize_skill_name(skill) for skill in candidate_skills]
        normalized_required = [self.normalize_skill_name(skill) for skill in required_skills]

        for req_skill in required_skills:
            normalized_req = self.normalize_skill_name(req_skill)

            # Try exact match first
            if normalized_req in normalized_candidate:
                matched_skills.append(req_skill)
                total_score += 1
                continue

            # Try simple string comparison
            best_match = (None, 0)
            for cand_skill in candidate_skills:
                # Calculate string similarity
                if cand_skill.lower() in req_skill.lower() or req_skill.lower() in cand_skill.lower():
                    similarity = 0.8
                else:
                    # Simple character-based similarity
                    longer = max(len(cand_skill), len(req_skill))
                    if longer == 0:
                        similarity = 0
                    else:
                        similarity = 1 - (self._levenshtein_distance(cand_skill.lower(), req_skill.lower()) / longer)

                if similarity > best_match[1]:
                    best_match = (cand_skill, similarity)

            if best_match[1] > 0.5:
                matched_skills.append(best_match[0])
                total_score += best_match[1]

        avg_score = (total_score / len(required_skills)) * 100 if required_skills else 0
        return avg_score, matched_skills

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

    def normalize_skill_name(self, skill):
        """Normalize skill names to standard format"""
        if not isinstance(skill, str):
            return ''

        replacements = {
            'javascript': 'javascript',
            'js': 'javascript',
            'typescript': 'typescript',
            'py': 'python',
            'golang': 'go',
            'nodejs': 'node.js',
            'reactjs': 'react',
            'vuejs': 'vue',
            'postgres': 'postgresql',
            'k8s': 'kubernetes',
            'github actions': 'github actions',
            'restful': 'rest',
            'restful api': 'rest api',
            'argo cd': 'argocd',
            'ci/cd': 'ci/cd',
            'aws cloud': 'aws',
            'amazon web services': 'aws',
            'google cloud platform': 'gcp',
            'automated testing': 'testing',
            'test automation': 'testing',
            'unit testing': 'testing',
            'integration testing': 'testing',
            'machine learning': 'ml',
            'deep learning': 'dl',
            'artificial intelligence': 'ai',
            'natural language processing': 'nlp'
        }

        skill = skill.lower().strip()
        skill = re.sub(r'^(?:experienced in |proficient in |knowledge of |expertise in )', '', skill)
        skill = re.sub(r'(?:development|programming|engineer)$', '', skill)
        skill = skill.strip()

        return replacements.get(skill, skill)

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

    def get_skill_similarity(self, skill1, skill2):
        """Compute similarity between two skills"""
        if not skill1 or not skill2:
            return 0.0

        # Normalize both skills
        skill1 = self.normalize_skill_name(skill1)
        skill2 = self.normalize_skill_name(skill2)

        # Exact match after normalization
        if skill1 == skill2:
            return 1.0

        # Simple string comparison
        if skill1 in skill2 or skill2 in skill1:
            return 0.8
        # Use basic string similarity
        max_len = max(len(skill1), len(skill2))
        if max_len == 0:
            return 0.0
        distance = self._levenshtein_distance(skill1, skill2)
        return 1.0 - (distance / max_len)