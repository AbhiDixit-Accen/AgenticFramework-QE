"""Browser Inspector API endpoints exposed via router."""

import hashlib
import logging
import os
from datetime import datetime
from typing import Any, Dict, Optional

from fastapi import APIRouter, HTTPException
from fastapi.responses import Response

from quality_engineering_agentic_framework.agents.browser_inspector import (
    BrowserInspectorAgent,
    SelectorEngine,
)
from quality_engineering_agentic_framework.llm.llm_factory import LLMFactory
from quality_engineering_agentic_framework.web.api.models import (
    BrowserInspectorRequest,
    BrowserInspectorResponse,
    LLMConfig,
)

router = APIRouter()
logger = logging.getLogger(__name__)

# Simple in-memory cache so inspector sessions can be fetched without re-calling the LLM
SESSION_CACHE: Dict[str, Dict[str, Any]] = {}


def _cache_inspector_capture(
    session_id: Optional[str],
    element_id: Optional[str],
    element_payload: Optional[Dict[str, Any]],
    selectors: Optional[list],
) -> None:
    """Persist captured element metadata for later retrieval."""
    if not session_id or not element_payload or not selectors:
        logger.debug(
            "Skipping cache write. session_id=%s element_present=%s selectors_present=%s",
            session_id,
            bool(element_payload),
            bool(selectors),
        )
        return

    session_state = SESSION_CACHE.setdefault(
        session_id,
        {
            "session_id": session_id,
            "created_at": datetime.utcnow().isoformat(),
            "url": element_payload.get("url"),
            "elements": {},
        },
    )

    if not element_id:
        element_id = element_payload.get("element_id") or element_payload.get("elementId")
    if not element_id:
        element_id = f"elem_{len(session_state['elements']) + 1:03d}"

    session_state["elements"][element_id] = {
        "element_data": element_payload,
        "selectors": selectors,
        "captured_at": datetime.utcnow().isoformat(),
    }
    logger.info(
        "Cached inspector element %s for session %s (total=%s)",
        element_id,
        session_id,
        len(session_state["elements"]),
    )


def _resolve_llm_config(requested_config: Optional[LLMConfig], require_api_key: bool = True) -> Optional[dict]:
    """Determine which LLM configuration to use for inspector actions."""
    if requested_config:
        config = requested_config.model_dump()
    else:
        config = {
            "provider": "openai",
            "model": "gpt-4",
            "api_key": os.environ.get("OPENAI_API_KEY", ""),
            "temperature": 0.2,
            "max_tokens": 2000,
        }

    # Fallback to environment key when not provided explicitly
    if not config.get("api_key"):
        config["api_key"] = os.environ.get("OPENAI_API_KEY", "")

    if require_api_key and not config.get("api_key"):
        raise HTTPException(status_code=400, detail="LLM API key missing for inspector request.")

    if not config.get("api_key"):
        return None

    config.setdefault("temperature", 0.2)
    config.setdefault("max_tokens", 2000)
    return config


def _generate_element_id(element_data: Optional[Dict[str, Any]]) -> str:
    """Generate a deterministic identifier for captured elements."""
    element_data = element_data or {}
    identifier = "_".join(
        [
            str(element_data.get("tagName", "")),
            str(element_data.get("id", "")),
            str(element_data.get("xpath", "")),
            str(element_data.get("session_id", "")),
        ]
    )
    return hashlib.md5(identifier.encode("utf-8")).hexdigest()[:12]


