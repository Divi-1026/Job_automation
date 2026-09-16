from datetime import datetime, timezone
from typing import Any
import json
import os
from pathlib import Path

from dotenv import load_dotenv

import httpx

SERVER_ROOT = Path(__file__).resolve().parents[2]
load_dotenv(SERVER_ROOT / ".env")

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.user import User
from app.models.extension_memory import ExtensionMemory
from app.models.extension_profile import ExtensionProfile
from app.routers.auth import get_current_user

router = APIRouter(
    prefix="/extension",
    tags=["Chrome Extension"],
)


# ============================================================
# Helpers
# ============================================================

def split_name(full_name: str | None):
    if not full_name:
        return "", ""

    parts = full_name.strip().split()

    if len(parts) == 1:
        return parts[0], ""

    first_name = parts[0]
    last_name = " ".join(parts[1:])

    return first_name, last_name


def normalize_question(value: str):
    if not value:
        return ""

    return " ".join(
        value
        .lower()
        .replace("_", " ")
        .replace("-", " ")
        .split()
    )

async def get_or_create_extension_profile(
    current_user: User,
    db: AsyncSession,
):
    result = await db.execute(
        select(ExtensionProfile)
        .where(
            ExtensionProfile.user_id == current_user.id
        )
    )

    existing_profile = result.scalar_one_or_none()

    if existing_profile:
        return existing_profile

    first_name, last_name = split_name(
        current_user.full_name
    )

    experience_type = None
    if current_user.experience_type:
        experience_type = getattr(
            current_user.experience_type,
            "value",
            current_user.experience_type,
        )

    skills_text = None
    if current_user.skills:
        if isinstance(current_user.skills, list):
            skills_text = ", ".join(current_user.skills)
        else:
            skills_text = str(current_user.skills)

    preferred_roles_text = None
    if current_user.preferred_roles:
        if isinstance(current_user.preferred_roles, list):
            preferred_roles_text = ", ".join(
                current_user.preferred_roles
            )
        else:
            preferred_roles_text = str(
                current_user.preferred_roles
            )

    extension_profile = ExtensionProfile(
        user_id=current_user.id,

        # Personal
        full_name=current_user.full_name,
        first_name=first_name,
        last_name=last_name,

        email=current_user.email,
        phone=current_user.phone,

        # Website profile does not currently have these
        date_of_birth=None,
        gender=None,
        address=None,
        city=current_user.location,
        state=None,
        country=None,
        pincode=None,

        # Links
        linkedin=current_user.linkedin_id,
        github=current_user.github_id,
        portfolio=current_user.portfolio_url,

        # Education
        highest_qualification=(
            current_user.highest_education
        ),
        college=current_user.college,
        graduation_year=(
            str(current_user.graduation_year)
            if current_user.graduation_year is not None
            else None
        ),

        degree=None,
        branch=None,
        cgpa=None,
        percentage=None,
        class10_percentage=None,
        class12_percentage=None,

        # Professional
        experience_type=experience_type,
        years_of_experience=(
            current_user.years_of_experience
        ),
        current_company=current_user.current_company,
        current_role=current_user.current_role,

        skills=skills_text,
        bio=current_user.bio,

        # Preferences
        preferred_roles=preferred_roles_text,
        preferred_locations=None,
        expected_ctc=None,
        notice_period=None,
        willing_to_relocate=None,
    )

    db.add(extension_profile)

    await db.commit()
    await db.refresh(extension_profile)

    return extension_profile
# ============================================================
# Schemas
# ============================================================

class MemoryCreateRequest(BaseModel):
    question: str
    answer: str

    field_context: dict[str, Any] | None = None

    source: str = "manual"

    confidence: float = 1.0


class ExtensionProfileUpdateRequest(BaseModel):
    key: str
    value: Any


class AIFieldRequest(BaseModel):
    index: int
    question: str
    field_context: dict[str, Any] | None = None
    choices: list[dict[str, Any]] | None = None
    profile_key: str | None = None


