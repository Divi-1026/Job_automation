"""
Generates ApplyAI_Presentation.pptx in the same folder.
Run:  python3 make_ppt.py
"""

from pptx import Presentation
from pptx.util import Inches, Pt, Emu
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN
from pptx.util import Inches, Pt
import copy

# ── Colour palette (matches the app's dark theme) ───────────────────────────
BG        = RGBColor(0x0F, 0x0E, 0x17)   # #0f0e17  deep navy
CARD      = RGBColor(0x1A, 0x18, 0x28)   # #1a1828
ACCENT    = RGBColor(0x6C, 0x63, 0xFF)   # #6c63ff  purple
ACCENT2   = RGBColor(0xFF, 0x65, 0x84)   # #ff6584  pink
GREEN     = RGBColor(0x43, 0xE0, 0xAD)   # #43e0ad
YELLOW    = RGBColor(0xFF, 0xD1, 0x66)   # #ffd166
WHITE     = RGBColor(0xFF, 0xFF, 0xFF)
GREY      = RGBColor(0xA7, 0xA5, 0xB5)
DIMGREY   = RGBColor(0x6B, 0x68, 0x80)

SLIDE_W = Inches(13.33)
SLIDE_H = Inches(7.5)


def new_prs():
    prs = Presentation()
    prs.slide_width  = SLIDE_W
    prs.slide_height = SLIDE_H
    return prs


def blank_slide(prs):
    blank_layout = prs.slide_layouts[6]   # blank layout
    return prs.slides.add_slide(blank_layout)


def fill_bg(slide, color=BG):
    """Fill the slide background with a solid colour."""
    bg   = slide.background
    fill = bg.fill
    fill.solid()
    fill.fore_color.rgb = color


def add_rect(slide, left, top, width, height, fill_color=CARD, line_color=None, alpha=None):
    shape = slide.shapes.add_shape(
        1,  # MSO_SHAPE_TYPE.RECTANGLE
        Inches(left), Inches(top), Inches(width), Inches(height)
    )
    shape.fill.solid()
    shape.fill.fore_color.rgb = fill_color
    if line_color:
        shape.line.color.rgb = line_color
        shape.line.width = Pt(0.75)
    else:
        shape.line.fill.background()
    return shape


def add_text(slide, text, left, top, width, height,
             font_size=18, bold=False, color=WHITE,
             align=PP_ALIGN.LEFT, italic=False, wrap=True):
    txBox = slide.shapes.add_textbox(
        Inches(left), Inches(top), Inches(width), Inches(height)
    )
    tf = txBox.text_frame
    tf.word_wrap = wrap
    p  = tf.paragraphs[0]
    p.alignment = align
    run = p.add_run()
    run.text = text
    run.font.size    = Pt(font_size)
    run.font.bold    = bold
    run.font.italic  = italic
    run.font.color.rgb = color
    return txBox


def add_multiline(slide, lines, left, top, width, height,
                  font_size=14, color=WHITE, line_color=None,
                  bold_first=False, spacing=None):
    """Add a textbox with multiple paragraphs."""
    txBox = slide.shapes.add_textbox(
        Inches(left), Inches(top), Inches(width), Inches(height)
    )
    tf = txBox.text_frame
    tf.word_wrap = True
    for i, line in enumerate(lines):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        if spacing:
            p.space_before = Pt(spacing)
        run = p.add_run()
        run.text = line
        run.font.size  = Pt(font_size)
        run.font.bold  = (i == 0 and bold_first)
        run.font.color.rgb = line_color if (line_color and i == 0) else color
    return txBox


def accent_bar(slide, left=0.3, top=0.18, width=0.06, height=0.55):
    """Gradient-look vertical bar using two stacked rectangles."""
    add_rect(slide, left, top,       width, height/2, fill_color=ACCENT)
    add_rect(slide, left, top+height/2, width, height/2, fill_color=ACCENT2)


# ════════════════════════════════════════════════════════════════════════════
#  SLIDES
# ════════════════════════════════════════════════════════════════════════════

