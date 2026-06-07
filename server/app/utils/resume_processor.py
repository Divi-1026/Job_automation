"""
Resume text extraction and skill extraction using Google Gemini API.
"""

import io
import logging
import os
from typing import List

try:
    import PyPDF2
except ImportError:
    PyPDF2 = None

try:
    from google import genai
    from google.genai import types
except ImportError:
    genai = None

logger = logging.getLogger(__name__)

# Configure Gemini API
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if GEMINI_API_KEY and genai:
    # Initialize the new client
    client = genai.Client(api_key=GEMINI_API_KEY)
else:
    client = None


def extract_text_from_pdf(pdf_bytes: bytes) -> str:
    """Extract text from PDF file bytes."""
    if not PyPDF2:
        raise ValueError("PyPDF2 is not installed.")
    try:
        pdf_file = io.BytesIO(pdf_bytes)
        pdf_reader = PyPDF2.PdfReader(pdf_file)
        text = ""
        for page in pdf_reader.pages:
            page_text = page.extract_text()
            if page_text:
                text += page_text + "\n"
        return text.strip()
    except Exception as e:
        logger.error(f"PDF extraction error: {e}")
        raise ValueError("Failed to extract text from PDF.")


def extract_skills_from_text(resume_text: str) -> List[str]:
    """
    Use the new Gemini API client to extract technical skills from resume text.
    Returns a list of unique skills (preserving original casing).
    """
    if not GEMINI_API_KEY:
        logger.warning("GEMINI_API_KEY not set. Skipping skill extraction.")
        return []
    if not client:
        logger.warning("google-genai not installed or configured.")
        return []
    if not resume_text or len(resume_text.strip()) < 50:
        logger.warning("Resume text too short to extract skills.")
        return []

    try:
        # Use the latest 'gemini-2.0-flash' model
        model_name = "gemini-2.5-flash-lite"

        prompt = f"""
You are a skill extraction assistant. Extract ONLY technical skills from the resume below.

Return them as a comma-separated list. Include programming languages, frameworks, tools, databases, cloud platforms, etc.
Do NOT include soft skills like "communication", "leadership", "teamwork", "problem solving".

Examples of good skills: Python, JavaScript, React, Docker, AWS, PostgreSQL, Node.js, Machine Learning.

Resume text (first 3000 chars):
{resume_text[:3000]}

Return ONLY the comma-separated skills, nothing else.
"""
        # Use the generate_content method with the new client
        response = client.models.generate_content(
            model=model_name,
            contents=prompt
        )

        skills_text = response.text.strip()

        # Parse comma-separated values
        skills = [s.strip() for s in skills_text.split(",") if s.strip()]
        # Remove duplicates (case-insensitive) and normalize
        seen = set()
        unique_skills = []
        for skill in skills:
            skill_lower = skill.lower()
            if skill_lower not in seen:
                seen.add(skill_lower)
                unique_skills.append(skill)  # keep original casing
        logger.info(f"Extracted {len(unique_skills)} skills: {unique_skills[:10]}...")
        return unique_skills[:20]  # limit to top 20 skills

    except Exception as e:
        logger.error(f"Gemini API error: {e}")
        return []


def merge_skills(existing: List[str], new_skills: List[str]) -> List[str]:
    """Merge new skills into existing, avoiding duplicates (case-insensitive)."""
    existing_lower = {s.lower() for s in existing}
    merged = list(existing)
    for skill in new_skills:
        if skill.lower() not in existing_lower:
            merged.append(skill)
            existing_lower.add(skill.lower())
    return merged