class AISuggestBatchRequest(BaseModel):
    fields: list[AIFieldRequest]


# ============================================================
# AI ASSISTANT
# ============================================================

SENSITIVE_OR_HIGH_STAKES_TERMS = (
    "disability",
    "veteran",
    "race",
    "ethnicity",
    "religion",
    "sexual orientation",
    "gender identity",
    "non-binary",
    "non binary",
    "marital status",
    "criminal",
    "arrest",
    "conviction",
    "work authorization",
    "authorized to work",
    "visa",
    "sponsorship",
    # User-only legal/consent decisions must never reach the model.
    "i agree",
    "consent",
    "privacy policy",
    "privacy notice",
    "terms and conditions",
    "terms of use",
    "terms of service",
    "i declare",
    "declaration",
    "i acknowledge",
    "acknowledgement",
    "authorization",
    "authorisation",
    "i certify",
    "certification",
    "electronic signature",
    "personal data",
    "data processing",
    "password",
    "passcode",
)


def extension_profile_to_ai_context(profile: ExtensionProfile) -> dict[str, Any]:
    return {
        "fullName": profile.full_name,
        "firstName": profile.first_name,
        "lastName": profile.last_name,
        "email": profile.email,
        "phone": profile.phone,
        "dateOfBirth": profile.date_of_birth,
        "gender": profile.gender,
        "address": profile.address,
        "city": profile.city,
        "state": profile.state,
        "country": profile.country,
        "pincode": profile.pincode,
        "linkedin": profile.linkedin,
        "github": profile.github,
        "portfolio": profile.portfolio,
        "highestQualification": profile.highest_qualification,
        "college": profile.college,
        "graduationYear": profile.graduation_year,
        "degree": profile.degree,
        "branch": profile.branch,
        "cgpa": profile.cgpa,
        "percentage": profile.percentage,
        "class10Percentage": profile.class10_percentage,
        "class12Percentage": profile.class12_percentage,
        "experienceType": profile.experience_type,
        "yearsOfExperience": profile.years_of_experience,
        "currentCompany": profile.current_company,
        "currentRole": profile.current_role,
        "skills": profile.skills,
        "bio": profile.bio,
        "preferredRoles": profile.preferred_roles,
        "preferredLocations": profile.preferred_locations,
        "expectedCTC": profile.expected_ctc,
        "noticePeriod": profile.notice_period,
        "willingToRelocate": profile.willing_to_relocate,
    }


def extract_json_object(text: str) -> dict[str, Any]:
    cleaned = (text or "").strip()

    if cleaned.startswith("```"):
        cleaned = cleaned.replace("```json", "", 1).replace("```", "", 1).strip()

    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        start = cleaned.find("{")
        end = cleaned.rfind("}")
        if start >= 0 and end > start:
            return json.loads(cleaned[start:end + 1])
        raise