def slide_title(prs):
    s = blank_slide(prs)
    fill_bg(s)

    # background glow blobs (rectangles with accent colours, blurred look)
    blob = add_rect(s, -1, -1, 6, 4, fill_color=RGBColor(0x1C, 0x18, 0x4A))
    blob.line.fill.background()

    blob2 = add_rect(s, 8, 4, 6, 4, fill_color=RGBColor(0x2A, 0x12, 0x1E))
    blob2.line.fill.background()

    # Logo
    add_text(s, "⚡ ApplyAI", 1.5, 1.5, 10, 1.2,
             font_size=52, bold=True, color=WHITE, align=PP_ALIGN.CENTER)

    # Gradient subtitle line using two separate text boxes
    add_text(s, "AI-Powered Job Application Automation",
             1.5, 2.9, 10, 0.7,
             font_size=22, bold=False, color=GREY, align=PP_ALIGN.CENTER)

    # Divider line
    add_rect(s, 5.16, 3.75, 3.0, 0.04, fill_color=ACCENT)

    # Tag line
    add_text(s, "Find  •  Match  •  Apply",
             1.5, 4.0, 10, 0.5,
             font_size=16, color=DIMGREY, align=PP_ALIGN.CENTER)

    # Team / course info
    add_text(s, "Final Year Project  |  2025–26",
             1.5, 5.5, 10, 0.5,
             font_size=13, color=DIMGREY, align=PP_ALIGN.CENTER, italic=True)

    # Tech pills
    for i, (label, col) in enumerate([
        ("React 19", ACCENT), ("FastAPI", GREEN), ("PostgreSQL", YELLOW), ("BeautifulSoup4", ACCENT2)
    ]):
        x = 2.3 + i * 2.2
        add_rect(s, x, 6.2, 1.9, 0.38, fill_color=CARD, line_color=col)
        add_text(s, label, x, 6.2, 1.9, 0.38,
                 font_size=11, bold=True, color=col, align=PP_ALIGN.CENTER)


def slide_problem(prs):
    s = blank_slide(prs)
    fill_bg(s)
    accent_bar(s)

    add_text(s, "The Problem", 0.55, 0.15, 9, 0.6,
             font_size=30, bold=True, color=WHITE)
    add_text(s, "Job searching today is broken for candidates",
             0.55, 0.82, 12, 0.4,
             font_size=15, color=GREY)
    add_rect(s, 0.55, 1.3, 12.2, 0.04, fill_color=RGBColor(0x2E, 0x2B, 0x47))

    pain_points = [
        ("🕒", "Time Consuming",
         "Manually visiting Indeed, Naukri, LinkedIn, Internshala\nevery day wastes hours of productive time."),
        ("🔍", "Skill Mismatch",
         "Generic job boards show irrelevant listings.\nCandidates miss roles that perfectly match their skills."),
        ("📋", "Application Fatigue",
         "Copying the same profile information across dozens\nof portals leads to inconsistent applications."),
        ("❌", "Missed Opportunities",
         "Fresh job postings get flooded within hours.\nManual checking means candidates always arrive late."),
    ]

    for i, (icon, title, body) in enumerate(pain_points):
        col = i % 2
        row = i // 2
        x = 0.55 + col * 6.3
        y = 1.6  + row * 2.55

        add_rect(s, x, y, 5.9, 2.3, fill_color=CARD,
                 line_color=RGBColor(0x2E, 0x2B, 0x47))
        add_text(s, icon, x + 0.2, y + 0.15, 0.7, 0.7, font_size=24)
        add_text(s, title, x + 0.9, y + 0.18, 4.8, 0.5,
                 font_size=15, bold=True, color=WHITE)
        add_text(s, body,  x + 0.9, y + 0.65, 4.7, 1.4,
                 font_size=11, color=GREY)


