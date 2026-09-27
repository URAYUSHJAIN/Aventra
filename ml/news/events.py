"""Rule-based event categorisation (Final Plan §14: rules/zero-shot first; no custom
classifier until labelled data exists). Rules are checked in priority order and the
matched keywords are returned so the category is explainable."""
from __future__ import annotations

import re

CATEGORY_RULES: list[tuple[str, list[str]]] = [
    ("Fraud / Investigation", ["fraud", "probe", "investigation", "raid", "whistleblower", "irregularit", "forensic audit", "money laundering", "enforcement directorate"]),
    ("Legal", ["court", "lawsuit", "tribunal", "nclt", "litigation", "verdict", "arbitration", "sued", "petition"]),
    ("Regulatory", ["sebi", "rbi", "regulator", "regulatory", "penalty", "fined", "licence", "license", "compliance", "ban on"]),
    ("Merger / Acquisition", ["acquire", "acquisition", "merger", "merge", "takeover", "buyout", "stake sale", "stake in", "joint venture"]),
    ("Earnings", ["results", "quarterly", "q1", "q2", "q3", "q4", "profit", "revenue", "earnings", "ebitda", "net income", "guidance", "margin"]),
    ("Management Change", ["ceo", "cfo", "managing director", "chairman", "resign", "appoint", "steps down", "succession"]),
    ("Corporate Action", ["dividend", "bonus", "stock split", "buyback", "rights issue", "record date", "demerger", "listing"]),
    ("Macroeconomic", ["inflation", "gdp", "repo rate", "interest rate", "rupee", "crude", "fiscal", "union budget", "monetary policy"]),
    ("Market-wide", ["sensex", "nifty", "stock market", "fii", "dii", "market rally", "market crash", "indices"]),
]


def classify_event(text: str) -> dict:
    lowered = text.lower()
    for category, keywords in CATEGORY_RULES:
        matched = [keyword for keyword in keywords if re.search(rf"(?<![a-z]){re.escape(keyword)}", lowered)]
        if matched:
            return {"category": category, "matched_keywords": matched, "method": "keyword_rules"}
    return {"category": "Other", "matched_keywords": [], "method": "keyword_rules"}
