# Architecture — Multi-Agent Logo Designer

## System Overview

A fully autonomous brand identity pipeline powered entirely by NVIDIA's free NIM APIs. The user provides a company name and description. Seven specialised agents collaborate to produce a complete, print-ready 10-page brand guideline PDF — cover art, logo SVGs, colour system, typography, usage rules, brand voice, and design system — without any human intervention between steps.

---

## API Infrastructure

```
┌─────────────────────────────────────────────────────────────────┐
│                     NVIDIA NIM (Free Tier)                      │
│                                                                 │
│  ┌──────────────────────────────────────┐                       │
│  │  Chat Completions                    │                       │
│  │  POST integrate.api.nvidia.com/v1/  │  ← LLM 1 + LLM 2     │
│  │  chat/completions                   │    (same model,        │
│  │  Model: meta/llama-3.1-405b-instruct│     diff persona)     │
│  └──────────────────────────────────────┘                       │
│                                                                 │
│  ┌──────────────────────────────────────┐                       │
│  │  Image Generation (Free Endpoint)    │                       │
│  │  POST ai.api.nvidia.com/v1/genai/   │  ← Image Gen          │
│  │  stabilityai/stable-diffusion-3-    │    (SD3-medium)       │
│  │  medium                             │                        │
│  └──────────────────────────────────────┘                       │
│                                                                 │
│  Auth: Bearer NVIDIA_API_KEY (same key for both endpoints)      │
└─────────────────────────────────────────────────────────────────┘
```

### Why These Models?

| Decision | Choice | Reason |
|---|---|---|
| LLM | `meta/llama-3.1-405b-instruct` | Largest free model on NVIDIA NIM; 405B parameters handles complex JSON generation + SVG code reliably |
| Image | `stabilityai/stable-diffusion-3-medium` | Only "Free Endpoint" image model — no download, no GPU, no self-hosting. All FLUX variants are "Downloadable" only |
| Two LLM "roles" | Same model, different system prompts | Achieves specialisation (analytical vs visual-creative) without cost of a second model |

---

## High-Level Pipeline

```
┌─────────────────────────────────────────────────────┐
│              USER INPUT                             │
│  company_name + company_description                 │
│  → user_input.json                                  │
└───────────────────┬─────────────────────────────────┘
                    │
                    ▼
┌─────────────────────────────────────────────────────┐
│     AGENT 1 — brand_strategist                      │
│     API: LLM 1 (analytical persona)                 │
│     In:  user_input.json                            │
│     Out: workspace/brand_brief.json                 │
│     → company name, tagline, archetype, logo        │
│       concept, colour direction, target audience    │
└───────────────────┬─────────────────────────────────┘
                    │
                    ▼
┌─────────────────────────────────────────────────────┐
│     AGENT 2 — logo_designer                         │
│     API: LLM 1 (concept elaboration)                │
│          LLM 2 (SVG visual persona)                 │
│     In:  brand_brief.json                           │
│     Out: logo_primary.svg, logo_white.svg,          │
│          logo_dark.svg, icon_only.svg,              │
│          logo_metadata.json                         │
└───────────────────┬─────────────────────────────────┘
                    │
                    ▼
┌─────────────────────────────────────────────────────┐
│     AGENT 3 — colour_architect       [SEQUENTIAL]   │
│     API: LLM 1                                      │
│     In:  brand_brief.json                           │
│     Out: colour_palette.json                        │
│     ↑ Must complete before image_generator starts   │
│       (image_generator reads primary colour hex)    │
└──────────┬────────────────────────────────┬─────────┘
           │                               │
           ▼                               ▼
┌──────────────────────┐      ┌────────────────────────┐
│  AGENT 4             │      │  AGENT 5               │
│  typography_director │      │  image_generator        │
│                      │      │                        │
│  LLM 1               │      │  Step 1: LLM 1         │
│                      │      │  writes SD3 prompts    │
│  Out:                │      │  Step 2: SD3-medium    │
│  typography.json     │      │  generates images      │
│                      │      │                        │
│  [PARALLEL with      │      │  Out:                  │
│   image_generator]   │      │  cover_art.png         │
│                      │      │  mood_board.png        │
│                      │      │  [PARALLEL with        │
│                      │      │   typography_director] │
└──────────┬───────────┘      └────────────┬───────────┘
           │                               │
           └───────────────┬───────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────┐
│     AGENT 6 — guideline_compiler                    │
│     API: LLM 1 (analytical persona)                 │
│     In:  brand_brief + palette + typography +       │
│          logo_metadata + asset file list            │
│     Quality gates: 5 checks before LLM call        │
│     Out: workspace/guideline_pages.json             │
│          (10-page structured content JSON)          │
└───────────────────┬─────────────────────────────────┘
                    │
                    ▼
┌─────────────────────────────────────────────────────┐
│     AGENT 7 — pdf_renderer                          │
│     API: NONE — pure Python                         │
│     In:  guideline_pages.json + all assets          │
│     Tools: ReportLab + cairosvg + Pillow            │
│     Out: workspace/brand_guidelines.pdf  ✅         │
└─────────────────────────────────────────────────────┘
```