def slide_solution(prs):
    s = blank_slide(prs)
    fill_bg(s)
    accent_bar(s)

    add_text(s, "Our Solution — ApplyAI", 0.55, 0.15, 11, 0.6,
             font_size=30, bold=True, color=WHITE)
    add_text(s, "One platform. Your skills. Jobs delivered automatically.",
             0.55, 0.82, 12, 0.4, font_size=15, color=GREY)
    add_rect(s, 0.55, 1.3, 12.2, 0.04, fill_color=RGBColor(0x2E, 0x2B, 0x47))

    # Flow diagram: 3 boxes connected by arrows
    steps = [
        (ACCENT,  "01", "Build Profile",   "Add your skills, experience\nand upload your resume"),
        (GREEN,   "02", "Auto-Scrape",     "Background engine scrapes\nIndeed & Naukri every 10 min"),
        (ACCENT2, "03", "Browse & Apply",  "Filtered job feed matched\nto your exact skill set"),
    ]
    for i, (col, num, title, body) in enumerate(steps):
        x = 0.7 + i * 4.1
        add_rect(s, x, 1.6, 3.7, 3.6, fill_color=CARD,
                 line_color=col)
        add_rect(s, x + 0.2, 1.8, 0.65, 0.55, fill_color=col)
        add_text(s, num, x + 0.2, 1.8, 0.65, 0.55,
                 font_size=13, bold=True, color=WHITE, align=PP_ALIGN.CENTER)
        add_text(s, title, x + 0.2, 2.52, 3.3, 0.55,
                 font_size=17, bold=True, color=col)
        add_text(s, body, x + 0.2, 3.15, 3.3, 1.8,
                 font_size=12, color=GREY)

        # arrow between boxes
        if i < 2:
            add_text(s, "→", x + 3.75, 3.05, 0.4, 0.5,
                     font_size=22, bold=True, color=DIMGREY, align=PP_ALIGN.CENTER)

    # Bottom highlight
    add_rect(s, 0.55, 5.45, 12.2, 0.04, fill_color=RGBColor(0x2E, 0x2B, 0x47))
    add_text(s,
             "✅  No manual searching   ✅  Skill-matched results   ✅  Real-time updates",
             0.55, 5.6, 12.2, 0.5,
             font_size=13, color=GREEN, align=PP_ALIGN.CENTER, bold=True)


def slide_architecture(prs):
    s = blank_slide(prs)
    fill_bg(s)
    accent_bar(s)

    add_text(s, "System Architecture", 0.55, 0.15, 9, 0.6,
             font_size=30, bold=True, color=WHITE)
    add_rect(s, 0.55, 1.3, 12.2, 0.04, fill_color=RGBColor(0x2E, 0x2B, 0x47))

    # Three layers
    layers = [
        (ACCENT,  "Frontend  (React 19 + Vite + Redux)",
         ["Vite dev server on :5173", "React Router v7 — protected routes",
          "Redux Toolkit — auth + jobs state", "Tailwind CSS v4 — dark theme UI"]),
        (GREEN,   "Backend  (FastAPI + SQLAlchemy 2.0)",
         ["Async FastAPI on :8000", "JWT auth — signup / login / logout",
          "Async SQLAlchemy + asyncpg driver", "Background asyncio tasks per user"]),
        (YELLOW,  "Database & Scraping  (PostgreSQL + httpx + BS4)",
         ["PostgreSQL — users, jobs tables", "httpx async HTTP client",
          "BeautifulSoup4 — HTML parsing", "JSON API fallback for Naukri"]),
    ]

    for i, (col, heading, bullets) in enumerate(layers):
        x = 0.55 + i * 4.26
        add_rect(s, x, 1.55, 4.0, 5.45, fill_color=CARD, line_color=col)
        add_rect(s, x,      1.55, 4.0, 0.5,  fill_color=col)
        add_text(s, heading, x + 0.15, 1.57, 3.75, 0.46,
                 font_size=11, bold=True, color=BG)
        for j, b in enumerate(bullets):
            add_text(s, f"• {b}", x + 0.18, 2.3 + j * 0.82, 3.7, 0.7,
                     font_size=11, color=WHITE)

    # Connection arrows between layers
    for i in range(2):
        add_text(s, "⇄", 4.55 + i * 4.26, 3.98, 0.35, 0.5,
                 font_size=18, bold=True, color=DIMGREY, align=PP_ALIGN.CENTER)


