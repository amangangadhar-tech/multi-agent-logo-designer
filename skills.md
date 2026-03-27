# Skill: Multi-Agent Logo Designer

## Purpose
Autonomous brand identity system that accepts a company name and description, then produces a complete 10-page brand guideline PDF — logo, colour palette, typography, usage rules, and design applications — without human intervention between agents.

---

## API Stack

| Role | Model | API |
|---|---|---|
| **Llama (Analysis + Prompt Writing)** — brand strategy, colour, typography, ALL image prompt generation | `meta/llama-3.1-405b-instruct` | NVIDIA NIM Chat Completions |
| **Flux (All Visual Creation)** — logo PNG, icon PNG, cover art, mood board | `flux` (Flux Schnell) | Pollinations.AI |
| **Pillow (Variant Derivation)** — logo_white, logo_dark from primary | Python Pillow | Local (no API) |

---

## NVIDIA NIM API Reference

### Base URLs
```
Chat (LLMs):  https://integrate.api.nvidia.com/v1/chat/completions
Image Gen:    https://ai.api.nvidia.com/v1/genai/stabilityai/stable-diffusion-3-medium
```

### Authentication
```python
import os
NVIDIA_API_KEY = os.environ["NVIDIA_API_KEY"]  # set in .env / docker-compose

HEADERS_LLM = {
    "Authorization": f"Bearer {NVIDIA_API_KEY}",
    "Content-Type": "application/json"
}
HEADERS_IMG = {
    "Authorization": f"Bearer {NVIDIA_API_KEY}",
    "Content-Type": "application/json",
    "Accept": "application/json"
}
```

### LLM Call Helper — shared/nvidia_api.py
```python
import requests, time, os, json

NVIDIA_API_KEY = os.environ["NVIDIA_API_KEY"]
LLM_URL = "https://integrate.api.nvidia.com/v1/chat/completions"
IMG_URL = "https://ai.api.nvidia.com/v1/genai/stabilityai/stable-diffusion-3-medium"
MODEL   = "meta/llama-3.1-405b-instruct"

HEADERS_LLM = {"Authorization": f"Bearer {NVIDIA_API_KEY}", "Content-Type": "application/json"}
HEADERS_IMG = {"Authorization": f"Bearer {NVIDIA_API_KEY}", "Content-Type": "application/json", "Accept": "application/json"}

def call_llm(system_prompt: str, user_message: str,
             temperature: float = 0.7, max_tokens: int = 4096,
             retries: int = 3) -> str:
    payload = {
        "model": MODEL,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user",   "content": user_message}
        ],
        "temperature": temperature,
        "max_tokens": max_tokens,
        "stream": False
    }
    for attempt in range(retries):
        try:
            resp = requests.post(LLM_URL, headers=HEADERS_LLM, json=payload, timeout=120)
            resp.raise_for_status()
            return resp.json()["choices"][0]["message"]["content"]
        except requests.exceptions.HTTPError as e:
            code = e.response.status_code
            if code == 429 or code >= 500:
                time.sleep(5 * (attempt + 1))
                continue
            raise
    raise RuntimeError(f"LLM call failed after {retries} retries")
```

