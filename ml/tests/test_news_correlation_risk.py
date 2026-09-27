import unittest
from unittest.mock import patch

from ml.correlation.correlate import correlate
from ml.news.entity import link_entities

PROFILES = {
    "XNSE:RELIANCE": {"strong": ["Reliance Industries", "RIL"], "weak": ["Reliance"], "exclude": ["Reliance Power"]},
    "XNSE:TCS": {"strong": ["Tata Consultancy Services", "TCS"], "weak": [], "exclude": []},
    "XNSE:HDFCBANK": {"strong": ["HDFC Bank"], "weak": ["HDFC"], "exclude": ["HDFC Life"]},
}


def links(text, explicit=None):
    return link_entities(text, explicit_ids=explicit, candidates=list(PROFILES), profiles=PROFILES)
from ml.news.events import classify_event
from ml.news.preprocessing import clean_text, deduplicate
from ml.risk.scoring import compute_risk

CONTRIB = [{"feature": "log_volume", "label": "Trading volume", "direction": "above", "robust_z": 5.0}]


def news(news_id, published, symbol="XNSE:RELIANCE", confidence=0.95, score=-0.9):
    return {"news_id": news_id, "headline": f"Reliance Industries headline {news_id}", "published_at": published, "source": "Test",
            "links": [{"instrument_id": symbol, "entity_match_confidence": confidence, "mapping_method": "strong_alias"}],
            "sentiment": {"label": "negative", "sentiment_score": score, "confidence": 0.9}}


class EntityAndEventTests(unittest.TestCase):
    def test_strong_alias_links_and_different_company_is_excluded(self):
        self.assertEqual(links("Reliance Industries shares rise")[0]["instrument_id"], "XNSE:RELIANCE")
        self.assertEqual([l["instrument_id"] for l in links("Reliance Power wins contract")], [])
        self.assertEqual([l["instrument_id"] for l in links("HDFC Life posts growth")], [])

    def test_ticker_alias_is_case_sensitive(self):
        self.assertIn("XNSE:TCS", [l["instrument_id"] for l in links("TCS wins a deal")])
        self.assertNotIn("XNSE:TCS", [l["instrument_id"] for l in links("Tcs is not a ticker mention here")])

    def test_explicit_metadata_has_full_confidence(self):
        self.assertEqual(links("Unrelated text", explicit=["TEST:DEMO"])[0]["entity_match_confidence"], 1.0)

    def test_event_classification_rules(self):
        self.assertEqual(classify_event("SEBI imposes penalty on company")["category"], "Regulatory")
        self.assertEqual(classify_event("Company Q2 profit rises 10%")["category"], "Earnings")
        self.assertEqual(classify_event("Company opens new office")["category"], "Other")

    def test_preprocessing(self):
        self.assertEqual(clean_text("<b>Hello</b>&amp;  world "), "Hello & world")
        kept, removed = deduplicate([{"headline": "A b", "url": "u1"}, {"headline": "a B!", "url": "u2"}, {"headline": "", "url": "u3"}])
        self.assertEqual((len(kept), removed), (1, 2))


@patch("ml.correlation.correlate.semantic.similarities", return_value=None)
class CorrelationTests(unittest.TestCase):
    def test_window_filtering_and_scores(self, _sim):
        items = [news("in_session", "2026-06-15T05:00:00Z"), news("before", "2026-06-14T15:45:00Z"), news("outside", "2026-06-10T05:00:00Z"),
                 news("low_conf", "2026-06-15T05:00:00Z", confidence=0.5), news("other_asset", "2026-06-15T05:00:00Z", symbol="XNSE:TCS")]
        result = correlate("2026-06-15", 0.8, CONTRIB, items, "XNSE:RELIANCE", "Reliance Industries", "XBOM")
        ids = [m["news_id"] for m in result["matches"]]
        self.assertEqual(ids, ["in_session", "before"])
        best = result["matches"][0]
        self.assertEqual(best["relation"], "published_during_session")
        self.assertAlmostEqual(best["correlation_score"], 0.30 * 1 + 0.25 * 0.95 + 0.20 * 0.9 + 0.25 * 0.8, places=4)
        self.assertEqual(result["matches"][1]["relation"], "published_before_session")
        self.assertIsNone(best["semantic_relevance"])
        self.assertIn("do not establish causation", result["interpretation"])

    def test_no_news_in_window(self, _sim):
        result = correlate("2026-06-15", 0.8, CONTRIB, [news("old", "2026-01-01T05:00:00Z")], "XNSE:RELIANCE", "Reliance Industries", "XBOM")
        self.assertEqual(result["status"], "no_aligned_news")
        self.assertEqual(result["best_score"], 0.0)


class RiskTests(unittest.TestCase):
    CORR = {"matches": [{"components": {"sentiment_strength": 0.9, "temporal_proximity": 1.0}, "correlation_score": 0.9, "sentiment_available": True}]}

    def test_contributions_sum_to_score(self):
        risk = compute_risk(0.9, 0.8, 0.9, self.CORR, "ok")
        self.assertAlmostEqual(sum(c["contribution"] for c in risk["components"]), risk["score"], delta=0.1)
        self.assertEqual(risk["basis"], "market_and_news")

    def test_news_context_cannot_create_risk_without_anomaly(self):
        risk = compute_risk(0.0, 0.0, 1.0, self.CORR, "ok")
        self.assertEqual(risk["score"], 0.0)
        self.assertEqual(risk["level"], "LOW")

    def test_news_unavailable_is_explicit(self):
        risk = compute_risk(0.9, 0.8, 0.9, None, "unavailable")
        self.assertEqual(risk["basis"], "market_only_news_unavailable")
        unavailable = {c["name"] for c in risk["components"] if not c["available"]}
        self.assertEqual(unavailable, {"sentiment", "correlation", "temporal"})


if __name__ == "__main__":
    unittest.main()