def slide_tech_stack(prs):
    s = blank_slide(prs)
    fill_bg(s)
    accent_bar(s)

    add_text(s, "Tech Stack", 0.55, 0.15, 9, 0.6,
             font_size=30, bold=True, color=WHITE)
    add_rect(s, 0.55, 1.3, 12.2, 0.04, fill_color=RGBColor(0x2E, 0x2B, 0x47))

    techs = [
        # (icon, name, version/detail, colour, col, row)
        ("⚛️",  "React 19",         "Vite 6 + React Router v7",   ACCENT,  0, 0),
        ("🎨",  "Tailwind CSS v4",  "@import 'tailwindcss'",        ACCENT,  1, 0),
        ("🗄️", "Redux Toolkit",    "createSlice + createAsyncThunk", ACCENT, 2, 0),
        ("⚡",  "FastAPI",          "Python 3.13, async endpoints", GREEN,   0, 1),
        ("🐘",  "PostgreSQL",       "asyncpg + SQLAlchemy 2.0",     GREEN,   1, 1),
        ("🔐",  "JWT + bcrypt",     "python-jose + passlib",         GREEN,   2, 1),
        ("🌐",  "httpx",            "Async HTTP client v0.28",      YELLOW,  0, 2),
        ("🍜",  "BeautifulSoup4",   "lxml parser, CSS selectors",   YELLOW,  1, 2),
        ("🤖",  "Scrapers",         "Indeed.co.in + Naukri.com",    YELLOW,  2, 2),
    ]

    labels = ["Frontend", "Backend", "Scraping"]
    for li, (label, col) in enumerate(zip(labels, [ACCENT, GREEN, YELLOW])):
        add_text(s, label, 0.55, 1.56 + li * 1.72, 1.4, 0.4,
                 font_size=12, bold=True, color=col)

    for icon, name, detail, col, c, r in techs:
        x = 2.0 + c * 3.78
        y = 1.52 + r * 1.72
        add_rect(s, x, y, 3.5, 1.4, fill_color=CARD, line_color=col)
        add_text(s, icon, x + 0.15, y + 0.12, 0.55, 0.6, font_size=20)
        add_text(s, name,   x + 0.75, y + 0.12, 2.6, 0.42,
                 font_size=13, bold=True, color=WHITE)
        add_text(s, detail, x + 0.75, y + 0.58, 2.6, 0.65,
                 font_size=10, color=GREY)


def slide_features(prs):
    s = blank_slide(prs)
    fill_bg(s)
    accent_bar(s)

    add_text(s, "Key Features", 0.55, 0.15, 9, 0.6,
             font_size=30, bold=True, color=WHITE)
    add_rect(s, 0.55, 1.3, 12.2, 0.04, fill_color=RGBColor(0x2E, 0x2B, 0x47))

    features = [
        (ACCENT,  "🔐", "Authentication",
         "JWT-based signup / login / logout.\nPasswords hashed with bcrypt.\nProtected routes on frontend & backend."),
        (GREEN,   "👤", "Profile Manager",
         "Full profile: skills, experience, education,\nresume upload (PDF). Skills saved via direct\nSQL UPDATE (bypasses ORM ARRAY bug)."),
        (ACCENT2, "🤖", "Auto-Scraper Engine",
         "Background asyncio task per user.\nScrapes every 10 min automatically.\nRestarts instantly when skills are updated."),
        (YELLOW,  "💼", "Job Feed",
         "Deduplicated jobs from Indeed + Naukri.\nFilter by source tab.\nPolling after scrape trigger for live updates."),
        (RGBColor(0x56, 0xCF, 0xE1), "📊", "Dashboard",
         "Overview of profile completion, job stats,\nquick-access links to profile and jobs page."),
        (RGBColor(0xF7, 0x78, 0x4E), "🔄", "Dual Scrape Strategy",
         "Primary: BeautifulSoup HTML parser\n(notebook CSS selectors).\nFallback: Naukri internal JSON API."),
    ]

    for i, (col, icon, title, body) in enumerate(features):
        c = i % 3
        r = i // 3
        x = 0.55 + c * 4.26
        y = 1.55 + r * 2.75

        add_rect(s, x, y, 4.0, 2.55, fill_color=CARD, line_color=col)
        add_text(s, icon, x + 0.2, y + 0.18, 0.65, 0.65, font_size=22)
        add_text(s, title, x + 0.9, y + 0.2, 2.9, 0.5,
                 font_size=14, bold=True, color=col)
        add_text(s, body, x + 0.2, y + 0.82, 3.6, 1.55,
                 font_size=10, color=GREY)


