from __future__ import annotations

import math
import re
from dataclasses import dataclass
from typing import Iterable, List
from urllib.parse import quote_plus, urlparse


USER_AGENT = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36"
)
REQUEST_TIMEOUT = 12

# Lista curta de domínios geralmente confiáveis para notícias.
KNOWN_RELIABLE_DOMAINS = {
    "g1.globo.com",
    "bbc.com",
    "bbc.co.uk",
    "reuters.com",
    "apnews.com",
    "estadao.com.br",
    "folha.uol.com.br",
    "uol.com.br",
    "cnn.com",
}

# Domínios que aparecem com frequência em golpes/clickbait.
KNOWN_SUSPICIOUS_DOMAINS = {
    "blogspot.com",
    "wordpress.com",
    "rumble.com",
    "odysee.com",
}


@dataclass
class SearchHit:
    title: str
    link: str
    snippet: str


@dataclass
class AnalysisReport:
    input_url: str
    article_title: str
    article_text: str
    corroborating_hits: List[SearchHit]
    conflicting_hits: List[SearchHit]
    unknown_hits: List[SearchHit]
    score: float
    verdict: str
    reasons: List[str]


def fetch_url(url: str) -> str:
    import requests

    response = requests.get(
        url,
        headers={"User-Agent": USER_AGENT, "Accept-Language": "pt-BR,pt;q=0.9,en;q=0.8"},
        timeout=REQUEST_TIMEOUT,
    )
    response.raise_for_status()
    return response.text


def extract_article(html: str) -> tuple[str, str]:
    from bs4 import BeautifulSoup

    soup = BeautifulSoup(html, "html.parser")
    title = (soup.title.text if soup.title else "").strip()

    paragraphs = [p.get_text(" ", strip=True) for p in soup.select("article p, main p, p")]
    paragraphs = [p for p in paragraphs if len(p) > 50]

    if not paragraphs:
        body_text = soup.get_text(" ", strip=True)
    else:
        body_text = "\n".join(paragraphs[:25])

    return title, normalize_whitespace(body_text)


