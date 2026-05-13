class ExecutivePerformanceAgent:
    def argue(self, context):
        score=((context.get('executive_observability') or {}).get('decision_quality_score') or .5); return {'agent':'executive_performance_agent','vote':'support' if score>=.6 else 'contest','position':'optimize decision quality feedback loops','priority':'performance_quality'}