def slide_scraper(prs):
    s = blank_slide(prs)
    fill_bg(s)
    accent_bar(s)

    add_text(s, "Scraping Engine", 0.55, 0.15, 9, 0.6,
             font_size=30, bold=True, color=WHITE)
    add_text(s, "How ApplyAI collects jobs from the web",
             0.55, 0.82, 12, 0.4, font_size=15, color=GREY)
    add_rect(s, 0.55, 1.3, 12.2, 0.04, fill_color=RGBColor(0x2E, 0x2B, 0x47))

    # Naukri panel
    add_rect(s, 0.55, 1.55, 5.9, 5.55, fill_color=CARD,
             line_color=YELLOW)
    add_rect(s, 0.55, 1.55, 5.9, 0.5, fill_color=YELLOW)
    add_text(s, "💼  Naukri.com Scraper", 0.75, 1.57, 5.6, 0.46,
             font_size=13, bold=True, color=BG)

    naukri_bullets = [
        "URL pattern: /python-developer-jobs-{page}",
        "Same URL format as Naukri-Web-Scraping notebook",
        "Primary: httpx + BeautifulSoup4",
        "CSS selectors (from notebook):",
        "   .srp-jobtuple-wrapper  →  job card",
        "   a.title                →  job title & URL",
        "   .comp-name             →  company",
        "   .exp-wrap / .sal-wrap  →  exp / salary",
        "   .tags-gt li            →  skills list",
        "Fallback: Naukri internal JSON API",
        "   endpoint: /jobapi/v3/search",
        "   used when JS hasn't rendered HTML",
    ]
    for j, b in enumerate(naukri_bullets):
        c = YELLOW if b.startswith("CSS") or b.startswith("URL") or b.startswith("Primary") or b.startswith("Fallback") else (WHITE if not b.startswith("  ") else GREY)
        add_text(s, ("• " if not b.startswith(" ") else "") + b,
                 0.75, 2.22 + j * 0.37, 5.5, 0.38,
                 font_size=10, color=c)

    # Indeed panel
    add_rect(s, 6.85, 1.55, 5.9, 5.55, fill_color=CARD,
             line_color=GREEN)
    add_rect(s, 6.85, 1.55, 5.9, 0.5, fill_color=GREEN)
    add_text(s, "🔍  Indeed.co.in Scraper", 7.05, 1.57, 5.6, 0.46,
             font_size=13, bold=True, color=BG)

    indeed_bullets = [
        "URL: indeed.co.in/jobs?q={skill}&l=India",
        "Strategy: httpx + BeautifulSoup4",
        "CSS selectors:",
        "   a.tapItem            →  job card",
        "   .jobTitle span       →  title",
        "   .companyName         →  company",
        "   .companyLocation     →  location",
        "   .salary-snippet-container → salary",
        "   .job-snippet          →  description",
        "User-Agent rotation (5 agents)",
        "Deduplication by URL",
        "max_per_skill = 10 results per skill",
    ]
    for j, b in enumerate(indeed_bullets):
        c = GREEN if b.startswith("URL") or b.startswith("Strategy") or b.startswith("CSS") else (WHITE if not b.startswith("  ") else GREY)
        add_text(s, ("• " if not b.startswith(" ") else "") + b,
                 7.05, 2.22 + j * 0.37, 5.5, 0.38,
                 font_size=10, color=c)


