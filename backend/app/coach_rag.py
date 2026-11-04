"""RAG documental acotado, sin enviar consultas ni perfiles a webs externas.

Recupera páginas oficiales registradas, las divide y rankea con BM25. Caché pública
de 24 h, tamaños/tiempos acotados y sin seguir redirecciones arbitrarias (SSRF).
Los documentos son evidencia no confiable, nunca instrucciones para el modelo.
"""

import hashlib
import math
import re
import time
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from html.parser import HTMLParser
from threading import Lock

import httpx

from .config import settings
from .knowledge import SOURCES, retrieve, tokens

DOCUMENTS = {
    "who-diet": dict(
        url=SOURCES["oms-dieta"]["url"],
        title="OMS — Alimentación saludable",
        topics="nutrition clinical cooking",
        terms="diet nutrition fat sugar salt protein fruta grasa azucar alimentacion pollo frito",
    ),
    "cdc-meals": dict(
        url=SOURCES["cdc-plato"]["url"],
        title="CDC — Diabetes Meal Planning",
        topics="clinical nutrition",
        terms="diabetes glucose carbohydrate plate glucosa carbohidratos plato arroz",
    ),
    "ada-fruit": dict(
        url=SOURCES["ada-fruta"]["url"],
        title="ADA — Fruit",
        topics="nutrition clinical",
        terms="fruit mango fruta diabetes jugo",
    ),
    "who-sodium": dict(
        url=SOURCES["oms-sodio"]["url"],
        title="OMS — Sodio",
        topics="clinical nutrition",
        terms="salt sodium hypertension sal sodio hipertension",
    ),
    "nih-kidney": dict(
        url="https://www.niddk.nih.gov/health-information/kidney-disease/chronic-kidney-disease-ckd/healthy-eating-adults-chronic-kidney-disease",
        title="NIDDK — Alimentación y enfermedad renal",
        topics="clinical",
        terms="kidney renal potassium phosphorus protein dialisis potasio fosforo",
    ),
    "who-food-safety": dict(
        url="https://www.who.int/news-room/fact-sheets/detail/food-safety",
        title="OMS — Inocuidad alimentaria",
        topics="cooking clinical",
        terms="food safety infection raw bacteria cooking inocuidad crudo coccion bacterias",
    ),
}
_cache = {}
_lock = Lock()


class ArticleParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.hidden = 0
        self.parts = []

    def handle_starttag(self, tag, attrs):
        if tag in {"script", "style", "nav", "header", "footer", "noscript"}:
            self.hidden += 1
        if tag in {"p", "li", "h1", "h2", "h3", "section"} and not self.hidden:
            self.parts.append("\n")

    def handle_endtag(self, tag):
        if tag in {"script", "style", "nav", "header", "footer", "noscript"}:
            self.hidden = max(0, self.hidden - 1)
        if tag in {"p", "li", "h1", "h2", "h3"} and not self.hidden:
            self.parts.append("\n")

    def handle_data(self, data):
        if not self.hidden:
            self.parts.append(data)


def fetch_document(key):
    if key not in DOCUMENTS:
        raise ValueError("Documento no registrado")
    with _lock:
        cached = _cache.get(key)
    if cached and time.monotonic() - cached[0] < 86400:
        return cached[1]
    doc = DOCUMENTS[key]
    try:
        with httpx.Client(timeout=6, follow_redirects=False) as client:
            with client.stream(
                "GET", doc["url"], headers={"User-Agent": "Mikuy-evidence/1.0"}
            ) as response:
                response.raise_for_status()
                if "text/html" not in response.headers.get("content-type", ""):
                    raise ValueError("Formato no admitido")
                body = bytearray()
                for data in response.iter_bytes():
                    body.extend(data)
                    if len(body) > 2_000_000:
                        raise ValueError("Documento demasiado grande")
        parser = ArticleParser()
        parser.feed(body.decode("utf-8", errors="replace"))
        paragraphs = [re.sub(r"\s+", " ", p).strip() for p in "".join(parser.parts).split("\n")]
        chunks = [
            p[i : i + 1400] for p in paragraphs if len(p) > 80 for i in range(0, len(p), 1200)
        ]
        if not chunks:
            raise ValueError("Documento sin texto recuperable")
        result = dict(
            chunks=chunks[:180],
            fetched_at=datetime.now(timezone.utc).isoformat(),
            digest=hashlib.sha256(body).hexdigest(),
            stale=False,
        )
        with _lock:
            _cache[key] = (time.monotonic(), result)
        return result
    except (httpx.HTTPError, ValueError):
        if cached:
            return {**cached[1], "stale": True}
        return None


