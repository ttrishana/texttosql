"""Optional pgvector-based retrieval for the Knowledge Layer.

Only needed when RETRIEVAL_MODE=true (large schemas / many few-shots). It embeds
table descriptions and few-shot questions with Gemini embeddings and stores them
in a `semantic_index` table so the agent can retrieve only the relevant subset.

Default (lexical) selection in ``catalog.py`` needs none of this. Build once with
``python scripts/build_index.py`` after the DB is seeded.
"""

from __future__ import annotations

from typing import Any

from sqlalchemy import text

from ..config import get_settings
from ..db.engine import get_admin_engine, get_readonly_engine

EMBED_MODEL = "models/text-embedding-004"
EMBED_DIM = 768


def _embedder():
    from langchain_google_genai import GoogleGenerativeAIEmbeddings

    settings = get_settings()
    return GoogleGenerativeAIEmbeddings(model=EMBED_MODEL, google_api_key=settings.google_api_key)


def build_index() -> int:
    """(Re)build the semantic_index table from the catalog. Returns row count."""
    from .catalog import SemanticCatalog

    catalog = SemanticCatalog(get_readonly_engine())
    embedder = _embedder()

    docs: list[dict[str, Any]] = []
    for t in catalog.table_summary():
        docs.append({"kind": "table", "ref": t["table"],
                     "content": f"{t['table']}: {t['description']} columns: {', '.join(t['columns'])}"})
    for ex in catalog.few_shots:
        docs.append({"kind": "few_shot", "ref": ex["question"],
                     "content": ex["question"] + " " + " ".join(ex.get("tags", []))})

    vectors = embedder.embed_documents([d["content"] for d in docs])

    engine = get_admin_engine()
    with engine.begin() as conn:
        conn.execute(text("SET default_transaction_read_only = off"))
        conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        conn.execute(text("DROP TABLE IF EXISTS semantic_index"))
        conn.execute(text(
            f"CREATE TABLE semantic_index (id SERIAL PRIMARY KEY, kind TEXT, ref TEXT, "
            f"content TEXT, embedding vector({EMBED_DIM}))"
        ))
        conn.execute(text("GRANT SELECT ON semantic_index TO texttosql_readonly"))
        for d, vec in zip(docs, vectors):
            conn.execute(
                text("INSERT INTO semantic_index (kind, ref, content, embedding) "
                     "VALUES (:kind, :ref, :content, :embedding)"),
                {**d, "embedding": str(vec)},
            )
    return len(docs)


def retrieve(query: str, kind: str, k: int = 6) -> list[str]:
    """Return the top-k `ref` values of the given kind nearest to the query."""
    embedder = _embedder()
    vec = str(embedder.embed_query(query))
    engine = get_readonly_engine()
    with engine.connect() as conn:
        rows = conn.execute(
            text("SELECT ref FROM semantic_index WHERE kind = :kind "
                 "ORDER BY embedding <=> :vec LIMIT :k"),
            {"kind": kind, "vec": vec, "k": k},
        ).fetchall()
    return [r[0] for r in rows]
