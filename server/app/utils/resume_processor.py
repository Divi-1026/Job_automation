"""
Resume processing utilities.

Responsibilities
----------------
1. Extract readable text from PDF.
2. Extract technical skills locally.
3. Optionally enhance skill extraction using Gemini.
4. Merge skills without duplicates.

IMPORTANT:
Resume parsing is performed only when the user
uploads or replaces a resume.

GET /jobs never parses the resume again.
"""

import io
import logging
import os
import re

from typing import List


try:
    import PyPDF2
except ImportError:
    PyPDF2 = None


try:
    from google import genai
except ImportError:
    genai = None


logger = logging.getLogger(
    __name__
)


# ---------------------------------------------------------
# Gemini configuration
# ---------------------------------------------------------

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")


if GEMINI_API_KEY and genai:

    try:
        gemini_client = genai.Client(
            api_key=GEMINI_API_KEY
        )

    except Exception:
        logger.exception(
            "Could not initialize Gemini client"
        )

        gemini_client = None

else:
    gemini_client = None


# ---------------------------------------------------------
# Local technical skill dictionary
#
# This guarantees resume parsing works even if Gemini
# is unavailable during the presentation.
# ---------------------------------------------------------

TECH_SKILLS = [

    # Languages
    "C",
    "C++",
    "C#",
    "Java",
    "Python",
    "JavaScript",
    "TypeScript",
    "Go",
    "Golang",
    "Rust",
    "Ruby",
    "PHP",
    "Kotlin",
    "Swift",

    # Frontend
    "HTML",
    "CSS",
    "React",
    "React.js",
    "Redux",
    "Tailwind CSS",
    "Bootstrap",
    "Angular",
    "Vue.js",
    "Next.js",
    "Vite",

    # Backend
    "Node.js",
    "Express.js",
    "FastAPI",
    "Flask",
    "Django",
    "Spring Boot",

    # Databases
    "SQL",
    "MySQL",
    "PostgreSQL",
    "MongoDB",
    "Redis",
    "SQLite",

    # Cloud / DevOps
    "AWS",
    "Azure",
    "GCP",
    "Docker",
    "Kubernetes",
    "Git",
    "GitHub",
    "CI/CD",
    "Linux",

    # API
    "REST",
    "REST API",
    "GraphQL",
    "WebSocket",
    "Socket.IO",

    # AI / ML
    "Machine Learning",
    "Deep Learning",
    "Artificial Intelligence",
    "AI",
    "NLP",
    "Natural Language Processing",
    "Computer Vision",
    "Scikit-learn",
    "TensorFlow",
    "PyTorch",
    "Pandas",
    "NumPy",

    # Gen AI
    "LangChain",
    "FAISS",
    "Hugging Face",
    "Gemini",
    "Groq",
    "OpenAI",

    # Other
    "Streamlit",
    "Postman",
    "Playwright",
    "Selenium",
    "Celery",
]


# ---------------------------------------------------------
# PDF text extraction
# ---------------------------------------------------------

def extract_text_from_pdf(
    pdf_bytes: bytes
) -> str:
    """
    Extract plain text from PDF bytes.
    """

    if PyPDF2 is None:
        raise RuntimeError(
            "PyPDF2 is not installed."
        )


    if not pdf_bytes:
        raise ValueError(
            "PDF file is empty."
        )


    try:

        pdf_file = io.BytesIO(
            pdf_bytes
        )

        reader = PyPDF2.PdfReader(
            pdf_file
        )


        pages = []


        for page in reader.pages:

            page_text = (
                page.extract_text()
                or ""
            )

            if page_text.strip():

                pages.append(
                    page_text.strip()
                )


        text = "\n".join(
            pages
        )


        # Normalize whitespace
        text = re.sub(
            r"[ \t]+",
            " ",
            text
        )

        text = re.sub(
            r"\n{3,}",
            "\n\n",
            text
        )


        return text.strip()


    except Exception as exc:

        logger.exception(
            "PDF extraction failed"
        )

        raise ValueError(
            "Failed to extract readable text from PDF."
        ) from exc


# ---------------------------------------------------------
# Local skill matching
# ---------------------------------------------------------

def _skill_present(
    text: str,
    skill: str
) -> bool:

    text_lower = text.lower()

    skill_lower = skill.lower()


    aliases = {

        "node.js": [
            "node.js",
            "nodejs",
            "node js",
        ],

        "react.js": [
            "react.js",
            "reactjs",
            "react",
        ],

        "vue.js": [
            "vue.js",
            "vuejs",
            "vue",
        ],

        "express.js": [
            "express.js",
            "expressjs",
            "express",
        ],

        "next.js": [
            "next.js",
            "nextjs",
            "next js",
        ],

        "c++": [
            "c++",
            "cpp",
        ],

        "c#": [
            "c#",
            "c sharp",
        ],

        "tailwind css": [
            "tailwind",
            "tailwind css",
        ],

        "rest api": [
            "rest api",
            "restful api",
            "restful",
        ],

        "machine learning": [
            "machine learning",
            "ml",
        ],

        "natural language processing": [
            "natural language processing",
            "nlp",
        ],

        "artificial intelligence": [
            "artificial intelligence",
            "ai",
        ],

        "hugging face": [
            "hugging face",
            "huggingface",
        ],

        "socket.io": [
            "socket.io",
            "socketio",
        ],

        "scikit-learn": [
            "scikit-learn",
            "sklearn",
        ],
    }


    candidates = aliases.get(
        skill_lower,
        [skill_lower]
    )


    for candidate in candidates:

        if candidate in text_lower:

            return True


    return False