### Image Generation Helper — shared/nvidia_api.py (continued)
```python
import base64
from PIL import Image
from io import BytesIO
import numpy as np

def generate_image(prompt: str, output_path: str,
                   width: int = 1024, height: int = 1024,
                   steps: int = 30, cfg_scale: float = 7.0,
                   seed: int = 42, retries: int = 3) -> str:
    """
    Calls SD3-medium free endpoint. Returns output_path on success.
    Falls back to gradient PNG if endpoint unavailable.
    """
    payload = {
        "prompt": prompt,
        # FIX (Issue 3): standardised negative prompt — consistent across all agents
        "negative_prompt": "text, letters, words, watermark, blurry, distorted, ugly, logo",
        "width":  width,
        "height": height,
        "num_inference_steps": steps,
        "guidance_scale": cfg_scale,
        "seed": seed
    }
    for attempt in range(retries):
        try:
            resp = requests.post(IMG_URL, headers=HEADERS_IMG, json=payload, timeout=180)
            resp.raise_for_status()
            img_b64 = resp.json()["artifacts"][0]["base64"]
            img = Image.open(BytesIO(base64.b64decode(img_b64)))
            img.save(output_path, "PNG")
            return output_path
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 429:
                time.sleep(30 * (attempt + 1))
                continue
            break
        except Exception:
            break
    # Fallback: colour gradient
    _gradient_fallback("#1a1a2e", "#16213e", width, height, output_path)
    return output_path

def _gradient_fallback(hex1: str, hex2: str, w: int, h: int, path: str):
    def to_rgb(h): return tuple(int(h.lstrip('#')[i:i+2], 16) for i in (0,2,4))
    r1,g1,b1 = to_rgb(hex1)
    r2,g2,b2 = to_rgb(hex2)
    arr = np.zeros((h, w, 3), dtype=np.uint8)
    for x in range(w):
        t = x / w
        arr[:, x] = [int(r1*(1-t)+r2*t), int(g1*(1-t)+g2*t), int(b1*(1-t)+b2*t)]
    Image.fromarray(arr).save(path)
```

---

## Single LLM Role — ANALYTICAL_PERSONA only

Llama's job is ONLY to analyse and write. It never generates visual output.
For every image (logo, icon, cover, mood board), Llama writes a structured
Flux prompt as JSON — Flux then handles all actual image creation.

### ANALYTICAL_PERSONA
```
You are a senior brand strategist and design consultant with 20 years of experience
at top branding agencies. You think systematically, output precise JSON only, and
never add markdown formatting, code fences, or preamble. Your outputs are
deterministic and structured.
```
Used by: ALL agents (brand_strategist, logo_designer, colour_architect, typography_director, image_generator, guideline_compiler)

---

## Agent Roster & Responsibilities

| Agent | LLM Used | Image Gen? | Input | Output |
|---|---|---|---|---|
| `brand_strategist` | Llama — ANALYTICAL_PERSONA | ✗ | `user_input.json` | `brand_brief.json` |
| `logo_designer` | Llama — ANALYTICAL_PERSONA (prompt writing only) | ✅ Flux — primary (1200×600) + icon (512×512) | `brand_brief.json` | `logo_*.png`, `logo_metadata.json` |
| `colour_architect` | Llama — ANALYTICAL_PERSONA | ✗ | `brand_brief.json` | `colour_palette.json` |
| `typography_director` | LLM 1 | ✗ | `brand_brief.json` | `typography.json` |
| `image_generator` | LLM 1 (prompt) + SD3-medium | ✅ | `brand_brief.json` + `colour_palette.json` | `cover_art.png`, `mood_board.png` |
| `guideline_compiler` | LLM 1 | ✗ | all outputs | `guideline_pages.json` |
| `pdf_renderer` | None | ✗ | `guideline_pages.json` + all assets | `brand_guidelines.pdf` |

---

## Agent Communication Protocol

- All agents communicate via shared JSON files written to `./workspace/` directory.
- Each agent reads its inputs, produces its outputs, then appends `STATUS: DONE` to `./workspace/agent_log.txt`.
- The orchestrator reads `agent_log.txt` after each step and only triggers the next agent when previous is `DONE`.
- No agent starts until all its upstream dependencies are `DONE`.

### Dependency Graph
```
brand_strategist
        ↓
   logo_designer
        ↓
  colour_architect         ← sequential: image_generator depends on colour_palette.json
        ↓
typography_director ──┐
        ↓             │   ← FIX (Issue 1): these 2 run in PARALLEL (colour_palette.json
  image_generator ────┘     already exists when they start)
        ↓
 guideline_compiler
        ↓
  pdf_renderer
```

> ⚠️ logo_designer reads ONLY brand_brief.json. It does NOT read colour_palette.json.
> colour_architect runs AFTER logo_designer completes. Any attempt to read
> colour_palette.json inside logo_designer will cause a permanent deadlock.