def slide_auth_db(prs):
    s = blank_slide(prs)
    fill_bg(s)
    accent_bar(s)

    add_text(s, "Auth & Database Design", 0.55, 0.15, 9, 0.6,
             font_size=30, bold=True, color=WHITE)
    add_rect(s, 0.55, 1.3, 12.2, 0.04, fill_color=RGBColor(0x2E, 0x2B, 0x47))

    # Auth flow
    add_rect(s, 0.55, 1.55, 5.9, 5.5, fill_color=CARD,
             line_color=ACCENT)
    add_rect(s, 0.55, 1.55, 5.9, 0.48, fill_color=ACCENT)
    add_text(s, "🔐  Authentication Flow", 0.75, 1.57, 5.6, 0.44,
             font_size=13, bold=True, color=WHITE)

    auth_steps = [
        ("POST /auth/signup",  "Hash password → save user → db.commit()\n→ issue JWT → start scraper loop"),
        ("POST /auth/login",   "Verify bcrypt hash → issue JWT\n→ (re)start scraper loop"),
        ("Bearer Token",       "All protected routes validate JWT\nvia OAuth2PasswordBearer"),
        ("POST /auth/logout",  "Cancel asyncio scraper task\n→ client clears localStorage"),
        ("ProtectedRoute",     "React component — redirects to /login\nif no token in Redux state"),
    ]
    for j, (endpoint, desc) in enumerate(auth_steps):
        y = 2.25 + j * 0.92
        add_rect(s, 0.75, y, 2.1, 0.58, fill_color=RGBColor(0x1E, 0x1C, 0x35), line_color=ACCENT)
        add_text(s, endpoint, 0.78, y + 0.05, 2.04, 0.48,
                 font_size=9, bold=True, color=ACCENT, align=PP_ALIGN.CENTER)
        add_text(s, desc, 2.95, y, 3.3, 0.72, font_size=9, color=GREY)

    # DB schema
    add_rect(s, 6.85, 1.55, 5.9, 5.5, fill_color=CARD, line_color=GREEN)
    add_rect(s, 6.85, 1.55, 5.9, 0.48, fill_color=GREEN)
    add_text(s, "🗄️  Database Schema", 7.05, 1.57, 5.6, 0.44,
             font_size=13, bold=True, color=BG)

    # users table
    add_text(s, "users", 7.05, 2.2, 5.5, 0.4,
             font_size=12, bold=True, color=GREEN)
    user_fields = [
        "id            UUID  PK",
        "full_name     TEXT",
        "email         TEXT  UNIQUE",
        "hashed_password TEXT",
        "skills        ARRAY(String)",
        "location / bio / experience_type",
        "current_role / current_company",
        "resume_url    TEXT",
        "is_active     BOOLEAN",
    ]
    for j, f in enumerate(user_fields):
        add_text(s, f"  {f}", 7.05, 2.58 + j * 0.33, 5.5, 0.34,
                 font_size=9, color=(WHITE if j < 5 else GREY))

    add_rect(s, 7.05, 5.68, 5.5, 0.03, fill_color=RGBColor(0x2E, 0x2B, 0x47))
    add_text(s, "jobs", 7.05, 5.78, 5.5, 0.4,
             font_size=12, bold=True, color=YELLOW)
    job_fields = [
        "id / user_id (FK)  title  company",
        "location  salary  url  source",
        "skill_query  description  scraped_at",
    ]
    for j, f in enumerate(job_fields):
        add_text(s, f"  {f}", 7.05, 6.2 + j * 0.3, 5.5, 0.3,
                 font_size=9, color=GREY)