def extract_skills_locally(
    resume_text: str
) -> List[str]:
    """
    Extract known technical skills without requiring
    an external API.
    """

    if not resume_text:

        return []


    detected = []


    for skill in TECH_SKILLS:

        if _skill_present(
            resume_text,
            skill
        ):

            detected.append(
                skill
            )


    return merge_skills(
        [],
        detected
    )
def extract_relevant_sections(resume_text: str) -> dict:
    """
    Extract Skills, Projects and Experience sections
    from resume text for semantic job matching.
    """

    if not resume_text:
        return {
            "skills": "",
            "projects": "",
            "experience": "",
        }

    lines = [
        line.strip()
        for line in resume_text.splitlines()
        if line.strip()
    ]

    section_aliases = {
        "skills": {
            "skills",
            "technical skills",
            "technical expertise",
            "technologies",
            "core skills",
            "key skills",
        },
        "projects": {
            "projects",
            "personal projects",
            "academic projects",
            "key projects",
            "major projects",
        },
        "experience": {
            "experience",
            "work experience",
            "professional experience",
            "employment",
            "internship",
            "internships",
        },
    }

    all_headings = set()

    for aliases in section_aliases.values():
        all_headings.update(
            alias.lower()
            for alias in aliases
        )

    sections = {
        "skills": [],
        "projects": [],
        "experience": [],
    }

    current_section = None

    for line in lines:

        normalized = re.sub(
            r"[:\-]+$",
            "",
            line.strip()
        ).strip().lower()

        found_section = None

        for section_name, aliases in section_aliases.items():
            if normalized in aliases:
                found_section = section_name
                break

        if found_section:
            current_section = found_section
            continue

        # Stop collecting when another known resume
        # section starts.
        if normalized in all_headings:
            current_section = None
            continue

        if current_section:
            sections[current_section].append(line)

    return {
        key: "\n".join(value).strip()
        for key, value in sections.items()
    }

# ---------------------------------------------------------
# Gemini skill extraction
# ---------------------------------------------------------

def _extract_skills_with_gemini(
    resume_text: str
) -> List[str]:

    if not gemini_client:

        return []


    if len(
        resume_text.strip()
    ) < 40:

        return []


    prompt = f"""
Extract technical skills from the following candidate resume.

Return ONLY a comma-separated list.

Include only:
- programming languages
- frontend/backend frameworks
- databases
- cloud platforms
- developer tools
- DevOps technologies
- AI/ML technologies
- APIs
- software engineering technologies

Do NOT return:
- communication
- teamwork
- leadership
- problem solving
- hobbies

Resume:
{resume_text[:6000]}
"""


    try:

        response = (
            gemini_client.models.generate_content(

                model="gemini-2.5-flash-lite",

                contents=prompt,

            )
        )


        text = (
            response.text
            or ""
        ).strip()


        if not text:

            return []


        skills = [

            value.strip()

            for value
            in text.split(",")

            if value.strip()

        ]


        return skills[:30]


    except Exception as exc:

        # Important:
        # Do NOT break resume upload if Gemini fails.
        logger.warning(

            "Gemini skill extraction failed: %s",

            exc,

        )

        return []


# ---------------------------------------------------------
# Public skill extraction function
# ---------------------------------------------------------

def extract_skills_from_text(
    resume_text: str
) -> List[str]:
    """
    Extract technical skills.

    Local extraction always runs.
    Gemini is used only as enhancement.
    """

    if not resume_text:

        return []


    local_skills = (
        extract_skills_locally(
            resume_text
        )
    )


    gemini_skills = (
        _extract_skills_with_gemini(
            resume_text
        )
    )


    combined = merge_skills(
        local_skills,
        gemini_skills
    )


    logger.info(

        "Resume skills extracted: %s",

        combined,

    )


    return combined[:40]


# ---------------------------------------------------------
# Skill merging
# ---------------------------------------------------------

def merge_skills(
    existing: List[str] | None,
    new_skills: List[str] | None,
) -> List[str]:
    """
    Merge two skill arrays and remove duplicates
    case-insensitively.
    """

    existing = (
        existing
        or []
    )

    new_skills = (
        new_skills
        or []
    )


    seen = set()

    merged = []


    for skill in [
        *existing,
        *new_skills,
    ]:

        if not skill:

            continue


        clean = (
            skill
            .strip()
        )


        if not clean:

            continue


        key = clean.lower()


        if key in seen:

            continue
        seen.add(
            key
        )

        merged.append(
            clean
        )


    return merged