---

## Agent Specifications

### Agent 1 — brand_strategist
- **API calls**: 1 × LLM 1
- **Output**: JSON, 11 fields
- **Temperature**: 0.7 (creative but structured)
- **Failure mode**: if description is vague, default to `Sage` archetype

### Agent 2 — logo_designer
- **API calls**: 1 × LLM 1 (concept elaboration) + 1 × LLM 2 (SVG generation, up to 1 retry)
- **Output**: JSON containing 4 raw SVG strings → parsed + written as individual files
- **Validation**: `xml.etree.ElementTree.fromstring()` on each SVG string
- **Failure mode**: retry with simpler icon → geometric letter-mark fallback

### Agent 3 — colour_architect
- **API calls**: 1 × LLM 1 (up to 1 WCAG retry)
- **Post-processing**: Python WCAG AA contrast check on primary vs #FFFFFF
- **Failure mode**: if contrast < 4.5:1, re-call LLM 1 with darkening instruction
- **Sequencing**: runs alone after logo_designer; typography_director and image_generator wait for it

### Agent 4 — typography_director
- **API calls**: 1 × LLM 1
- **Post-processing**: `requests.head()` on Google Fonts URL to verify font exists
- **Failure mode**: Poppins + Inter fallback
- **Parallelism**: runs concurrently with image_generator (after colour_architect is DONE)

### Agent 5 — image_generator
- **API calls**: 1 × LLM 1 (prompt writing) + 2 × SD3-medium (cover + mood board)
- **Parallelism**: runs concurrently with typography_director (after colour_architect is DONE)
- **Failure mode**: gradient PNG fallback — NEVER halts pipeline
- **Outputs used in PDF**: cover_art.png on Page 1 (full bleed), mood_board.png on Page 2

### Agent 6 — guideline_compiler
- **API calls**: 1 × LLM 1 (largest context window usage)
- **Quality gates**: 5 checks before API call
- **Output**: 10-page structured JSON with all text copy and layout instructions

### Agent 7 — pdf_renderer
- **API calls**: 0
- **Libraries**: ReportLab (A4, platypus), cairosvg (SVG→PNG), Pillow (image manipulation)
- **Font loading**: downloads TTF from Google Fonts API, registers with pdfmetrics

---

## Data Schemas

### user_input.json
```json
{ "company_name": "string", "company_description": "string" }
```

### brand_brief.json
```json
{
  "company_name": "string", "tagline": "string",
  "brand_archetype": "string", "personality_traits": ["str","str","str"],
  "tone_of_voice": "string", "industry": "string",
  "primary_emotion": "string", "colour_direction": "string",
  "logo_concept": "string", "logo_style": "string", "target_audience": "string"
}
```

### colour_palette.json
```json
{
  "primary":       { "name":"", "hex":"", "rgb":"", "cmyk":"", "use":"" },
  "secondary":     { "..." : "..." },
  "accent":        { "..." : "..." },
  "neutral_dark":  { "..." : "..." },
  "neutral_light": { "..." : "..." },
  "white":         { "name":"White",  "hex":"#FFFFFF", "rgb":"255,255,255", "cmyk":"0,0,0,0",   "use":"Backgrounds" },
  "black":         { "name":"Black",  "hex":"#000000", "rgb":"0,0,0",       "cmyk":"0,0,0,100", "use":"Text fallback" }
}
```

### typography.json
```json
{
  "heading_font":  { "family":"", "weights":[], "google_import_url":"", "character":"" },
  "body_font":     { "family":"", "weights":[], "google_import_url":"", "character":"" },
  "accent_font":   { "family":"", "weights":[], "use":"" },
  "scale": { "h1_px":48, "h2_px":36, "h3_px":28, "h4_px":22, "body_px":16, "caption_px":12 },
  "line_height":    { "headings":1.2, "body":1.6 },
  "letter_spacing": { "headings_em":-0.02, "body_em":0, "caps_em":0.08 }
}
```

### guideline_pages.json
```json
{
  "pages": [
    {
      "page_number": 1,
      "page_type": "cover",
      "title": "string",
      "background_colour_key": "primary",
      "background_image": "cover_art.png",
      "sections": [
        { "type": "logo_display", "content": { "svg_file": "logo_white.svg", "width_mm": 80 } },
        { "type": "heading",      "content": { "text": "Company Name", "colour": "white" } },
        { "type": "body",         "content": { "text": "Tagline", "colour": "white_70" } }
      ]
    }
  ]
}
```