def slide_scraper_logic(prs):
    s = blank_slide(prs)
    fill_bg(s)
    accent_bar(s)

    add_text(s, "Auto-Scrape Background Engine", 0.55, 0.15, 11, 0.6,
             font_size=28, bold=True, color=WHITE)
    add_text(s, "How jobs keep updating without any user action",
             0.55, 0.82, 12, 0.4, font_size=15, color=GREY)
    add_rect(s, 0.55, 1.3, 12.2, 0.04, fill_color=RGBColor(0x2E, 0x2B, 0x47))

    # Flow boxes
    flow = [
        (ACCENT,  "Login / Signup",      "JWT issued\nstart_user_scraper(user_id)"),
        (ACCENT,  "_scrape_loop()",      "asyncio.Task per user\nruns indefinitely"),
        (GREEN,   "_do_scrape_cycle()",  "Fetch fresh skills from DB\nScrape Indeed + Naukri"),
        (GREEN,   "persist_jobs()",      "Insert into jobs table\nsilently skip duplicates"),
        (YELLOW,  "Sleep 10 min",        "600 s in 10-s chunks\nfor prompt cancellation"),
        (ACCENT2, "Profile Update",      "User updates skills →\nrestart loop immediately"),
    ]

    box_w = 1.85
    for i, (col, title, body) in enumerate(flow[:5]):
        x = 0.6 + i * 2.45
        y = 1.65
        add_rect(s, x, y, box_w, 1.65, fill_color=CARD, line_color=col)
        add_rect(s, x, y, box_w, 0.4, fill_color=col)
        add_text(s, title, x + 0.1, y + 0.04, box_w - 0.15, 0.35,
                 font_size=10, bold=True, color=BG)
        add_text(s, body, x + 0.1, y + 0.5, box_w - 0.15, 1.1,
                 font_size=9, color=WHITE)
        if i < 4:
            add_text(s, "→", x + box_w + 0.07, y + 0.62, 0.47, 0.45,
                     font_size=18, bold=True, color=DIMGREY)

    # skips back arrow from sleep to loop
    add_rect(s, 0.6, 3.6, 11.65, 0.04, fill_color=RGBColor(0x2E, 0x2B, 0x47))
    add_text(s, "↩  Loop repeats from _scrape_loop() after each 10-min sleep",
             0.6, 3.72, 11.65, 0.45, font_size=11, color=DIMGREY, italic=True)

    # skill update restart
    add_rect(s, 6.85, 4.35, 5.9, 2.6, fill_color=CARD, line_color=ACCENT2)
    add_rect(s, 6.85, 4.35, 5.9, 0.44, fill_color=ACCENT2)
    add_text(s, "⚡  Instant Skill-Update Restart", 7.05, 4.37, 5.6, 0.4,
             font_size=12, bold=True, color=BG)
    for j, line in enumerate([
        "User saves new skills via PATCH /profile/me",
        "profile.py detects 'skills' in update_data",
        "Calls start_user_scraper(user_id)",
        "Cancels old loop task → creates new task",
        "New cycle starts immediately with fresh skills",
    ]):
        add_text(s, f"• {line}", 7.05, 4.9 + j * 0.38, 5.6, 0.38,
                 font_size=10, color=WHITE if j < 3 else GREY)

    # signup fix box
    add_rect(s, 0.55, 4.35, 5.9, 2.6, fill_color=CARD, line_color=GREEN)
    add_rect(s, 0.55, 4.35, 5.9, 0.44, fill_color=GREEN)
    add_text(s, "🐛  Race Condition Fix (Signup)", 0.75, 4.37, 5.6, 0.4,
             font_size=12, bold=True, color=BG)
    for j, line in enumerate([
        "Before: start_user_scraper before db.commit()",
        "  → background task found no user → loop died",
        "After: await db.commit() THEN start scraper",
        "  → user exists in DB when loop first queries",
        "Result: scraping always starts successfully",
    ]):
        add_text(s, line, 0.75, 4.9 + j * 0.38, 5.6, 0.38,
                 font_size=10, color=WHITE if not line.startswith("  ") else GREY)


def slide_ui_overview(prs):
    s = blank_slide(prs)
    fill_bg(s)
    accent_bar(s)

    add_text(s, "Application Pages", 0.55, 0.15, 9, 0.6,
             font_size=30, bold=True, color=WHITE)
    add_rect(s, 0.55, 1.3, 12.2, 0.04, fill_color=RGBColor(0x2E, 0x2B, 0x47))

    pages = [
        (ACCENT,  "/login\n/signup",      "Auth Pages",
         "• JWT token stored in localStorage\n• Redux state hydrated on refresh\n• Redirect to /dashboard on success"),
        (GREEN,   "/dashboard",            "Dashboard",
         "• Profile completion overview\n• Quick links to Profile & Jobs\n• Stats: skills count, job count"),
        (ACCENT2, "/profile",              "Profile Manager",
         "• Edit all personal/professional fields\n• Skills array saved via direct SQL UPDATE\n• Resume upload/delete (PDF, max 10 MB)"),
        (YELLOW,  "/jobs",                 "Jobs Feed",
         "• Source tabs: All / Indeed / Naukri\n• Live badge counts per source\n• Poll every 4 s after scrape trigger\n• Apply link opens job directly"),
    ]

    for i, (col, route, title, bullets) in enumerate(pages):
        c = i % 2
        r = i // 2
        x = 0.55 + c * 6.45
        y = 1.55 + r * 2.9

        add_rect(s, x, y, 6.15, 2.65, fill_color=CARD, line_color=col)
        add_rect(s, x, y, 6.15, 0.46, fill_color=col)
        add_text(s, f"{title}  —  {route}", x + 0.15, y + 0.04, 5.9, 0.38,
                 font_size=11, bold=True, color=BG)
        add_text(s, bullets, x + 0.2, y + 0.62, 5.7, 1.9,
                 font_size=11, color=WHITE)


