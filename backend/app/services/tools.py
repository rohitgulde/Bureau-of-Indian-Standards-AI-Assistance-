"""
app/services/tools.py
──────────────────────
LangChain / Gemini function-calling tools for the BIS Knowledge Portal.

Tools defined
-------------
search_testing_labs(product_type, state, city=None)
    Queries the `laboratories` SQLite table and returns matching BIS/NABL labs.

verify_hallmark_huid(huid_code)
    Validates 6-char alphanumeric HUID format and returns step-by-step
    verification guide via BIS Care App / HUID Online portal.

get_certification_steps(scheme_name, product)
    Returns a structured 5-step checklist for Manak Online BIS registration,
    tailored to the named scheme and product.

ToolRegistry
    Holds all tools, binds them to Gemini, runs single-turn agent loop.

Usage
-----
    # Direct tool invocation:
    from app.services.tools import search_testing_labs
    result = search_testing_labs.invoke({"product_type": "cement", "state": "Delhi"})

    # Agent loop (Gemini function calling):
    from app.services.tools import ToolRegistry
    registry = ToolRegistry.from_env()
    response = await registry.agent_invoke("Find a lab to test PVC pipes in Mumbai")
"""

from __future__ import annotations

import logging
import os
import re
from typing import Any

from langchain_core.tools import StructuredTool
from langchain_google_genai import ChatGoogleGenerativeAI
from pydantic import BaseModel, Field, field_validator

from app.database.session import SessionLocal
from app.models.db_models import CertificationScheme, Laboratory

logger = logging.getLogger(__name__)


# =============================================================================
# Pydantic input schemas
# =============================================================================

class SearchLabsInput(BaseModel):
    product_type: str = Field(
        ..., min_length=2, max_length=100,
        description="Product to be tested. E.g. 'cement', 'PVC pipes', 'LED lights'.",
    )
    state: str = Field(
        ..., min_length=2, max_length=60,
        description="Indian state where the lab must be located. E.g. 'Delhi', 'Maharashtra'.",
    )
    city: str | None = Field(
        None, max_length=60,
        description="Optional city filter. E.g. 'Mumbai', 'Bengaluru', 'Chennai'.",
    )

    @field_validator("product_type", "state", mode="before")
    @classmethod
    def _strip(cls, v: str) -> str:
        return v.strip().lower() if isinstance(v, str) else v


class VerifyHuidInput(BaseModel):
    huid_code: str = Field(
        ..., min_length=6, max_length=6,
        description="6-character alphanumeric HUID code from a hallmarked gold/silver article.",
    )

    @field_validator("huid_code", mode="before")
    @classmethod
    def _upper(cls, v: str) -> str:
        return v.strip().upper() if isinstance(v, str) else v


class GetCertificationStepsInput(BaseModel):
    scheme_name: str = Field(
        ..., min_length=2, max_length=200,
        description="BIS scheme name or code: 'ISI Mark', 'CRS', 'FMCS', 'Hallmarking', 'Eco Mark'.",
    )
    product: str = Field(
        ..., min_length=2, max_length=150,
        description="Product seeking certification. E.g. 'cement', 'LED bulbs', 'gold jewellery'.",
    )


# =============================================================================
# Tool 1: search_testing_labs
# =============================================================================

def _search_testing_labs(product_type: str, state: str, city: str | None = None) -> dict[str, Any]:
    """Query SQLite laboratories table for accredited testing labs."""
    db = SessionLocal()
    try:
        q = (
            db.query(Laboratory)
            .filter(Laboratory.is_active == True)
            .filter(Laboratory.state.ilike(f"%{state}%"))
            .filter(Laboratory.testing_scope.ilike(f"%{product_type}%"))
        )
        if city:
            q = q.filter(Laboratory.city.ilike(f"%{city}%"))

        labs = q.order_by(Laboratory.name).limit(5).all()

        # Widen to state-only if city filter returned nothing
        if not labs and city:
            labs = (
                db.query(Laboratory)
                .filter(Laboratory.is_active == True)
                .filter(Laboratory.state.ilike(f"%{state}%"))
                .filter(Laboratory.testing_scope.ilike(f"%{product_type}%"))
                .order_by(Laboratory.name).limit(5).all()
            )

        lab_dicts = [
            {
                "name":          l.name,
                "city":          l.city,
                "state":         l.state,
                "pincode":       l.pincode,
                "address":       l.address,
                "phone":         l.phone or "N/A",
                "contact_email": l.contact_email or "N/A",
                "website":       l.website or "N/A",
                "accreditations":l.accreditations,
                "testing_scope": l.testing_scope,
                "latitude":      l.latitude,
                "longitude":     l.longitude,
            }
            for l in labs
        ]

        loc = f"{city}, {state}" if city else state
        message = (
            f"Found {len(lab_dicts)} BIS/NABL lab(s) in {loc} for '{product_type}'. "
            "Contact them to book a testing slot."
            if lab_dicts else
            f"No labs found in {loc} for '{product_type}'. "
            "Visit https://bis.gov.in or call 1800-11-4000 for the full lab directory."
        )
        return {"found": len(lab_dicts), "labs": lab_dicts,
                "query_params": {"product_type": product_type, "state": state, "city": city},
                "message": message}

    except Exception as exc:
        logger.exception("search_testing_labs error: %s", exc)
        return {"found": 0, "labs": [],
                "query_params": {"product_type": product_type, "state": state, "city": city},
                "message": f"Database error: {exc}"}
    finally:
        db.close()


