from __future__ import annotations

from collections import Counter
import re
from typing import Iterable, Mapping

import jellyfish
from rapidfuzz import distance, fuzz
from unidecode import unidecode

SPACE_RE = re.compile(r"\s+")
NON_ALNUM_RE = re.compile(r"[^a-z0-9\s]")


def clean_name_piece(value: str) -> str:
    cleaned = SPACE_RE.sub(" ", (value or "").strip())
    return cleaned.strip()


def _dedupe_name_parts(parts: list[str]) -> list[str]:
    seen: set[str] = set()
    deduped: list[str] = []
    for part in parts:
        normalized_part = normalize_name(part)
        if not normalized_part or normalized_part in seen:
            continue
        seen.add(normalized_part)
        deduped.append(part)
    return deduped


def build_search_name(
    *,
    nombre: str = "",
    paterno: str = "",
    materno: str = "",
) -> str:
    nombre = clean_name_piece(nombre)
    paterno = clean_name_piece(paterno)
    materno = clean_name_piece(materno)

    if nombre:
        base_tokens = set(tokens(nombre))
        if paterno and set(tokens(paterno)).issubset(base_tokens):
            paterno = ""
        if materno and set(tokens(materno)).issubset(base_tokens):
            materno = ""

    parts = _dedupe_name_parts([part for part in [nombre, paterno, materno] if part])
    if parts:
        return " ".join(parts)

    return ""


def normalize_name(name: str) -> str:
    normalized = unidecode((name or "").strip().lower())
    normalized = NON_ALNUM_RE.sub(" ", normalized)
    normalized = SPACE_RE.sub(" ", normalized)
    return normalized.strip()


def tokens(name: str) -> list[str]:
    normalized = normalize_name(name)
    if not normalized:
        return []
    return normalized.split(" ")


def phonetic_token(token: str) -> str:
    if not token:
        return ""
    code = jellyfish.metaphone(token)
    return code or token


def _token_overlap_score(tokens_a: list[str], tokens_b: list[str]) -> float:
    if not tokens_a or not tokens_b:
        return 0.0

    counter_a = Counter(tokens_a)
    counter_b = Counter(tokens_b)
    common_tokens = sum((counter_a & counter_b).values())
    denom = max(sum(counter_a.values()), sum(counter_b.values()))

    if denom == 0:
        return 0.0

    return (common_tokens / denom) * 100


def _phonetic_scores(query: str, candidate: str) -> dict[str, float]:
    query_codes = [phonetic_token(token) for token in tokens(query)]
    candidate_codes = [phonetic_token(token) for token in tokens(candidate)]

    joined_query = " ".join(sorted(query_codes))
    joined_candidate = " ".join(sorted(candidate_codes))

    token_sort = fuzz.token_sort_ratio(joined_query, joined_candidate)
    overlap = _token_overlap_score(query_codes, candidate_codes)
    combined = (token_sort * 0.7) + (overlap * 0.3)

    return {
        "phonetic_token_sort": round(token_sort, 2),
        "phonetic_overlap": round(overlap, 2),
        "phonetic": round(combined, 2),
    }


def _candidate_variants(candidate_payload: Mapping[str, object]) -> list[str]:
    variants: list[str] = []

    search_full_name = clean_name_piece(
        str(candidate_payload.get("search_full_name", "") or "")
    )
    if search_full_name:
        variants.append(search_full_name)

    nombre = clean_name_piece(str(candidate_payload.get("nombre", "") or ""))
    paterno = clean_name_piece(str(candidate_payload.get("paterno", "") or ""))
    materno = clean_name_piece(str(candidate_payload.get("materno", "") or ""))

    if nombre or paterno:
        without_materno = build_search_name(
            nombre=nombre,
            paterno=paterno,
            materno="",
        )
        if without_materno:
            variants.append(without_materno)

    if nombre and not paterno and not materno:
        variants.append(nombre)

    return _dedupe_name_parts(variants)