def slide_future(prs):
    s = blank_slide(prs)
    fill_bg(s)
    accent_bar(s)

    add_text(s, "Future Enhancements", 0.55, 0.15, 9, 0.6,
             font_size=30, bold=True, color=WHITE)
    add_rect(s, 0.55, 1.3, 12.2, 0.04, fill_color=RGBColor(0x2E, 0x2B, 0x47))

    future = [
        (ACCENT,  "🤖", "AI Cover Letter Generator",
         "GPT-4 generates personalised cover letters\nbased on job description + user profile."),
        (GREEN,   "📊", "Match Score Analytics",
         "ML model scores each job listing against\nthe candidate's skills and experience range."),
        (ACCENT2, "📧", "Email / Push Notifications",
         "Alert user via email when high-match jobs\nappear in the feed within minutes."),
        (YELLOW,  "🌐", "More Job Portals",
         "Add LinkedIn, Internshala, AngelList,\nGlassdoor scrapers to the engine."),
        (RGBColor(0x56,0xCF,0xE1), "📄", "One-Click Apply",
         "Auto-fill application forms using\nstored profile & uploaded resume PDF."),
        (RGBColor(0xF7,0x78,0x4E), "📱", "Mobile App",
         "React Native cross-platform app\nwith push notification support."),
    ]

    for i, (col, icon, title, body) in enumerate(future):
        c = i % 3
        r = i // 3
        x = 0.55 + c * 4.26
        y = 1.55 + r * 2.7

        add_rect(s, x, y, 4.0, 2.5, fill_color=CARD, line_color=col)
        add_text(s, icon, x + 0.2, y + 0.18, 0.65, 0.65, font_size=22)
        add_text(s, title, x + 0.9, y + 0.2, 2.9, 0.5,
                 font_size=13, bold=True, color=col)
        add_text(s, body, x + 0.2, y + 0.82, 3.6, 1.5,
                 font_size=10, color=GREY)


def slide_thankyou(prs):
    s = blank_slide(prs)
    fill_bg(s)

    # bg blobs
    add_rect(s, -1, -1, 7, 5, fill_color=RGBColor(0x1C, 0x18, 0x4A))
    add_rect(s, 8.5, 3.5, 6, 5, fill_color=RGBColor(0x2A, 0x12, 0x1E))

    add_text(s, "Thank You!", 1.5, 1.6, 10, 1.1,
             font_size=52, bold=True, color=WHITE, align=PP_ALIGN.CENTER)

    add_rect(s, 4.16, 3.15, 5.0, 0.05, fill_color=ACCENT)

    add_text(s, "ApplyAI  —  AI-Powered Job Application Automation",
             1.5, 3.4, 10, 0.55,
             font_size=16, color=GREY, align=PP_ALIGN.CENTER)

    # Summary pills
    summary = [
        ("React 19 + Vite", ACCENT),
        ("FastAPI + PostgreSQL", GREEN),
        ("httpx + BeautifulSoup4", YELLOW),
        ("JWT Auth", ACCENT2),
    ]
    for i, (label, col) in enumerate(summary):
        x = 1.2 + i * 2.7
        add_rect(s, x, 4.3, 2.4, 0.45, fill_color=CARD, line_color=col)
        add_text(s, label, x, 4.3, 2.4, 0.45,
                 font_size=11, bold=True, color=col, align=PP_ALIGN.CENTER)

    add_text(s, "Questions & Discussion",
             1.5, 5.2, 10, 0.5,
             font_size=18, bold=True, color=ACCENT, align=PP_ALIGN.CENTER)

    add_text(s, "GitHub  |  Final Year Project  |  2025–26",
             1.5, 5.85, 10, 0.45,
             font_size=12, color=DIMGREY, align=PP_ALIGN.CENTER, italic=True)


# ── Build & save ─────────────────────────────────────────────────────────────

def build():
    prs = new_prs()

    slide_title(prs)
    slide_problem(prs)
    slide_solution(prs)
    slide_architecture(prs)
    slide_tech_stack(prs)
    slide_features(prs)
    slide_scraper(prs)
    slide_auth_db(prs)
    slide_scraper_logic(prs)
    slide_ui_overview(prs)
    slide_future(prs)
    slide_thankyou(prs)

    out = "/Users/dib5066/Desktop/final_year/ApplyAI_Presentation.pptx"
    prs.save(out)
    print(f"✅  Saved → {out}  ({len(prs.slides)} slides)")


if __name__ == "__main__":
    build()
