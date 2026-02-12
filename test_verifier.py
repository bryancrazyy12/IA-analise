import unittest

from verifier import domain_of, keyword_overlap_ratio, score_report


class VerifierTests(unittest.TestCase):
    def test_domain_of_removes_www(self):
        self.assertEqual(domain_of("https://www.g1.globo.com/politica"), "g1.globo.com")

    def test_keyword_overlap_ratio(self):
        a = {"vacina", "covid", "brasil"}
        b = {"covid", "brasil", "saude"}
        self.assertAlmostEqual(keyword_overlap_ratio(a, b), 2 / 3)

    def test_score_report_conflicting_lowers_score(self):
        score_good, verdict_good, _ = score_report(
            "https://g1.globo.com/teste",
            corroborating=[object(), object(), object()],
            conflicting=[],
        )
        score_bad, verdict_bad, _ = score_report(
            "https://blogspot.com/post",
            corroborating=[],
            conflicting=[object(), object(), object()],
        )

        self.assertGreater(score_good, score_bad)
        self.assertIn(verdict_good, {"Provavelmente verdadeira", "Inconclusiva / requer checagem humana"})
        self.assertIn(verdict_bad, {"Provavelmente falsa", "Inconclusiva / requer checagem humana"})


if __name__ == "__main__":
    unittest.main()
