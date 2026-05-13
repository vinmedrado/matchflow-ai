class ExecutiveRiskAgent:
    def argue(self, context):
        gov=context.get('governance') or {}; return {'agent':'executive_risk_agent','vote':'contest' if gov.get('safe_mode') else 'support','position':'limit autonomy when governance blocks exist','priority':'bankroll_protection'}
