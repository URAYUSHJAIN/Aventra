import unittest
from unittest.mock import patch

from backend.app import create_app
from backend.services.news_analysis_service import FinBertUnavailable


class NewsRouteTests(unittest.TestCase):
    def setUp(self):
        self.client = create_app({"TESTING": True}).test_client()

    def test_missing_text_is_rejected(self):
        response = self.client.post("/api/news/analyze", json={})
        self.assertEqual(response.status_code, 400)

    def test_invalid_json_is_rejected(self):
        response = self.client.post("/api/news/analyze", data="not-json", content_type="text/plain")
        self.assertEqual(response.status_code, 400)

    @patch("backend.routes.news_routes.get_news_analysis_service")
    def test_valid_text_returns_service_result(self, get_service):
        get_service.return_value.analyze.return_value = {"label": "positive", "positive_probability": 0.8, "neutral_probability": 0.15, "negative_probability": 0.05, "sentiment_score": 0.75}
        response = self.client.post("/api/news/analyze", json={"text": "Earnings improved."})
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json["success"])

    @patch("backend.routes.news_routes.get_news_analysis_service")
    def test_model_unavailable_returns_503(self, get_service):
        get_service.return_value.analyze.side_effect = FinBertUnavailable()
        response = self.client.post("/api/news/analyze", json={"text": "Earnings improved."})
        self.assertEqual(response.status_code, 503)


if __name__ == "__main__":
    unittest.main()