> **Why colour_architect is no longer parallel:**
> `image_generator` reads `colour_palette.json` (primary + secondary hex) to write
> its Stable Diffusion prompt. Running it concurrently with `colour_architect` creates
> a race condition — the file may not exist yet. Sequencing `colour_architect` first
> costs only a few seconds and eliminates the crash entirely.

---

## brand_strategist Agent Rules

Input: `user_input.json` → `{ "company_name": str, "company_description": str }`

Output: `workspace/brand_brief.json`
```json
{
  "company_name": "string",
  "tagline": "string (≤6 words)",
  "brand_archetype": "Hero|Sage|Creator|Caregiver|Explorer|Rebel|Ruler|Magician|Jester|Lover|Innocent|Everyman",
  "personality_traits": ["trait1", "trait2", "trait3"],
  "tone_of_voice": "string",
  "industry": "string",
  "primary_emotion": "string",
  "colour_direction": "string",
  "logo_concept": "string — concrete SVG-drawable shape description",
  "logo_style": "wordmark|lettermark|pictorial|abstract|combination|emblem",
  "target_audience": "string"
}
```

### sys.path for all agents
```python
# FIX (Issue 5): portable sys.path — works both inside Docker (/app) and locally
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from shared.nvidia_api import call_llm, ANALYTICAL_PERSONA
```

---

## logo_designer Agent Rules

**Three-phase Flux logo process:**

Phase 1 — Llama writes Flux prompts (ANALYTICAL_PERSONA, 1 API call):
  Input:  brand_brief.json ONLY (colour_palette.json not yet available)
  Output: JSON with 4 keys: primary_logo_prompt, icon_prompt,
          primary_negative, icon_negative
  Key constraint: use brand_brief['colour_direction'] text for colour guidance.
  Do NOT attempt to read colour hex values — they don't exist yet.

Phase 2 — Flux generates primary logo + icon (2 Pollinations API calls):
  logo_primary.png : 1200×600, with wordmark text, white background
  icon_only.png    : 600×600 square, symbol only, no text, white background
  Both calls MUST pass their respective negative_prompt from Phase 1 output.

Phase 3 — Pillow derives variants (0 API calls):
  logo_white.png : hardcoded dark neutral bg + white logo content (greyscale mask)
  logo_dark.png  : hardcoded light bg + hardcoded brand-neutral blue logo content
  icon_only.png  : resized to 512×512 square with ImageOps.fit()
  Note: Variant backgrounds use hardcoded neutrals (colour_palette not available).
  The pdf_renderer applies real brand colours to page backgrounds separately.

---

## colour_architect Agent Rules

Uses **LLM 1**. Output: `workspace/colour_palette.json`

7 required slots: `primary`, `secondary`, `accent`, `neutral_dark`, `neutral_light`, `white`, `black`
Each: `{ name, hex, rgb, cmyk, use }`

Post-processing: compute WCAG AA ratio for primary vs #FFFFFF. If < 4.5 → re-call LLM 1 with correction note.

---

## typography_director Agent Rules

Uses **LLM 1**. Output: `workspace/typography.json`

Keys: `heading_font`, `body_font`, `accent_font`, `scale`, `line_height`, `letter_spacing`
body_font restricted to: Inter, DM Sans, Source Sans 3, Nunito Sans, Lato
Validate font URL via `requests.head()` → fallback to Poppins + Inter on failure.

---

## image_generator Agent Rules

> **Execution order note (Issue 1 fix):** This agent runs AFTER `colour_architect` completes,
> in parallel only with `typography_director`. `colour_palette.json` is guaranteed to exist
> before this agent reads it.

**Step 1 — Write prompts (LLM 1):**
```python
system = LLM1_PERSONA
user   = f"""Write two Stable Diffusion prompts as JSON {{cover_prompt, moodboard_prompt}}.
Each 40-80 words. No text/letters in images. Focus on mood, abstract shapes, lighting, texture.
Brand: {brand_brief['company_name']}, Industry: {brand_brief['industry']},
Archetype: {brand_brief['brand_archetype']}, Primary colour: {colour_palette['primary']['hex']}"""
```