def rank_chunks(query, chunks, limit=4):
    query_terms = set(tokens(query))
    docs = [Counter(tokens(c["text"])) for c in chunks]
    df = Counter(t for doc in docs for t in doc)
    avg = sum(sum(d.values()) for d in docs) / max(1, len(docs))
    ranked = []
    for chunk, doc in zip(chunks, docs):
        score = 0.0
        for word in query_terms:
            tf = doc.get(word, 0)
            if tf:
                idf = math.log(1 + (len(docs) - df[word] + 0.5) / (df[word] + 0.5))
                score += (
                    idf * tf * 2.2 / (tf + 1.2 * (0.25 + 0.75 * sum(doc.values()) / max(avg, 1)))
                )
        if score:
            ranked.append((score, chunk))
    return [c for _, c in sorted(ranked, key=lambda pair: pair[0], reverse=True)[:limit]]


def evidence_for(intent, conditions=()):
    query = intent.rewritten_question + " " + " ".join(intent.search_terms)
    translations = {
        "potasio": "potassium",
        "renal": "kidney",
        "fosforo": "phosphorus",
        "frito": "fried fat",
        "frituras": "frying fat",
        "pollo": "chicken",
        "grasa": "fat",
        "sodio": "sodium",
        "sal": "salt",
        "fruta": "fruit",
        "azucar": "sugar",
        "glucosa": "glucose",
    }
    query += " " + " ".join(translations.get(word, "") for word in tokens(query))
    # No contaminación por enfermedades del perfil en preguntas generales.
    if intent.topic == "general":
        return [], dict(live=0, unavailable=[], scope="general_knowledge")
    seed = retrieve(query, conditions, k=4)
    cards = [
        {
            **c,
            "url": SOURCES[c["source"]]["url"],
            "source_title": SOURCES[c["source"]]["title"],
            "kind": "curated_summary",
        }
        for c in seed
    ]
    if not settings().coach_live_rag or intent.topic == "budget":
        return cards, dict(live=0, unavailable=[], scope="curated")
    qwords = set(tokens(query))
    choices = sorted(
        DOCUMENTS, key=lambda k: len(qwords & set(tokens(DOCUMENTS[k]["terms"]))), reverse=True
    )
    choices = [k for k in choices if qwords & set(tokens(DOCUMENTS[k]["terms"]))][:2]
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(fetch_document, choices))
    chunks, unavailable = [], []
    for key, result in zip(choices, results):
        if not result:
            unavailable.append(key)
            continue
        doc = DOCUMENTS[key]
        for i, text in enumerate(result["chunks"]):
            chunks.append(
                dict(
                    id=f"{key}:{result['digest'][:8]}:{i}",
                    title=doc["title"],
                    source_title=doc["title"],
                    url=doc["url"],
                    text=text,
                    kind="document_excerpt",
                    fetched_at=result["fetched_at"],
                    stale=result["stale"],
                )
            )
    live = rank_chunks(query, chunks)
    return (live + cards)[:8], dict(
        live=len(live), unavailable=unavailable, scope="documents_and_curated"
    )


def source_link(card):
    if "url" in card:
        return dict(
            id=card["id"],
            title=card["title"],
            source=card.get("source_title", card["title"]),
            url=card["url"],
        )
    from .knowledge import cite

    return cite(card)