search_testing_labs = StructuredTool.from_function(
    func=_search_testing_labs,
    name="search_testing_labs",
    description=(
        "Search for BIS-recognised and NABL-accredited testing laboratories "
        "for a specific product type in an Indian state / city. "
        "Use when the user asks where to get a product tested or needs a lab "
        "for BIS certification sample submission."
    ),
    args_schema=SearchLabsInput,
    return_direct=False,
)


# =============================================================================
# Tool 2: verify_hallmark_huid
# =============================================================================

_HUID_RE = re.compile(r"^[A-Z0-9]{6}$")

_FINENESS_MAP: dict[str, str] = {
    "999": "24 Karat (999 fine — 99.9% pure gold)",
    "995": "24 Karat (995 fine)",
    "958": "23 Karat (958 fine — Britannia gold)",
    "916": "22 Karat (916 fine — most common in India)",
    "875": "21 Karat (875 fine)",
    "750": "18 Karat (750 fine — popular for studded jewellery)",
    "585": "14 Karat (585 fine)",
    "375": "9 Karat (375 fine)",
}


def _verify_hallmark_huid(huid_code: str) -> dict[str, Any]:
    """Validate HUID format and return BIS Care App verification steps."""
    code = huid_code.strip().upper()
    valid = bool(_HUID_RE.match(code))

    error: str | None = None
    if len(code) != 6:
        error = f"HUID must be exactly 6 characters. Got {len(code)}: '{code}'."
    elif not valid:
        bad = set(re.findall(r"[^A-Z0-9]", code))
        error = f"Invalid characters: {', '.join(sorted(bad))}. Only A-Z and 0-9 allowed."

    steps = [
        f"1. Locate the HUID '{code}' engraved/laser-stamped on the jewellery (clasp, inner band, or tag).",
        "2. Download the free BIS Care App from Google Play or Apple App Store.",
        f"3. Open app → tap 'Verify HUID' → enter '{code}' → tap 'Verify'.",
        "4. Genuine result shows: article type, fineness (e.g. 916=22K), AHSC name, hallmarking date.",
        "5. If 'Not Found': article may be fake. File complaint at https://bis.gov.in or call 1800-11-4000.",
    ]

    app_steps = [
        "Download 'BIS Care' from Google Play / Apple App Store (free).",
        "Open app → Home → tap 'Verify HUID'.",
        f"Enter code: {code}",
        "Tap 'Verify' — result appears in ~2 seconds.",
        "Screenshot the result for your purchase records.",
    ]

    result: dict[str, Any] = {
        "huid_code": code,
        "format_valid": valid,
        "format_error": error,
        "verification_steps": steps,
        "bis_care_app_steps": app_steps,
        "web_verification_url": "https://huidonline.bis.gov.in/verify",
        "regulatory_note": (
            "HUID is mandatory for all gold jewellery sold in India since 1 April 2023 "
            "under BIS (Hallmarking) Regulations 2018. Each article gets a unique 6-char "
            "HUID at the Assaying & Hallmarking Centre (AHSC). Selling non-HUID jewellery "
            "is punishable with fines up to INR 1 lakh under BIS Act 2016."
        ),
        "fineness_guide": _FINENESS_MAP,
    }
    if not valid:
        result["warning"] = f"Code '{code}' has an invalid format. Recheck the engraving."

    logger.info("verify_hallmark_huid: code=%r valid=%s", code, valid)
    return result


verify_hallmark_huid = StructuredTool.from_function(
    func=_verify_hallmark_huid,
    name="verify_hallmark_huid",
    description=(
        "Validate a 6-character HUID (Hallmark Unique Identification) code from "
        "BIS-hallmarked gold or silver jewellery, and provide step-by-step instructions "
        "to verify it via the BIS Care App or HUID Online portal. "
        "Use when a user asks about hallmark verification, HUID codes, or jewellery authenticity."
    ),
    args_schema=VerifyHuidInput,
    return_direct=False,
)

# =============================================================================
# Tool 3: get_certification_steps
# =============================================================================