**Step 2 — Generate images (SD3-medium):**
- `cover_art.png`: 1024×1024, steps=35, cfg=7.5
- `mood_board.png`: 1024×512, steps=30, cfg=7.0
- Negative prompt: `"text, letters, words, watermark, blurry, distorted, ugly, logo"` ← FIX (Issue 3)
- Fallback: gradient PNG from primary + secondary hex values (never halts pipeline)

---

## guideline_compiler Agent Rules

Uses **LLM 1**. Input: all upstream JSONs merged. Output: `workspace/guideline_pages.json`

Quality gates (run BEFORE LLM call):
- brand_brief: 11 fields non-empty
- colour_palette: 7 slots present
- typography: heading_font + body_font present
- assets/: ≥ 3 SVG files + cover_art.png or mood_board.png
- Gate failure → STATUS: ERROR, halt

10 mandatory pages:
```
1=cover, 2=about, 3=logo_primary, 4=logo_variants,
5=colour_palette, 6=typography, 7=usage_rules,
8=brand_voice, 9=design_system, 10=closing
```

---

## pdf_renderer Agent Rules

No API calls — pure Python with ReportLab + cairosvg.
Reads `guideline_pages.json` + all assets.
Outputs `workspace/brand_guidelines.pdf`.

Key rules:
- Cover: `cover_art.png` full-bleed background; logo + text overlaid
- About: `mood_board.png` as top-half image strip
- Colour swatches: `Table` cells with `BACKGROUND` style, 55mm×28mm
- SVGs → PNG via `cairosvg.svg2png()` before embedding
- Page numbers bottom-right, accent colour (skip pages 1 and 10)
- Fonts downloaded from Google Fonts, registered with `pdfmetrics.registerFont(TTFont(...))`

---

## Error Handling Standards

- Every agent: `try/except` around main logic, writes `STATUS: ERROR — {msg}` to agent_log.txt, calls `exit(1)`
- `image_generator`: failure writes gradient fallback, writes `STATUS: DONE (fallback)`, does NOT halt pipeline
- SVG parse failure: retry once → lettermark fallback → never crash
- NVIDIA 429: exponential backoff, max 3 retries
- JSON writes: atomic via `.tmp` + `os.rename()`

---

## Environment & Dependencies

```env
# .env
NVIDIA_API_KEY=nvapi-xxxxxxxxxxxxxxxxxxxx
```

```
# requirements.txt
requests>=2.31.0
reportlab>=4.0.0
cairosvg>=2.7.0
Pillow>=10.0.0
numpy>=1.24.0
python-dotenv>=1.0.0
PyPDF2>=3.0.0
```
<!-- FIX (Issue 2): PyPDF2 added — required by Step 19 integration test (pdf page count verification) -->

---

## File Structure

```
logo-designer/
├── main.py
├── user_input.json
├── .env                           # NVIDIA_API_KEY
├── shared/
│   └── nvidia_api.py              # call_llm() + generate_image() helpers
├── agents/
│   ├── brand_strategist.py
│   ├── logo_designer.py
│   ├── colour_architect.py
│   ├── typography_director.py
│   ├── image_generator.py
│   ├── guideline_compiler.py
│   └── pdf_renderer.py
├── workspace/
│   ├── agent_log.txt
│   ├── brand_brief.json
│   ├── colour_palette.json
│   ├── typography.json
│   ├── guideline_pages.json
│   └── assets/
│       ├── logo_primary.svg / .png
│       ├── logo_white.svg / .png
│       ├── logo_dark.svg / .png
│       ├── icon_only.svg / .png
│       ├── cover_art.png          # SD3-medium
│       └── mood_board.png         # SD3-medium
├── requirements.txt
├── Dockerfile
└── docker-compose.yml
```