@router.post("/api/inspect/capture")
async def inspect_capture_element(request: BrowserInspectorRequest):
    """
    Capture element from browser and generate selectors.
    """
    logger.info("=== Received browser inspector request ===")
    logger.info(f"Action: {request.action}")
    
    try:
        llm_config = _resolve_llm_config(request.llm_config, require_api_key=False)

        if llm_config:
            llm = LLMFactory.create_llm(llm_config)
            agent = BrowserInspectorAgent(llm, {})
            result = await agent.process({
                "action": request.action,
                "payload": request.payload,
            })
            selectors = None
            if isinstance(result, dict):
                selectors = result.get("selectors")
                if not selectors and isinstance(result.get("data"), dict):
                    selectors = result["data"].get("selectors")
        else:
            logger.warning("No LLM configuration supplied; using heuristic selector engine.")
            element_payload = request.payload or {}
            selectors = SelectorEngine().generate_all_framework_selectors(element_payload)
            session_id = (
                element_payload.get("session_id")
                or element_payload.get("sessionId")
                or element_payload.get("session-id")
            )
            result = {
                "element_id": _generate_element_id(element_payload),
                "selectors": selectors,
                "session_id": session_id,
                "fallback": True,
            }

        session_id = (
            request.payload.get("session_id")
            or request.payload.get("sessionId")
            or request.payload.get("session-id")
        )
        _cache_inspector_capture(
            session_id=session_id,
            element_id=result.get("element_id") if isinstance(result, dict) else None,
            element_payload=request.payload,
            selectors=selectors,
        )

        return BrowserInspectorResponse(success=True, data=result)

    except Exception as e:
        logger.error(f"Error in inspector: {str(e)}", exc_info=True)
        return BrowserInspectorResponse(success=False, error=str(e))
    except Exception as e:
        logger.error(f"Error in inspector: {str(e)}", exc_info=True)
        return BrowserInspectorResponse(
            success=False,
            error=str(e)
        )


@router.post("/api/inspect/validate")
async def inspect_validate_selector(request: BrowserInspectorRequest):
    """
    Validate a selector and return stability score.
    """
    logger.info("=== Validating selector ===")
    
    try:
        llm_config = _resolve_llm_config(request.llm_config)
        
        llm = LLMFactory.create_llm(llm_config)
        agent = BrowserInspectorAgent(llm, {})
        
        result = await agent.process({
            "action": "validate_selector",
            "payload": request.payload
        })
        
        return BrowserInspectorResponse(
            success=True,
            data=result
        )
        
    except Exception as e:
        logger.error(f"Error validating selector: {str(e)}", exc_info=True)
        return BrowserInspectorResponse(
            success=False,
            error=str(e)
        )


@router.get("/api/inspect/session/{session_id}")
async def inspect_get_session(session_id: str):
    """
    Retrieve an inspection session.
    """
    logger.info(f"=== Retrieving session: {session_id} ===")
    
    session_payload = SESSION_CACHE.get(session_id)
    if not session_payload:
        logger.info("Session not yet cached; returning empty payload.")
        session_payload = {"session_id": session_id, "elements": {}}
    else:
        logger.info(
            "Returning %s cached elements for session %s",
            len(session_payload.get("elements", {})),
            session_id,
        )

    return BrowserInspectorResponse(
        success=True,
        data=session_payload,
    )


@router.get("/api/inspect/script")
async def get_inspector_script():
    """Serve the browser inspector JavaScript code with minimal escaping."""
    utils_dir = os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
        "utils",
    )

    standalone_path = os.path.join(utils_dir, "browser_inspector_standalone.js")
    if os.path.exists(standalone_path):
        with open(standalone_path, "r", encoding="utf-8") as standalone_file:
            return Response(content=standalone_file.read(), media_type="application/javascript")

    # Fallback to templated version if standalone not found
    template_path = os.path.join(utils_dir, "browser_inspector.js")
    if os.path.exists(template_path):
        with open(template_path, "r", encoding="utf-8") as template_file:
            script_content = template_file.read()

        start_marker = 'const QEAF_INSPECTOR_JS = `'
        end_marker = '`;'
        start_idx = script_content.find(start_marker)
        if start_idx != -1:
            start_idx += len(start_marker)
            end_idx = script_content.find(end_marker, start_idx)
            if end_idx != -1:
                inspector_code = script_content[start_idx:end_idx]
                inspector_code = inspector_code.replace(r"\${", "${").replace(r"\`", "`")
                return Response(content=inspector_code, media_type="application/javascript")

        return Response(content=script_content, media_type="application/javascript")

    raise HTTPException(status_code=404, detail="Inspector script not found")
