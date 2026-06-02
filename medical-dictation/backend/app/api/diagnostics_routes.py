"""Lightweight diagnostics endpoints."""

import time

from fastapi import APIRouter, Request

from app.observability.events import log_event
from app.observability.request_id import request_id_from_state
from app.services.diagnostics.service import DiagnosticsService

router = APIRouter(prefix="/diagnostics", tags=["diagnostics"])


def get_diagnostics_service(request: Request) -> DiagnosticsService:
    return DiagnosticsService(
        request.app.state.config,
        request.app.state.stt_service,
        getattr(request.app.state, "stt_metrics", None),
    )


@router.get("")
def diagnostics(request: Request) -> dict:
    started = time.perf_counter()
    request_id = request_id_from_state(request)
    service = get_diagnostics_service(request)
    result = service.aggregate()
    result["request_id"] = request_id
    log_event(
        category="DIAGNOSTICS",
        event="diagnostics.aggregate",
        status=result["status"],
        duration_ms=(time.perf_counter() - started) * 1000,
        request_id=request_id,
    )
    return result


@router.get("/stt")
def stt_diagnostics(request: Request) -> dict:
    request_id = request_id_from_state(request)
    result = get_diagnostics_service(request).stt()
    log_event(
        category="DIAGNOSTICS",
        event="diagnostics.stt",
        status=result["status"],
        provider=result["provider"],
        request_id=request_id,
    )
    return {"request_id": request_id, "stt": result}


@router.get("/llm")
def llm_diagnostics(request: Request) -> dict:
    request_id = request_id_from_state(request)
    result = get_diagnostics_service(request).llm()
    log_event(
        category="DIAGNOSTICS",
        event="diagnostics.llm",
        status=result["status"],
        provider=result["provider"],
        request_id=request_id,
        error=result.get("last_error"),
    )
    return {"request_id": request_id, "llm": result}


@router.get("/tts")
def tts_diagnostics(request: Request) -> dict:
    request_id = request_id_from_state(request)
    result = get_diagnostics_service(request).tts()
    log_event(
        category="DIAGNOSTICS",
        event="diagnostics.tts",
        status=result["status"],
        provider=result["provider"],
        request_id=request_id,
        error=result.get("last_error"),
    )
    return {"request_id": request_id, "tts": result}
