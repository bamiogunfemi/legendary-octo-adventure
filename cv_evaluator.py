class CVEvaluator:
    def __init__(self, scoring_engine):
        self.scoring_engine = scoring_engine

    def process_cv_batch(self, cv_data, job_requirements):
        """Process a batch of CVs against job requirements"""
        results = []
        for cv in cv_data:
            result = self.scoring_engine.evaluate_cv(cv, job_requirements)
            results.append(result)
        return results

    def filter_suitable_candidates(self, results, threshold=60):
        """Filter candidates above the suitability threshold"""
        return [r for r in results if r['overall_score'] >= threshold]

    def get_top_candidates(self, results, limit=10):
        """Get top N candidates by overall score"""
        sorted_results = sorted(
            results,
            key=lambda x: x['overall_score'],
            reverse=True
        )
        return sorted_results[:limit]
