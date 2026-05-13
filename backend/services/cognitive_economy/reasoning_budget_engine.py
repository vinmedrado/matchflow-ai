from __future__ import annotations
class ReasoningBudgetEngine:
    def budget(self, request_type='dashboard'):
        budgets={'dashboard': {'max_depth':2,'max_agents':6,'max_items':40}, 'ask': {'max_depth':3,'max_agents':6,'max_items':80}}
        return budgets.get(request_type, budgets['dashboard'])
