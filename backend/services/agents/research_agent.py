from __future__ import annotations
from .base import AgentFinding, BaseAgent, num

class ResearchAgent(BaseAgent):
    name='research_agent'
    role='auto research, hypothesis and edge discovery'
    def findings(self,snapshot):
        out=[]
        leagues=(snapshot.get('analytics') or {}).get('league_performance') or []
        markets=(snapshot.get('analytics') or {}).get('market_performance') or []
        for league in leagues[:5]:
            if num(league.get('avg_ev_pct'),0)>1 and league.get('signals',0)>=3:
                out.append(AgentFinding(self.name,'research_hypothesis','info',0.61,'Hipótese de liga promissora',f"{league.get('name')} mostra EV positivo com amostra mínima.",{'league':league},'Criar estudo histórico dessa liga por mercado, odds range e horário.'))
                break
        combo=[]
        if leagues and markets:
            combo={'league':leagues[0].get('name'),'market':markets[0].get('name'),'evidence':'top buckets atuais por EV médio'}
            out.append(AgentFinding(self.name,'combo_research','info',0.57,'Combinação candidata para pesquisa',f"Cruzar liga {combo['league']} com mercado {combo['market']} pode revelar edge.",combo,'Rodar backtest segmentado antes de qualquer aumento de exposição.'))
        return out