async def call_groq_json(system_prompt: str, user_payload: dict[str, Any]) -> dict[str, Any]:
    api_key = os.getenv("GROQ_API_KEY", "").strip()
    model = os.getenv("GROQ_MODEL", "openai/gpt-oss-120b").strip()
    api_url = os.getenv(
        "GROQ_API_URL",
        "https://api.groq.com/openai/v1/chat/completions",
    ).strip()

    if not api_key:
        raise HTTPException(status_code=503, detail="AI assistant is not configured. Add GROQ_API_KEY to server/.env.")

    timeout = httpx.Timeout(30.0, connect=10.0)
    last_error: Exception | None = None

    # Retry once with an even stricter JSON-only instruction. This protects the
    # extension from occasional provider prose/code-fence/malformed output.
    for attempt in range(2):
        strict_prompt = system_prompt
        if attempt:
            strict_prompt += "\nCRITICAL RETRY: Return ONE valid JSON object only. No markdown, no prose, no code fences. It must contain a results array."

        request_body = {
            "model": model,
            "temperature": 0,
            "max_tokens": int(os.getenv("GROQ_MAX_TOKENS", "2000")),
            "response_format": {"type": "json_object"},
            "messages": [
                {"role": "system", "content": strict_prompt},
                {"role": "user", "content": json.dumps(user_payload, ensure_ascii=False)},
            ],
        }

        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                response = await client.post(
                    api_url,
                    headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
                    json=request_body,
                )
        except httpx.RequestError as exc:
            last_error = exc
            if attempt == 0:
                continue
            raise HTTPException(status_code=502, detail=f"AI provider request failed: {exc}") from exc

        if response.status_code >= 400:
            detail = response.text[:1000]
            last_error = ValueError(detail)
            if attempt == 0 and response.status_code in (408, 429, 500, 502, 503, 504):
                continue
            raise HTTPException(status_code=502, detail=f"AI provider returned {response.status_code}: {detail}")

        try:
            data = response.json()
            message = data["choices"][0]["message"]
            content = message.get("content") or ""
            print(f"[CareerSync][AI RAW RESPONSE attempt={attempt+1}]", content[:6000])
            parsed = extract_json_object(content)
            if isinstance(parsed, list):
                parsed = {"results": parsed}
            if not isinstance(parsed, dict) or not isinstance(parsed.get("results"), list):
                raise ValueError("AI JSON must contain a results array")
            print("[CareerSync][AI PARSED RESPONSE]", json.dumps(parsed, ensure_ascii=False)[:6000])
            return parsed
        except (KeyError, IndexError, TypeError, ValueError, json.JSONDecodeError) as exc:
            last_error = exc
            try:
                print("[CareerSync][AI INVALID RESPONSE OBJECT]", json.dumps(data, ensure_ascii=False)[:6000])
            except Exception:
                print("[CareerSync][AI INVALID RESPONSE BODY]", response.text[:6000])
            if attempt == 0:
                continue

    raise HTTPException(status_code=502, detail=f"AI provider returned invalid structured JSON after retry: {type(last_error).__name__}: {last_error}")


