from django.test import TestCase

from .matching import build_search_name, find_name_matches, normalize_name, score_name
from .models import NameRecord


class MatchingEngineTests(TestCase):
    def test_build_search_name_joins_available_parts(self):
        self.assertEqual(
            build_search_name(nombre=" Juan ", paterno=" Perez", materno="Lopez "),
            "Juan Perez Lopez",
        )

    def test_build_search_name_uses_partial_data(self):
        self.assertEqual(build_search_name(nombre="Maria Fernanda"), "Maria Fernanda")

    def test_build_search_name_avoids_duplicate_surname_from_full_name(self):
        self.assertEqual(
            build_search_name(nombre="Juan Perez", paterno="Perez"),
            "Juan Perez",
        )

    def test_build_search_name_avoids_duplicate_parts_across_fields(self):
        self.assertEqual(
            build_search_name(
                nombre="Maria Fernanda",
                paterno="Lopez",
                materno="Lopez",
            ),
            "Maria Fernanda Lopez",
        )

    def test_normalization_removes_accents_and_symbols(self):
        self.assertEqual(normalize_name("  Núñez, José!  "), "nunez jose")

    def test_typo_similarity_detected(self):
        metrics = score_name("Jhon Peres", "Juan Perez")
        self.assertGreaterEqual(metrics["overall"], 65)

    def test_exact_match_reaches_top_score_after_normalization(self):
        metrics = score_name("José Núñez", "Jose Nunez")
        self.assertEqual(metrics["overall"], 100.0)
        self.assertTrue(metrics["exact_match"])

    def test_same_tokens_in_different_order_get_strong_score(self):
        metrics = score_name("Perez Juan", "Juan Perez")
        self.assertGreaterEqual(metrics["overall"], 97.0)

    def test_missing_letters_detected(self):
        metrics = score_name("Alejndro Gmez", "Alejandro Gomez")
        self.assertGreaterEqual(metrics["partial"], 80)

    def test_short_query_does_not_overinflate_partial_match(self):
        metrics = score_name("Juan", "Juan Carlos Fernandez")
        self.assertLess(metrics["overall"], 85)

    def test_reordered_tokens_detected(self):
        metrics = score_name("Perez Juan", "Juan Perez")
        self.assertGreaterEqual(metrics["token_sort"], 95)

    def test_phonetic_similarity_detected(self):
        metrics = score_name("Cristian Hernandez", "Christian Hernandes")
        self.assertGreaterEqual(metrics["phonetic"], 75)

    def test_find_name_matches_keeps_candidate_context(self):
        results = find_name_matches(
            query="Jhon Peres",
            candidates=[
                {
                    "id": 99,
                    "nombre": "Juan",
                    "paterno": "Perez",
                    "materno": "Lopez",
                    "search_full_name": "Juan Perez",
                    "origen": "SolicitudPartes",
                    "folio_ref": "FICT-999",
                    "rfc": "JUAP000101AAA",
                }
            ],
            min_score=50,
            limit=5,
        )
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["origen"], "SolicitudPartes")
        self.assertEqual(results[0]["folio_ref"], "FICT-999")
        self.assertEqual(results[0]["rfc"], "JUAP000101AAA")

    def test_find_name_matches_can_score_without_materno_when_needed(self):
        results = find_name_matches(
            query="Juan Perez",
            candidates=[
                {
                    "search_full_name": "Juan Perez Lopez",
                    "nombre": "Juan",
                    "paterno": "Perez",
                    "materno": "Lopez",
                    "origen": "SolicitudPartes",
                    "folio_ref": "FICT-001",
                    "rfc": "",
                }
            ],
            min_score=50,
            limit=5,
        )
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["matched_variant"], "Juan Perez")
        self.assertGreaterEqual(results[0]["score"], 97.0)


class SearchViewTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        NameRecord.objects.create(
            nombre="Juan",
            paterno="Perez",
            origen="SolicitudPartes",
            folio_ref="FICT-001",
        )
        NameRecord.objects.create(nombre="Maria Fernanda", paterno="Lopez")
        NameRecord.objects.create(nombre="Cristian", paterno="Hernandez")

    def test_model_builds_search_fields_on_save(self):
        record = NameRecord.objects.create(
            nombre=" Ana Lucia ",
            paterno=" Torres ",
            materno="",
            rfc="abc123456",
        )
        self.assertEqual(record.search_full_name, "Ana Lucia Torres")
        self.assertEqual(record.normalized_name, "ana lucia torres")
        self.assertEqual(record.rfc, "ABC123456")

    def test_search_page_loads(self):
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)

    def test_search_returns_expected_result(self):
        response = self.client.get("/", {"query": "Jhon Peres", "min_score": 50})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Juan Perez")

    def test_search_shows_origin_context(self):
        response = self.client.get("/", {"query": "Jhon Peres", "min_score": 50})
        self.assertContains(response, "Origen:")
        self.assertContains(response, "SolicitudPartes")
