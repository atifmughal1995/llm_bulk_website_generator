# bulk_website_generator

A Django 5.0 backend for **AI-powered bulk website generation** with automated Netlify deployment. Generates homepages, service pages, city-specific landing pages, and listing pages using OpenAI/Anthropic, then builds and deploys static HTML to Netlify.

---

## Features

| Feature | Description |
|---|---|
| **AI Page Generation** | Generates homepage, service pages, and city pages via OpenAI (GPT-4o-mini) or Anthropic (Claude 3.7 Sonnet) |
| **Bulk City Page Creation** | Upload an Excel file to generate hundreds of location-specific landing pages |
| **Template System** | Reusable templates with ordered sections, AI-generated content, and custom CSS |
| **Visual Editor** | GrapesJS-powered inline HTML editor with AI regeneration and versioning |
| **Netlify Deployment** | One-click build and deploy to Netlify with custom domain support |
| **Image Management** | Unsplash integration + OpenAI image regeneration for broken images |
| **SEO & Tracking** | Meta tags, Google reCAPTCHA, EmailJS forms, tracking code injection |
| **Async Task Processing** | Celery + Redis for background page generation and Excel processing |

---

## Tech Stack

| Component | Technology |
|---|---|
| **Framework** | Django 5.0 + Django REST Framework |
| **AI Providers** | OpenAI API (`gpt-4o-mini`), Anthropic API (`claude-3-7-sonnet`) |
| **Task Queue** | Celery + Redis |
| **Database** | PostgreSQL |
| **Frontend Editor** | GrapesJS |
| **Deployment** | Netlify API |
| **Utilities** | BeautifulSoup4, openpyxl, Pillow, Tailwind CSS |

---

## Project Structure

```
bulk_website_generator/
├── manage.py                          # Django entry point
├── bulk_website_generator/
│   ├── settings.py                    # Django settings
│   ├── urls.py                        # Root URL config
│   ├── wsgi.py                        # WSGI application
│   ├── asgi.py                        # ASGI application
│   └── celery.py                      # Celery app configuration
├── apps/
│   └── projects/                      # Main application
│       ├── models.py                  # Database models
│       ├── views/
│       │   ├── api.py                 # REST API endpoints
│       │   └── web.py                 # Page-rendering views
│       ├── serializers.py             # DRF serializers
│       ├── urls.py                    # App URL routing
│       ├── admin.py                   # Django admin configuration
│       ├── forms.py                   # Form definitions
│       │
│       ├── services/                  # Business logic layer
│       │   ├── ai_service.py          # AI content generation
│       │   ├── page_service.py        # Page creation logic
│       │   ├── project_service.py     # Project management
│       │   ├── html_service.py        # HTML rendering
│       │   ├── image_service.py       # Image sourcing
│       │   ├── excel_service.py       # Excel file processing
│       │   └── deployment_service.py  # Netlify deployment
│       │
│       ├── clients/
│       │   └── netlify_client.py      # Netlify API client
│       │
│       ├── renderers/
│       │   └── html_renderer.py       # HTML section & page rendering
│       │
│       ├── html_utils/                # HTML manipulation utilities
│       │   ├── __init__.py
│       │   └── html_utils.py
│       │
│       ├── ai_utils.py                # OpenAI / Anthropic API calls
│       ├── image_utils.py             # Unsplash + OpenAI image handling
│       ├── prompts.py                 # AI prompt templates
│       ├── enums.py                   # Enums (page types, statuses, providers)
│       ├── exceptions.py              # Custom exceptions
│       ├── tasks.py                   # Celery async tasks
│       ├── migrations/                # Database migrations
│       ├── templates/                 # Django HTML templates
│       └── tests.py                   # Tests
├── templates/                         # Global templates
├── static/                            # Static files (CSS, JS, images)
├── media/                             # Uploaded media
├── logs/                              # Application logs
├── pyproject.toml                     # Project metadata & dependencies
├── .env.example                       # Environment variable template
└── README.md                          # This file
```

---

## Core Models

| Model | Purpose |
|---|---|
| `Project` | Client project config (base HTML, tracking codes, Netlify site, AI model) |
| `ProjectPage` | Homepage / service pages with versioning (`ProjectPageVersion`) |
| `Page` | Service pages tied to cities/zip codes with AI-generated sections |
| `Template` / `Section` / `TemplateSection` | Template system with ordered sections and default content |
| `AIGeneratedContent` | AI-generated content per template section per page |
| `State` / `County` / `City` | Geographic hierarchy with AI-generated city pages |
| `UploadedFile` | Excel bulk uploads for city page creation |
| `RegeneratedImage` | AI-regenerated images for broken image links |