import json
from pathlib import Path

def _get_certification_steps(scheme: str = None) -> dict[str, Any]:
    """Retrieve JSON playbook for ISI_Mark, CRS, or FMCS."""
    if not scheme:
        return {"error": "Please specify which certification process you need: ISI Mark, CRS, or FMCS."}

    scheme_lower = scheme.lower()
    playbook_name = None
    if "isi" in scheme_lower:
        playbook_name = "ISI_Mark.json"
    elif "crs" in scheme_lower or "compulsory" in scheme_lower:
        playbook_name = "CRS.json"
    elif "fmcs" in scheme_lower or "foreign" in scheme_lower:
        playbook_name = "FMCS.json"
    
    if not playbook_name:
        return {"error": "I couldn't recognize the scheme. Please specify: ISI Mark, CRS, or FMCS."}

    playbook_path = Path(__file__).parent.parent / "data" / "playbooks" / playbook_name
    
    try:
        with open(playbook_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            return {"success": True, "playbook": data}
    except Exception as exc:
        logger.exception("Failed to load playbook %s: %s", playbook_name, exc)
        return {"error": f"Failed to load playbook for {scheme}."}


class GetCertificationStepsInput(BaseModel):
    scheme: str = Field(description="The name of the certification scheme (e.g. 'ISI Mark', 'CRS', 'FMCS')", default=None)

get_certification_steps = StructuredTool.from_function(
    func=_get_certification_steps,
    name="get_certification_steps",
    description="Get the step-by-step application workflow for BIS certifications like ISI Mark, CRS, or FMCS.",
    args_schema=GetCertificationStepsInput,
    return_direct=False,
)


# =============================================================================
# Tool registry
# =============================================================================

BIS_TOOLS: list[StructuredTool] = [
    search_testing_labs,
    verify_hallmark_huid,
    get_certification_steps,
]


class ToolRegistry:
    """
    Binds all BIS tools to Gemini and runs single-turn agent loops
    with native function calling (parallel tool use supported).
    """

    def __init__(
        self,
        model_name: str = "gemini-1.5-flash",
        google_api_key: str | None = None,
        tools: list[StructuredTool] | None = None,
    ) -> None:
        api_key = google_api_key or os.environ.get("GOOGLE_API_KEY", "")
        if not api_key:
            raise ValueError("GOOGLE_API_KEY is not set.")

        self.tools = tools or BIS_TOOLS
        self._tool_map: dict[str, StructuredTool] = {t.name: t for t in self.tools}

        self._llm = ChatGoogleGenerativeAI(
            model=model_name,
            google_api_key=api_key,
            temperature=0.0,
        )
        self._llm_with_tools = self._llm.bind_tools(self.tools)
        logger.info("ToolRegistry ready: model=%s tools=%s",
                    model_name, [t.name for t in self.tools])

    async def agent_invoke(self, user_message: str) -> dict[str, Any]:
        """
        Single-turn Gemini function-calling agent loop.

        Flow: send query -> Gemini picks tools -> execute tools -> Gemini synthesises.

        Returns dict with keys: output (str), tool_calls (list), iterations (int).
        """
        from langchain_core.messages import AIMessage, HumanMessage, ToolMessage

        messages = [HumanMessage(content=user_message)]

        # Turn 1: LLM decides whether to call tools
        ai_msg: AIMessage = await self._llm_with_tools.ainvoke(messages)
        messages.append(ai_msg)

        tool_records: list[dict] = []
        iterations = 1

        if hasattr(ai_msg, "tool_calls") and ai_msg.tool_calls:
            iterations = 2
            for tc in ai_msg.tool_calls:
                name    = tc["name"]
                args    = tc["args"]
                call_id = tc.get("id", name)

                logger.info("Tool called: %s(%s)", name, args)
                tool_obj = self._tool_map.get(name)
                try:
                    result = tool_obj.invoke(args) if tool_obj else {"error": f"Tool '{name}' not found."}
                except Exception as exc:
                    logger.error("Tool %s error: %s", name, exc)
                    result = {"error": str(exc)}

                tool_records.append({"tool_name": name, "tool_args": args, "result": result})
                messages.append(ToolMessage(content=str(result), tool_call_id=call_id))

            # Turn 2: synthesise tool results into final answer
            final: AIMessage = await self._llm_with_tools.ainvoke(messages)
            output = final.content
        else:
            output = ai_msg.content

        return {"output": output, "tool_calls": tool_records, "iterations": iterations}

    @classmethod
    def from_env(cls, model_name: str | None = None) -> "ToolRegistry":
        """Build from environment variables (GOOGLE_API_KEY, GEMINI_MODEL)."""
        return cls(model_name=model_name or os.environ.get("GEMINI_MODEL", "gemini-1.5-flash"))
