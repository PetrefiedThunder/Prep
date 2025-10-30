"""Graph service API stubs."""
from __future__ import annotations

from typing import Any

from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI(title="Graph Service")


def _graph_state() -> dict[str, Any]:
    if not hasattr(app.state, "documents"):
        app.state.documents = {}
    return app.state.documents


class UpsertDoc(BaseModel):
    doc_id: str
    jurisdiction: str
    title: str
    version: str
    published_at: str
    sections: list[dict[str, Any]]


@app.post("/graph/docs")
def upsert_document(doc: UpsertDoc) -> dict[str, str]:
    docs = _graph_state()
    docs[doc.doc_id] = doc.model_dump()
    return {"doc_id": doc.doc_id}


@app.get("/graph/obligations")
def get_obligations(jurisdiction: str, subject: str | None = None, type: str | None = None) -> list[dict[str, Any]]:
    obligations = getattr(app.state, "obligations", [])
    filtered = [
        obl
        for obl in obligations
        if obl.get("jurisdiction") == jurisdiction
        and (subject is None or obl.get("subject") == subject)
        and (type is None or obl.get("type") == type)
    ]
    return filtered


@app.post("/graph/links/citation")
def add_citation(from_section_id: str, to_ref: str) -> dict[str, str]:
    citations = getattr(app.state, "citations", [])
    citations.append({"from": from_section_id, "to": to_ref})
    app.state.citations = citations
    return {"status": "queued"}


@app.get("/healthz")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/readyz")
def ready() -> dict[str, str]:
    return {"status": "ready"}
