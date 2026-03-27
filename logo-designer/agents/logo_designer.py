import sys
import os
import json
import time
import numpy as np

sys.path.insert(0, '/app')
from shared.nvidia_api import call_llm, generate_image, ANALYTICAL_PERSONA
from PIL import Image, ImageOps


def main():
    root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    workspace_dir = os.path.join(root_dir, "workspace")
    log_path = os.path.join(workspace_dir, "agent_log.txt")
    assets_dir = os.path.join(workspace_dir, "assets")
    os.makedirs(assets_dir, exist_ok=True)

    try:
        # ── PHASE A — Load inputs ────────────────────────────────────
        # logo_designer runs BEFORE colour_architect — only brand_brief exists
        with open(os.path.join(workspace_dir, "brand_brief.json"), "r", encoding="utf-8") as f:
            brand_brief = json.load(f)

        # ── PHASE B — Llama writes Flux prompts (ANALYTICAL_PERSONA) ─
        prompt_request = f"""You are writing professional image generation prompts for Flux (a diffusion model)
to create a company logo and icon.

Output ONLY valid JSON (no markdown, no preamble) with exactly these 4 keys:

  primary_logo_prompt : string — detailed Flux prompt for the main logo (with wordmark text)
  icon_prompt         : string — detailed Flux prompt for the icon/symbol only (no text at all)
  primary_negative    : string — comma-separated list of things to avoid in the primary logo
  icon_negative       : string — comma-separated list of things to avoid in the icon

Rules for primary_logo_prompt:
  - Background must be PURE WHITE (#FFFFFF) — state this explicitly
  - Include the exact company name as readable text/wordmark
  - Describe typography style precisely: e.g. "bold geometric sans-serif wordmark"
  - Describe the icon/symbol concept: shape, style, visual metaphor
  - Describe colours using the colour direction text (e.g. "in deep navy blue and electric blue")
  - Always include these style keywords: "vector logo design, professional, clean,
    minimal, flat design, brand identity, high contrast, white background"

Rules for primary_negative:
  - Always include: "blurry, raster texture, photograph, 3D render, drop shadow,
    gradient background, multiple logos, watermark, sketch lines, rough edges,
    busy background, noise, jpeg artifacts"

Rules for icon_prompt:
  - Square composition (will be displayed at 512x512)
  - Symbol ONLY — absolutely NO company name, NO letters, NO text of any kind
  - Centred on pure white background
  - Same visual style and colours as the primary logo
  - Describe only the graphic mark/symbol

Rules for icon_negative:
  - Always include: "text, letters, words, company name, typography, blurry,
    gradient background, photograph, 3D, shadow, watermark, multiple symbols"

Brand inputs to use:
  Company name    : {brand_brief['company_name']}
  Tagline         : {brand_brief['tagline']}
  Industry        : {brand_brief['industry']}
  Archetype       : {brand_brief['brand_archetype']}
  Logo concept    : {brand_brief['logo_concept']}
  Logo style      : {brand_brief['logo_style']}
  Colour direction: {brand_brief['colour_direction']}
  Tone            : {brand_brief['tone_of_voice']}
  Target audience : {brand_brief['target_audience']}"""

        resp = call_llm(ANALYTICAL_PERSONA, prompt_request, temperature=0.7)
        resp = resp.strip()
        if resp.startswith("```json"):
            resp = resp[7:]
        elif resp.startswith("```"):
            resp = resp[3:]
        if resp.endswith("```"):
            resp = resp[:-3]

        flux_prompts = json.loads(resp.strip())

        required_keys = ['primary_logo_prompt', 'icon_prompt', 'primary_negative', 'icon_negative']
        for key in required_keys:
            if key not in flux_prompts or not isinstance(flux_prompts[key], str) or not flux_prompts[key].strip():
                raise ValueError(f"Missing or empty key in Flux prompt JSON: {key}")

        print("✅ Phase B: Flux prompts generated successfully")

        # ── PHASE C — Generate primary logo with Flux ────────────────
        primary_path = os.path.join(assets_dir, "logo_primary.png")
        generate_image(
            prompt=flux_prompts['primary_logo_prompt'],
            output_path=primary_path,
            width=1200,
            height=600,
            seed=42,
            negative_prompt=flux_prompts['primary_negative']
        )

        # Silent quality check — use numpy for O(n) performance
        img = Image.open(primary_path).convert("RGB")
        std_dev = np.std(np.array(img))
        if std_dev < 5:
            print("WARNING: Flux fallback gradient detected for logo_primary — image may be solid colour")

        print("✅ Phase C: Primary logo generated")

        # ── PHASE D — Generate icon-only with Flux ───────────────────
        icon_path = os.path.join(assets_dir, "icon_only.png")
        generate_image(
            prompt=flux_prompts['icon_prompt'],
            output_path=icon_path,
            width=600,
            height=600,
            seed=99,
            negative_prompt=flux_prompts['icon_negative']
        )

        # Silent quality check — use numpy for O(n) performance
        img_icon = Image.open(icon_path).convert("RGB")
        std_dev_icon = np.std(np.array(img_icon))
        if std_dev_icon < 5:
            print("WARNING: Flux fallback gradient detected for icon_only — image may be solid colour")

        print("✅ Phase D: Icon generated")

        # ── PHASE E — Derive logo variants with Pillow ───────────────
        primary = Image.open(primary_path).convert("RGBA")
        grey = primary.convert("L")
        # Content mask: pixels darker than 240 = logo content, rest = white background
        content_mask = grey.point(lambda p: 255 if p < 240 else 0)

        # logo_white.png — white logo for dark backgrounds
        # Hardcoded dark background — colour_palette not available at this stage
        dark_bg = Image.new("RGBA", primary.size, (20, 20, 40, 255))
        white_fg = Image.new("RGBA", primary.size, (255, 255, 255, 255))
        dark_bg.paste(white_fg, mask=content_mask)
        dark_bg.convert("RGB").save(os.path.join(assets_dir, "logo_white.png"), "PNG")

        # logo_dark.png — brand-coloured logo for light backgrounds
        # Hardcoded brand-neutral blue — colour_palette not available
        light_bg = Image.new("RGBA", primary.size, (248, 248, 250, 255))
        brand_fg = Image.new("RGBA", primary.size, (30, 58, 138, 255))
        light_bg.paste(brand_fg, mask=content_mask)
        light_bg.convert("RGB").save(os.path.join(assets_dir, "logo_dark.png"), "PNG")

        # icon_only.png — resize to standard 512×512 square
        icon = Image.open(icon_path)
        icon_sq = ImageOps.fit(icon, (512, 512), Image.LANCZOS)
        icon_sq.save(os.path.join(assets_dir, "icon_only.png"), "PNG")

        print("✅ Phase E: Logo variants derived")

        # ── PHASE F — Write logo_metadata.json ───────────────────────
        import datetime
        metadata = {
            "format": "png",
            "generated_at": datetime.datetime.utcnow().isoformat(),
            "logo_generated_by": "flux-pollinations",
            "variants_generated_by": "pillow",
            "primary_logo": {
                "path": "workspace/assets/logo_primary.png",
                "width_px": 1200,
                "height_px": 600,
                "safe_zone_px": 60,
                "min_width_px": 200
            },
            "icon_only": {
                "path": "workspace/assets/icon_only.png",
                "width_px": 512,
                "height_px": 512,
                "safe_zone_px": 24,
                "min_width_px": 48
            },
            "variants": {
                "logo_white": "workspace/assets/logo_white.png",
                "logo_dark": "workspace/assets/logo_dark.png"
            },
            "note": "Variant backgrounds use hardcoded neutrals — real brand hex applied by pdf_renderer"
        }

        tmp = os.path.join(assets_dir, "logo_metadata.json.tmp")
        final = os.path.join(assets_dir, "logo_metadata.json")
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(metadata, f, indent=2)
        os.replace(tmp, final)

        print("✅ Phase F: logo_metadata.json written")

        # ── PHASE G — Status ─────────────────────────────────────────
        with open(log_path, "a", encoding="utf-8") as f:
            f.write("logo_designer — STATUS: DONE\n")

        print("✅ logo_designer complete — all assets generated via Flux + Pillow")

    except Exception as e:
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(f"logo_designer — STATUS: ERROR — {e}\n")
        print(f"❌ logo_designer failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