def score_name(query: str, candidate: str) -> dict[str, float]:
    normalized_query = normalize_name(query)
    normalized_candidate = normalize_name(candidate)

    if not normalized_query or not normalized_candidate:
        return {
            "overall": 0.0,
            "typo_similarity": 0.0,
            "token_sort": 0.0,
            "token_set": 0.0,
            "partial": 0.0,
            "levenshtein": 0.0,
            "jaro_winkler": 0.0,
            "phonetic": 0.0,
            "phonetic_token_sort": 0.0,
            "phonetic_overlap": 0.0,
        }

    exact_match = normalized_query == normalized_candidate
    same_tokens = set(tokens(normalized_query)) == set(tokens(normalized_candidate))
    query_length = len(normalized_query)
    candidate_length = len(normalized_candidate)

    typo_similarity = fuzz.ratio(normalized_query, normalized_candidate)
    token_sort = fuzz.token_sort_ratio(normalized_query, normalized_candidate)
    token_set = fuzz.token_set_ratio(normalized_query, normalized_candidate)
    partial = fuzz.partial_ratio(normalized_query, normalized_candidate)
    levenshtein = (
        distance.Levenshtein.normalized_similarity(normalized_query, normalized_candidate)
        * 100
    )
    jaro_winkler = (
        jellyfish.jaro_winkler_similarity(normalized_query, normalized_candidate) * 100
    )

    phonetic_scores = _phonetic_scores(normalized_query, normalized_candidate)

    overall = (
        (token_sort * 0.23)
        + (token_set * 0.15)
        + (typo_similarity * 0.15)
        + (partial * 0.15)
        + (levenshtein * 0.12)
        + (jaro_winkler * 0.10)
        + (phonetic_scores["phonetic"] * 0.10)
    )

    if query_length and candidate_length:
        length_ratio = min(query_length, candidate_length) / max(
            query_length, candidate_length
        )
        if length_ratio < 0.45 and partial > 90:
            overall *= max(0.72, length_ratio + 0.25)

    if exact_match:
        overall = 100.0
    elif same_tokens:
        overall = max(overall, 97.0)

    return {
        "overall": round(min(100.0, max(0.0, overall)), 2),
        "exact_match": exact_match,
        "typo_similarity": round(typo_similarity, 2),
        "token_sort": round(token_sort, 2),
        "token_set": round(token_set, 2),
        "partial": round(partial, 2),
        "levenshtein": round(levenshtein, 2),
        "jaro_winkler": round(jaro_winkler, 2),
        **phonetic_scores,
    }


def explain_score(metrics: dict[str, float]) -> str:
    if metrics.get("exact_match"):
        return "Coincidencia exacta tras normalización."
    if metrics["token_sort"] >= 92 and metrics["typo_similarity"] < 85:
        return "Coincide aunque los nombres estén en orden distinto."
    if metrics["phonetic"] >= 85:
        return "Coincidencia fuerte por pronunciación."
    if metrics["partial"] >= 85 and metrics["typo_similarity"] < 80:
        return "Coincide con letras faltantes o abreviaciones."
    if metrics["typo_similarity"] >= 85:
        return "Coincidencia por errores ortográficos menores."
    return "Coincidencia difusa combinada."


def find_name_matches(
    query: str,
    candidates: Iterable[str | Mapping[str, object]],
    min_score: int = 45,
    limit: int = 20,
) -> list[dict[str, object]]:
    results = []

    for candidate in candidates:
        if isinstance(candidate, str):
            candidate_name = candidate
            candidate_payload: dict[str, object] = {"search_full_name": candidate}
            candidate_variants = [candidate]
        else:
            candidate_payload = dict(candidate)
            candidate_name = str(candidate_payload.get("search_full_name", "") or "")
            candidate_variants = _candidate_variants(candidate_payload)

        metrics = None
        matched_variant = candidate_name
        for variant in candidate_variants or [candidate_name]:
            variant_metrics = score_name(query, variant)
            if metrics is None or variant_metrics["overall"] > metrics["overall"]:
                metrics = variant_metrics
                matched_variant = variant

        if metrics is None:
            continue

        if metrics["overall"] < min_score:
            continue

        results.append(
            {
                "id": candidate_payload.get("id"),
                "name": candidate_name,
                "score": metrics["overall"],
                "details": metrics,
                "explanation": explain_score(metrics),
                "matched_variant": matched_variant,
                "origen": candidate_payload.get("origen", ""),
                "folio_ref": candidate_payload.get("folio_ref", ""),
                "rfc": candidate_payload.get("rfc", ""),
            }
        )

    results.sort(key=lambda item: item["score"], reverse=True)
    return results[:limit]