---

## Environment Variables

Create a `.env` file in the project root:

```bash
# Django
DJANGO_DEBUG=True
SECRET_KEY=your-secret-key

# Database (PostgreSQL)
DB_NAME=bulk_website_generator
DB_USER=postgres
DB_PASSWORD=postgres
DB_HOST=localhost
DB_PORT=5432

# AI Providers
OPENAI_KEY=sk-...
OPENAI_IMG_KEY=sk-...
ANTHROPIC_KEY=sk-ant-...

# Netlify
NETLIFY_ACCESS_KEY=...

# reCAPTCHA
RECAPTCHA_SITE_ID=...

# EmailJS
EMAILJS_PUBLIC_KEY=...
EMAILJS_SERVICE_ID=...
EMAILJS_TEMPLATE_ID=...

# Celery
CELERY_BROKER_URL=redis://localhost:6379/0

# Backend IP (for redirect logic)
BACKEND_IP=157.245.218.95
```

---

## Setup

### Prerequisites

- Python 3.13+
- PostgreSQL
- Redis (for Celery)
- Virtual environment (recommended)

### Installation

```bash
# 1. Clone repository
git clone <repository-url>
cd bulk_website_generator

# 2. Create virtual environment
python -m venv venv
source venv/bin/activate  # Linux/macOS
# or
venv\Scripts\activate     # Windows

# 3. Install dependencies
pip install -e .

# 4. Configure environment
cp .env.example .env
# Edit .env with your credentials

# 5. Run migrations
python manage.py migrate

# 6. Start development server
python manage.py runserver
```

### Running Celery Worker

```bash
# Terminal 1: Django server
python manage.py runserver

# Terminal 2: Celery worker
celery -A bulk_website_generator worker -l info

# Terminal 3: Celery beat (if using periodic tasks)
celery -A bulk_website_generator beat -l info
```

---

## Key Endpoints

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/project/` | Projects listing |
| `GET/POST` | `/project/create/` | Create new project |
| `GET` | `/project/<id>/` | Project homepage |
| `GET` | `/project/<id>/detail/` | Project detail dashboard |
| `GET/POST` | `/project/<id>/homepage/edit/` | GrapesJS editor for homepage |
| `GET/POST` | `/project/<id>/service/<slug>/edit/` | GrapesJS editor for service page |
| `GET/POST` | `/project/<id>/city/<id>/edit/` | GrapesJS editor for city page |
| `POST` | `/project/<id>/publish/` | Build and deploy to Netlify |
| `POST` | `/project/<id>/client_domain/` | Configure custom domain |
| `POST` | `/page/create/` | Create city service page |
| `GET` | `/page/<page_id>/` | Get rendered service page HTML |
| `POST` | `/project/<id>/regenerate_html/` | AI-powered HTML regeneration |
| `POST` | `/project/upload/` | Upload Excel for bulk city page creation |

---

## Architecture: Frontend vs Backend Views

The `views/` package separates concerns into two modules:

```
views/
├── api.py    # Data operations, JSON responses, form handlers
└── web.py    # Full HTML page rendering for browser navigation
```

**`views/api.py`** — endpoints that process data:
- All `APIView` classes (`CreateProjectView`, `PublishProjectView`, etc.)
- Function-based API handlers (`save_page`, `regenerate_html`, `get_version_html`)
- Returns JSON or raw HTML snippets

**`views/web.py`** — endpoints that render pages:
- Page-rendering views (`homepage`, `city_page`, `project_detail`)
- Listing views (`states_listing`, `cities_listing`, `zipcodes_listing`)
- GrapesJS editor (`grapesjs_editor`)
- Returns complete HTML documents for browser navigation

---

## Services Layer

Business logic is organized into focused service classes:

| Service | Responsibility |
|---|---|
| `AIService` | OpenAI / Anthropic content generation with retry logic |
| `PageService` | Service page, city page, and project page creation |
| `ProjectService` | Project CRUD operations |
| `DeploymentService` | Static HTML build + Netlify deployment |
| `HtmlRenderer` | Section rendering and page assembly |
| `ImageService` | Unsplash sourcing + OpenAI image regeneration |
| `ExcelProcessingService` | Bulk Excel file processing for city pages |