def normalize_whitespace(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def top_keywords(title: str, body: str, max_terms: int = 8) -> List[str]:
    text = f"{title} {body}".lower()
    tokens = re.findall(r"[a-zà-ÿ0-9]{4,}", text)

    stopwords = {
        "para",
        "como",
        "mais",
        "sobre",
        "entre",
        "depois",
        "porque",
        "quando",
        "também",
        "apenas",
        "muito",
        "ainda",
        "seria",
        "foram",
        "dessa",
        "deste",
        "essa",
        "este",
        "isso",
        "pela",
        "pelo",
        "com",
        "sem",
        "numa",
        "num",
        "uma",
        "mais",
        "notícia",
        "noticias",
    }

    freq: dict[str, int] = {}
    for token in tokens:
        if token in stopwords or token.isdigit():
            continue
        freq[token] = freq.get(token, 0) + 1

    ranked = sorted(freq.items(), key=lambda item: item[1], reverse=True)
    return [term for term, _ in ranked[:max_terms]]


def search_related_news(query: str, limit: int = 10) -> List[SearchHit]:
    from bs4 import BeautifulSoup

    # DuckDuckGo HTML endpoint (sem chave/API paga)
    url = f"https://duckduckgo.com/html/?q={quote_plus(query)}"
    html = fetch_url(url)
    soup = BeautifulSoup(html, "html.parser")

    hits: List[SearchHit] = []
    for result in soup.select(".result"):
        a = result.select_one(".result__a")
        snippet = result.select_one(".result__snippet")
        if not a:
            continue
        hits.append(
            SearchHit(
                title=normalize_whitespace(a.get_text(" ", strip=True)),
                link=a.get("href", ""),
                snippet=normalize_whitespace(snippet.get_text(" ", strip=True) if snippet else ""),
            )
        )
        if len(hits) >= limit:
            break

    return hits


def classify_hits(input_url: str, input_title: str, input_text: str, hits: Iterable[SearchHit]) -> tuple[List[SearchHit], List[SearchHit], List[SearchHit]]:
    source_domain = domain_of(input_url)
    reference_terms = set(top_keywords(input_title, input_text, max_terms=12))

    corroborating: List[SearchHit] = []
    conflicting: List[SearchHit] = []
    unknown: List[SearchHit] = []

    for hit in hits:
        hit_domain = domain_of(hit.link)

        if hit_domain == source_domain:
            # Ignora resultados do mesmo domínio para evitar auto-confirmação.
            continue

        hit_text = f"{hit.title} {hit.snippet}".lower()
        overlap = keyword_overlap_ratio(reference_terms, set(re.findall(r"[a-zà-ÿ0-9]{4,}", hit_text)))

        contradiction_markers = [
            "boato",
            "falso",
            "fake",
            "desmente",
            "enganoso",
            "sem evidência",
            "não há provas",
        ]
        has_contradiction = any(marker in hit_text for marker in contradiction_markers)

        if has_contradiction and overlap >= 0.2:
            conflicting.append(hit)
        elif overlap >= 0.3:
            corroborating.append(hit)
        else:
            unknown.append(hit)

    return corroborating, conflicting, unknown


def keyword_overlap_ratio(a: set[str], b: set[str]) -> float:
    if not a:
        return 0.0
    return len(a.intersection(b)) / len(a)


def domain_of(url: str) -> str:
    try:
        netloc = urlparse(url).netloc.lower()
        return netloc.replace("www.", "")
    except Exception:
        return ""


def score_report(input_url: str, corroborating: List[SearchHit], conflicting: List[SearchHit]) -> tuple[float, str, List[str]]:
    domain = domain_of(input_url)
    reasons: List[str] = []

    score = 0.5

    if domain in KNOWN_RELIABLE_DOMAINS:
        score += 0.2
        reasons.append("O domínio de origem está em uma lista curta de fontes geralmente confiáveis.")
    if any(domain.endswith(susp) for susp in KNOWN_SUSPICIOUS_DOMAINS):
        score -= 0.2
        reasons.append("O domínio de origem está associado a plataformas com risco maior de conteúdo não verificado.")

    corroboration_boost = min(0.35, 0.08 * len(corroborating))
    contradiction_penalty = min(0.45, 0.12 * len(conflicting))

    score += corroboration_boost
    score -= contradiction_penalty

    if corroborating:
        reasons.append(f"Encontradas {len(corroborating)} fontes externas com termos semelhantes.")
    if conflicting:
        reasons.append(f"Encontradas {len(conflicting)} fontes com linguagem de desmentido/falsidade.")

    score = max(0.0, min(1.0, score))

    if score >= 0.7:
        verdict = "Provavelmente verdadeira"
    elif score <= 0.35:
        verdict = "Provavelmente falsa"
    else:
        verdict = "Inconclusiva / requer checagem humana"

    confidence = abs(score - 0.5) * 2
    reasons.append(f"Confiança heurística: {math.floor(confidence * 100)}% (não substitui fact-checking profissional).")

    return score, verdict, reasons


def analyze_news_url(url: str) -> AnalysisReport:
    article_html = fetch_url(url)
    title, body = extract_article(article_html)

    if len(body) < 180:
        raise ValueError("Não foi possível extrair conteúdo suficiente da notícia. Tente outro link.")

    keywords = top_keywords(title, body)
    query = f'"{title[:120]}" ' + " ".join(keywords[:5])

    hits = search_related_news(query=query, limit=12)
    corroborating, conflicting, unknown = classify_hits(url, title, body, hits)
    score, verdict, reasons = score_report(url, corroborating, conflicting)

    return AnalysisReport(
        input_url=url,
        article_title=title or "(sem título detectado)",
        article_text=body,
        corroborating_hits=corroborating,
        conflicting_hits=conflicting,
        unknown_hits=unknown,
        score=score,
        verdict=verdict,
        reasons=reasons,
    )