@router.post("/ai/suggest-batch")
async def ai_suggest_batch(
    payload: AISuggestBatchRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if not payload.fields:
        return {"success": True, "results": []}

    if len(payload.fields) > 60:
        raise HTTPException(
            status_code=400,
            detail="A maximum of 60 fields can be sent in one AI request.",
        )

    profile = await get_or_create_extension_profile(
        current_user=current_user,
        db=db,
    )

    memory_result = await db.execute(
        select(ExtensionMemory)
        .where(ExtensionMemory.user_id == current_user.id)
        .order_by(ExtensionMemory.updated_at.desc())
        .limit(20)
    )
    memories = memory_result.scalars().all()

    fields = [field.model_dump() for field in payload.fields]

    # Never let AI infer high-stakes / sensitive answers merely from unrelated
    # profile facts. Such questions remain available for explicit user input.
    blocked_indexes = set()
    ai_fields = []
    for field in fields:
        q = (field.get("question") or "").lower()
        if any(term in q for term in SENSITIVE_OR_HIGH_STAKES_TERMS):
            blocked_indexes.add(field["index"])
        else:
            ai_fields.append(field)

    if not ai_fields:
        return {
            "success": True,
            "results": [
                {
                    "index": field["index"],
                    "canAnswer": False,
                    "answer": None,
                    "confidence": 0,
                    "reason": "requires-explicit-user-answer",
                }
                for field in fields
            ],
        }

    def compact_nonempty(value):
        if isinstance(value, dict):
            out = {}
            for key, item in value.items():
                compacted = compact_nonempty(item)
                if compacted not in (None, "", [], {}):
                    out[key] = compacted
            return out
        if isinstance(value, list):
            out = [compact_nonempty(item) for item in value]
            return [item for item in out if item not in (None, "", [], {})]
        if isinstance(value, str):
            return value.strip()
        return value

    profile_context = compact_nonempty(extension_profile_to_ai_context(profile))
    memory_context = [
        {
            "q": str(memory.question)[:180],
            "a": str(memory.answer)[:180],
        }
        for memory in memories
        if memory.question and memory.answer
    ]

    # Large ATS dropdowns (countries, cities, universities, etc.) can contain
    # hundreds of options. Sending every option is what pushed Groq above the
    # 8k TPM/request budget. Keep exact likely matches plus a small sample.
    candidate_values: list[str] = []

    def collect_strings(value):
        if isinstance(value, dict):
            for item in value.values():
                collect_strings(item)
        elif isinstance(value, list):
            for item in value:
                collect_strings(item)
        elif isinstance(value, (str, int, float, bool)):
            text = str(value).strip()
            if 1 <= len(text) <= 120:
                candidate_values.append(text.lower())

    collect_strings(profile_context)
    for item in memory_context:
        candidate_values.append(item["a"].lower())

    compact_ai_fields = []
    for field in ai_fields:
        compact_field = {
            "index": field.get("index"),
            "question": str(field.get("question") or "")[:280],
            "profile_key": field.get("profile_key"),
        }

        context = field.get("field_context") or {}
        if isinstance(context, dict):
            compact_context = {}
            for key in ("type", "name", "id", "placeholder", "ariaLabel", "autocomplete"):
                value = context.get(key)
                if value not in (None, ""):
                    compact_context[key] = str(value)[:160]
            if compact_context:
                compact_field["context"] = compact_context

        choices = field.get("choices") or []
        if choices:
            cleaned_choices = []
            seen = set()
            for choice in choices:
                if not isinstance(choice, dict):
                    continue
                label = str(choice.get("label") or "").strip()[:120]
                value = str(choice.get("value") or "").strip()[:120]
                key = (label.lower(), value.lower())
                if key in seen:
                    continue
                seen.add(key)
                cleaned_choices.append({"label": label, "value": value})

            if len(cleaned_choices) <= 45:
                compact_field["choices"] = cleaned_choices
            else:
                likely = []
                for choice in cleaned_choices:
                    text = f"{choice['label']} {choice['value']}".lower()
                    if any(
                        candidate == choice["label"].lower()
                        or candidate == choice["value"].lower()
                        or (len(candidate) >= 3 and candidate in text)
                        for candidate in candidate_values
                    ):
                        likely.append(choice)

                selected = []
                selected_keys = set()
                for choice in likely + cleaned_choices[:8]:
                    key = (choice["label"].lower(), choice["value"].lower())
                    if key not in selected_keys:
                        selected_keys.add(key)
                        selected.append(choice)
                    if len(selected) >= 24:
                        break

                compact_field["choices"] = selected
                compact_field["totalChoiceCount"] = len(cleaned_choices)
                compact_field["choicesAreFiltered"] = True

        compact_ai_fields.append(compact_field)

    resume_text = (current_user.resume_text or "").strip()
    if len(resume_text) > 1800:
        resume_text = resume_text[:1800]

    system_prompt = r"""
You are the LAST fallback layer of CareerSync job-form autofill.
Offline exact-memory and regex/profile matching have already failed, so semantically
match ONLY the unresolved fields to facts that already exist in profile, learned
memory, or resume.

Rules:
1. Understand meaning, not wording. "provide your name" can mean fullName;
   "major/field of study/specialization" can mean branch; "telephone/contact" can
   mean phone; "institute/university" can mean college.
2. Never invent a personal fact, preference, legal statement, consent, experience,
   identity attribute, or application-specific answer.
3. If choices are supplied, the answer MUST be exactly one supplied label/value.
   Never return a profile category as the answer to a Yes/No field.
4. For boolean option questions such as "Pronouns: He/him", answer only Yes/No.
   If explicit saved gender is Female, He/him => No and She/her => Yes.
   Do not infer uncommon pronouns, race/ethnicity, disability, veteran status,
   gender identity categories, visa/work authorization, or other protected/legal
   attributes unless the exact answer exists in learned memory.
5. If a dropdown asks "location" but its choices are countries, use saved country
   (or an explicitly supported country from resume), not city.
6. For ambiguous, unsupported, sensitive or low-confidence fields return
   canAnswer=false so CareerSync asks the user once and learns the answer.
7. JSON only.

Return:
{"results":[{"index":0,"canAnswer":true,"answer":"...","confidence":0.0,"reason":"short"}]}
Return exactly one result per provided field index.
Unknown => canAnswer=false, answer=null, confidence=0.
""".strip()

    ai_response = await call_groq_json(
        system_prompt,
        {
            "profile": profile_context,
            "memory": memory_context,
            "resume": resume_text,
            "fields": compact_ai_fields,
        },
    )

    def normalize_choice_text(value: Any) -> str:
        return " ".join(str(value or "").lower().replace("_", " ").replace("-", " ").split())

    allowed_choices_by_index: dict[int, list[dict[str, Any]]] = {
        int(field.get("index")): (field.get("choices") or [])
        for field in compact_ai_fields
        if field.get("index") is not None
    }

    def coerce_ai_answer_to_choice(index: int, answer: Any):
        choices = allowed_choices_by_index.get(index) or []
        if not choices:
            return answer

        target = normalize_choice_text(answer)
        if not target:
            return None

        for choice in choices:
            label = choice.get("label")
            value = choice.get("value")
            if target in {normalize_choice_text(label), normalize_choice_text(value)}:
                # Return a real supplied choice, never an invented profile value.
                return value if value not in (None, "") else label

        return None

    raw_results = ai_response.get("results", [])
    by_index: dict[int, dict[str, Any]] = {}

    for item in raw_results:
        try:
            index = int(item.get("index"))
        except (TypeError, ValueError):
            continue

        answer = item.get("answer")
        can_answer = bool(item.get("canAnswer")) and answer not in (None, "")

        if can_answer:
            coerced_answer = coerce_ai_answer_to_choice(index, answer)
            if coerced_answer is None:
                can_answer = False
                answer = None
            else:
                answer = coerced_answer

        try:
            confidence = float(item.get("confidence", 0))
        except (TypeError, ValueError):
            confidence = 0

        by_index[index] = {
            "index": index,
            "canAnswer": can_answer,
            "answer": answer if can_answer else None,
            "confidence": max(0.0, min(1.0, confidence)),
            "reason": str(item.get("reason") or "ai-semantic-match")[:200],
        }

    results = []
    for field in fields:
        index = field["index"]

        if index in blocked_indexes:
            results.append({
                "index": index,
                "canAnswer": False,
                "answer": None,
                "confidence": 0,
                "reason": "requires-explicit-user-answer",
            })
            continue

        results.append(
            by_index.get(
                index,
                {
                    "index": index,
                    "canAnswer": False,
                    "answer": None,
                    "confidence": 0,
                    "reason": "ai-could-not-answer",
                },
            )
        )

    return {
        "success": True,
        "provider": "groq",
        "model": os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile"),
        "results": results,
    }


# ============================================================
# Ping
# ============================================================

@router.get("/ping")
async def extension_ping(
    current_user: User = Depends(get_current_user),
):
    return {
        "success": True,
        "message": "CareerSync extension API connected.",
        "userId": str(current_user.id),
    }


# ============================================================
# Profile
# ============================================================

@router.get("/profile")
async def get_extension_profile(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    profile = await get_or_create_extension_profile(
        current_user=current_user,
        db=db,
    )

    personal_info = {
        "fullName": profile.full_name,
        "firstName": profile.first_name,
        "lastName": profile.last_name,

        "email": profile.email,
        "phone": profile.phone,

        "linkedIn": profile.linkedin,
        "github": profile.github,
        "portfolio": profile.portfolio,

        "location": profile.city,

        "dateOfBirth": profile.date_of_birth,
        "gender": profile.gender,
        "address": profile.address,
        "city": profile.city,
        "state": profile.state,
        "country": profile.country,
        "pincode": profile.pincode,
    }

    education = {
        "highestEducation":
            profile.highest_qualification,

        "college":
            profile.college,

        "graduationYear":
            profile.graduation_year,

        "degree":
            profile.degree,

        "branch":
            profile.branch,

        "cgpa":
            profile.cgpa,

        "percentage":
            profile.percentage,

        "class10School":
            None,

        "class10Board":
            None,

        "class10Percentage":
            profile.class10_percentage,

        "class10Year":
            None,

        "class12School":
            None,

        "class12Board":
            None,

        "class12Percentage":
            profile.class12_percentage,

        "class12Year":
            None,
    }

    skills_list = []

    if profile.skills:
        skills_list = [
            skill.strip()
            for skill in profile.skills.split(",")
            if skill.strip()
        ]

    preferred_roles_list = []

    if profile.preferred_roles:
        preferred_roles_list = [
            role.strip()
            for role in profile.preferred_roles.split(",")
            if role.strip()
        ]

    preferred_locations_list = []

    if profile.preferred_locations:
        preferred_locations_list = [
            location.strip()
            for location in profile.preferred_locations.split(",")
            if location.strip()
        ]

    professional = {
        "experienceType":
            profile.experience_type,

        "yearsOfExperience":
            profile.years_of_experience,

        "currentCompany":
            profile.current_company,

        "currentRole":
            profile.current_role,

        "skills":
            skills_list,

        "preferredRoles":
            preferred_roles_list,

        "bio":
            profile.bio,

        "languages": [],
        "tools": [],
        "frameworks": [],
        "workExperience": [],
        "internships": [],
        "projects": [],
        "certifications": [],
        "achievements": [],
    }

    preferences = {
        "preferredRoles":
            preferred_roles_list,

        "jobTypes":
            [],

        "preferredLocations":
            preferred_locations_list,

        "expectedCTC":
            profile.expected_ctc,

        "noticePeriod":
            profile.notice_period,

        "willingToRelocate":
            profile.willing_to_relocate,
    }

    resume_available = bool(
        current_user.resume_filename
        or current_user.resume_url
        or current_user.resume_text
    )

    resume_parsed = bool(
        current_user.resume_parsed_at
        or current_user.resume_embedding
    )

    resume = {
        "available":
            resume_available,

        "filename":
            current_user.resume_filename,

        "url":
            current_user.resume_url,

        "parsed":
            resume_parsed,

        "parsedAt": (
            current_user.resume_parsed_at.isoformat()
            if current_user.resume_parsed_at
            else None
        ),
    }

    return {
        "success": True,
        "userId": str(current_user.id),

        "personalInfo":
            personal_info,

        "education":
            education,

        "professional":
            professional,

        "preferences":
            preferences,

        "resume":
            resume,
    }
@router.patch("/profile")
async def update_extension_profile(
    payload: ExtensionProfileUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    profile = await get_or_create_extension_profile(
        current_user=current_user,
        db=db,
    )

    key_map = {
        "fullName": "full_name",
        "firstName": "first_name",
        "lastName": "last_name",
        "email": "email",
        "phone": "phone",

        "dateOfBirth": "date_of_birth",
        "gender": "gender",

        "address": "address",
        "city": "city",
        "location": "city",
        "state": "state",
        "country": "country",
        "pincode": "pincode",

        "linkedin": "linkedin",
        "linkedIn": "linkedin",
        "github": "github",
        "portfolio": "portfolio",

        "highestEducation": "highest_qualification",
        "highestQualification": "highest_qualification",

        "college": "college",
        "graduationYear": "graduation_year",

        "degree": "degree",
        "branch": "branch",
        "cgpa": "cgpa",
        "percentage": "percentage",

        "class10Percentage": "class10_percentage",
        "class12Percentage": "class12_percentage",

        "experienceType": "experience_type",
        "yearsOfExperience": "years_of_experience",
        "currentCompany": "current_company",
        "currentRole": "current_role",

        "skills": "skills",
        "bio": "bio",

        "preferredRoles": "preferred_roles",
        "preferredLocations": "preferred_locations",

        "expectedCTC": "expected_ctc",
        "noticePeriod": "notice_period",
        "willingToRelocate": "willing_to_relocate",
    }

    field_name = key_map.get(payload.key)

    if not field_name:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported extension profile key: {payload.key}",
        )

    value = payload.value

    # Convert list values to comma-separated text
    if isinstance(value, list):
        value = ", ".join(
            str(item).strip()
            for item in value
            if str(item).strip()
        )

    # Clean strings
    if isinstance(value, str):
        value = value.strip()

    # Special handling for years of experience
    if field_name == "years_of_experience":
        if value in ("", None):
            value = None
        else:
            try:
                value = float(value)
            except (TypeError, ValueError):
                raise HTTPException(
                    status_code=400,
                    detail="yearsOfExperience must be a number.",
                )

    setattr(
        profile,
        field_name,
        value,
    )

    profile.updated_at = datetime.now(timezone.utc)

    await db.commit()
    await db.refresh(profile)

    return {
        "success": True,
        "message": "Extension profile updated.",
        "key": payload.key,
        "value": value,
    }
# ============================================================
# GET MEMORY
#
# Returns all learned answers for current user.
# ============================================================

@router.get("/memory")
async def get_extension_memory(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(ExtensionMemory)
        .where(
            ExtensionMemory.user_id
            == current_user.id
        )
        .order_by(
            ExtensionMemory.updated_at.desc()
        )
    )

    memories = result.scalars().all()

    return {
        "success": True,
        "count": len(memories),
        "items": [
            {
                "id": str(memory.id),

                "question":
                    memory.question,

                "normalizedQuestion":
                    memory.normalized_question,

                "answer":
                    memory.answer,

                "fieldContext":
                    memory.field_context,

                "source":
                    memory.source,

                "confidence":
                    memory.confidence,

                "usageCount":
                    memory.usage_count,

                "lastUsed": (
                    memory.last_used.isoformat()
                    if memory.last_used
                    else None
                ),

                "createdAt": (
                    memory.created_at.isoformat()
                    if memory.created_at
                    else None
                ),

                "updatedAt": (
                    memory.updated_at.isoformat()
                    if memory.updated_at
                    else None
                ),
            }
            for memory in memories
        ],
    }


# ============================================================
# POST MEMORY
#
# Save or update learned answer.
#
# Same normalized question for same user:
# -> update existing answer
# instead of creating duplicate.
# ============================================================

@router.post("/memory")
async def save_extension_memory(
    payload: MemoryCreateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    question = payload.question.strip()
    answer = payload.answer.strip()

    if not question:
        raise HTTPException(
            status_code=400,
            detail="Question is required.",
        )

    if not answer:
        raise HTTPException(
            status_code=400,
            detail="Answer is required.",
        )

    normalized = normalize_question(
        question
    )

    if not normalized:
        raise HTTPException(
            status_code=400,
            detail="Invalid question.",
        )

    result = await db.execute(
        select(ExtensionMemory)
        .where(
            ExtensionMemory.user_id
            == current_user.id,

            ExtensionMemory.normalized_question
            == normalized,
        )
    )

    existing = result.scalar_one_or_none()

    now = datetime.now(timezone.utc)

    if existing:
        existing.question = question
        existing.answer = answer
        existing.field_context = (
            payload.field_context
        )
        existing.source = payload.source
        existing.confidence = (
            payload.confidence
        )
        existing.updated_at = now

        memory = existing

    else:
        memory = ExtensionMemory(
            user_id=current_user.id,
            question=question,
            normalized_question=normalized,
            answer=answer,
            field_context=(
                payload.field_context
            ),
            source=payload.source,
            confidence=payload.confidence,
            usage_count=0,
        )

        db.add(memory)

    await db.commit()
    await db.refresh(memory)

    return {
        "success": True,
        "message": (
            "Memory updated."
            if existing
            else "Memory saved."
        ),

        "item": {
            "id": str(memory.id),

            "question":
                memory.question,

            "normalizedQuestion":
                memory.normalized_question,

            "answer":
                memory.answer,

            "fieldContext":
                memory.field_context,

            "source":
                memory.source,

            "confidence":
                memory.confidence,

            "usageCount":
                memory.usage_count,
        },
    }