---

## Infrastructure

### docker-compose.yml
```yaml
version: "3.9"
services:
  logo-designer:
    build: .
    volumes:
      - ./workspace:/app/workspace
      - ./user_input.json:/app/user_input.json:ro
    environment:
      - NVIDIA_API_KEY=${NVIDIA_API_KEY}
    env_file:
      - .env
```

### Dockerfile
```dockerfile
FROM python:3.12-slim
# FIX (Issue 4): added libpangoft2-1.0-0 and libpangocairo-1.0-0 —
# required by cairosvg for font rendering when SVGs embed Google Fonts
RUN apt-get update && apt-get install -y \
    libcairo2 libpango-1.0-0 libffi-dev libgdk-pixbuf2.0-0 \
    libpangoft2-1.0-0 libpangocairo-1.0-0 \
    && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
CMD ["python", "main.py"]
```

### requirements.txt
```
requests>=2.31.0
reportlab>=4.0.0
cairosvg>=2.7.0
Pillow>=10.0.0
numpy>=1.24.0
python-dotenv>=1.0.0
PyPDF2>=3.0.0
```
<!-- FIX (Issue 2): PyPDF2 added — used in Step 19 integration test to verify 10-page PDF output -->

---

## Multi-Agent Execution Model

```python
import asyncio, subprocess

async def run_agent_async(name: str):
    proc = await asyncio.create_subprocess_exec(
        "python", f"agents/{name}.py",
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE
    )
    stdout, stderr = await proc.communicate()
    if proc.returncode != 0:
        raise RuntimeError(f"{name} failed:\n{stderr.decode()}")
    print(f"✅ {name} done")

async def main_async():
    await run_agent_async("brand_strategist")      # sequential
    await run_agent_async("logo_designer")          # sequential (needs brand_brief)

    # FIX (Issue 1): colour_architect runs alone first — image_generator reads
    # colour_palette.json, so it cannot start until colour_architect is DONE.
    # Running all three in parallel caused a race condition (FileNotFoundError).
    await run_agent_async("colour_architect")

    # Parallel: typography + image generation simultaneously
    # colour_palette.json now guaranteed to exist before either agent starts
    await asyncio.gather(
        run_agent_async("typography_director"),
        run_agent_async("image_generator")
    )

    await run_agent_async("guideline_compiler")     # sequential (needs all above)
    await run_agent_async("pdf_renderer")           # sequential (final step)
```

---

## 10-Page PDF Layout Reference

| Page | Title | Key Visual | Assets Used | Background |
|------|-------|-----------|-------------|------------|
| 1 | Cover | Logo centred, company name, tagline | `cover_art.png` (full bleed) + `logo_white.png` | SD3-generated image |
| 2 | About the Brand | Mood board strip, archetype badge, traits | `mood_board.png` + text | White |
| 3 | Primary Logo | Logo large, clear-space diagram, min-size rule | `logo_primary.png` | White + light grey zone |
| 4 | Logo Variants | 3 variants with use-case labels | `logo_white.png`, `logo_dark.png`, `icon_only.png` | Split dark/light |
| 5 | Colour Palette | 7 swatches, 4+3 grid layout | Hex-filled rectangles | White |
| 6 | Typography | Font specimens, type scale table | Google Fonts rendered | White |
| 7 | Do's & Don'ts | 4 green-tick + 4 red-cross rule cards | Text cards | White |
| 8 | Brand Voice | Tone descriptor, vocab pairs, sample copy | Text layout | Light neutral |
| 9 | Design System | Grid, spacing bars, radius demo, shadow | Programmatic shapes | White |
| 10 | Closing | Brand version, contact placeholder | Accent colour strip | Primary accent |

---

## Antigravity Agent Manager Setup

- **Spawn order**: each agent as a separate named workspace (`logo-brand-strategist`, etc.)
- **Shared volume**: mount `./workspace/` read-write to all workspaces
- **Review gates**: enable Review-Driven Development on `logo_designer` (visual milestone) and `pdf_renderer` (final output)
- **Agent sequencing**: colour_architect must complete before spawning typography_director and image_generator; spawn those two simultaneously

---

## How to Get Your NVIDIA API Key (Free)

1. Go to **https://build.nvidia.com**
2. Click "Sign Up" → create free account
3. Navigate to any model (e.g. Llama 3.1 405B)
4. Click "Get API Key" → copy `nvapi-...` key
5. Add to `.env`: `NVIDIA_API_KEY=nvapi-xxxxxxxxxxxxxxxxxxxx`
6. Free tier includes generous monthly token limits for both LLM and image generation
