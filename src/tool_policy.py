"""Offline deterministic tool routing over a known contract registry.

This is an executable policy, not an LLM planner or a claim about a production agent.
The structured tool receives query text and public registry fields only, never labels.
"""
import re
from collections import defaultdict
from common import tok


def normal(text):
    return " ".join(tok(text))


class ToolPolicy:
    def __init__(self, docs):
        self.by_title=defaultdict(list)
        self.trigrams=defaultdict(set)
        for doc in docs:
            title=normal(doc["title"])
            self.by_title[title].append(doc)
            words=title.split()
            for start in range(max(1,len(words)-2)):
                self.trigrams[tuple(words[start:start+3])].add(title)

    def route(self, query):
        text=normal(query)
        quoted=re.findall(r"['\"]([^'\"]+)['\"]",query)
        quoted=[normal(x) for x in quoted if normal(x)]
        words=text.split()
        possible=set()
        for start in range(max(1,len(words)-2)):
            possible.update(self.trigrams.get(tuple(words[start:start+3]),set()))
        titles={t for t in possible if t in text}
        titles.update(t for t in quoted if t in self.by_title)
        matched=[]
        dates=re.findall(r"\b\d{4}-\d{2}-\d{2}\b",query)
        for title in sorted(titles):
            candidates=[]
            for doc in self.by_title[title]:
                entities=[doc["buyer"]]+doc["suppliers"]
                identities=sum(normal(x) in text for x in entities if normal(x))
                if not identities:
                    continue
                if dates and not all(date in [doc.get("award_date"),doc.get("contract_start"),doc.get("contract_end")] for date in dates):
                    continue
                candidates.append((doc["doc_id"],identities))
            if candidates:
                best=max(x[1] for x in candidates)
                matched.extend((d,2.+score) for d,score in candidates if score==best)
        if matched:
            return "structured",list(dict(matched).items())
        if quoted:
            return "abstain",[]
        return "retrieve",None

    def run(self,queries,fallback):
        ranks=[]
        routes=[]
        for query,base in zip(queries,fallback):
            route,structured=self.route(query)
            routes.append(route)
            if structured is None:
                ranks.append(base)
            elif not structured:
                ranks.append([])
            else:
                seen={d for d,_ in structured}
                ranks.append(structured+[(d,s) for d,s in base if d not in seen])
        return ranks,routes
