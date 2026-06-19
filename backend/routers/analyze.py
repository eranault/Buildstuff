"""
POST /api/analyze — main pipeline endpoint.

M1: clone + detect stack, return manifest + empty graph.
M2-M6: analyzers, merge, enrich will be wired in here.
"""
from __future__ import annotations

import asyncio
import shutil
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from core.ingest import IngestError, clone_repo
from core.manifest import StackManifest, detect_stack
from core.schema import GraphResult

router = APIRouter()


class AnalyzeRequest(BaseModel):
    url: str


class ManifestOut(BaseModel):
    detected_frameworks: list[str]
    db_layers: list[str]
    run_python_analyzer: bool
    run_js_analyzer: bool


class AnalyzeResponse(BaseModel):
    repo: str
    manifest: ManifestOut
    graph: GraphResult


@router.post("/analyze", response_model=AnalyzeResponse)
async def analyze(body: AnalyzeRequest) -> Any:
    local_path = None
    try:
        # Clone runs in a thread so it doesn't block the event loop
        local_path = await asyncio.to_thread(clone_repo, body.url)
        manifest: StackManifest = await asyncio.to_thread(
            detect_stack, local_path, body.url
        )

        # ── M2: JS/TS analyzer will be called here if manifest.run_js_analyzer ──
        # ── M3: Python analyzer will be called here if manifest.run_python_analyzer ──
        # ── M6: merge + Claude enrichment will run here ──

        graph = GraphResult(repo=body.url)

        return AnalyzeResponse(
            repo=body.url,
            manifest=ManifestOut(
                detected_frameworks=manifest.detected_frameworks,
                db_layers=manifest.db_layers,
                run_python_analyzer=manifest.run_python_analyzer,
                run_js_analyzer=manifest.run_js_analyzer,
            ),
            graph=graph,
        )

    except IngestError as exc:
        raise HTTPException(status_code=422, detail=str(exc))

    finally:
        # Clean up temp dir regardless of success or failure.
        # local_path is <tmp>/reponame, so parent is the mkdtemp dir.
        if local_path is not None:
            shutil.rmtree(local_path.parent, ignore_errors=True)
