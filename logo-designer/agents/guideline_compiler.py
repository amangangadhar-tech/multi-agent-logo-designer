import sys, os, json, traceback

# FIX (Issue 5): portable sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from shared.nvidia_api import call_llm, ANALYTICAL_PERSONA

def append_log(msg):
    workspace = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "workspace")
    log_path = os.path.join(workspace, "agent_log.txt")
    with open(log_path, "a", encoding="utf-8") as f:
        f.write(msg + "\n")

def main():
    try:
        workspace = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "workspace")
        
        # Load JSONs
        def load_json(name):
            path = os.path.join(workspace, name)
            if not os.path.exists(path):
                raise Exception(f"{name} missing")
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)

        brand_brief = load_json("brand_brief.json")
        colour_palette = load_json("colour_palette.json")
        typography = load_json("typography.json")
        
        # PART A — Quality Gates (fail fast BEFORE any API call):
        # Gate 1: workspace/brand_brief.json — all 11 fields non-empty
        bb_expected = ["company_name", "tagline", "brand_archetype", "personality_traits", "tone_of_voice", 
                       "industry", "primary_emotion", "colour_direction", "logo_concept", "logo_style", "target_audience"]
        for field in bb_expected:
            val = brand_brief.get(field)
            if not val or (isinstance(val, str) and not val.strip()) or (isinstance(val, list) and not val):
                raise Exception(f"brand_brief {field} is empty or missing")
        if len(brand_brief.keys()) < 11:
            raise Exception("brand_brief has fewer than 11 fields")

        # Gate 2: workspace/colour_palette.json — all 7 colour keys present
        cp_expected = ["primary", "secondary", "accent", "neutral_dark", "neutral_light", "white", "black"]
        for key in cp_expected:
            if key not in colour_palette:
                raise Exception(f"colour_palette missing {key}")

        # Gate 3: workspace/typography.json — heading_font and body_font keys present
        if "heading_font" not in typography or "body_font" not in typography:
            raise Exception("typography missing heading_font or body_font")

        # Gate 4: workspace/assets/ — at least 3 .svg files exist
        assets_dir = os.path.join(workspace, "assets")
        if not os.path.exists(assets_dir):
            raise Exception("assets directory missing")
        svg_files = [f for f in os.listdir(assets_dir) if f.endswith(".svg")]
        if len(svg_files) < 3:
            raise Exception(f"only {len(svg_files)} .svg files found, need at least 3")

        # Gate 5: workspace/assets/cover_art.png OR mood_board.png exists
        if not (os.path.exists(os.path.join(assets_dir, "cover_art.png")) or os.path.exists(os.path.join(assets_dir, "mood_board.png"))):
            raise Exception("neither cover_art.png nor mood_board.png exists")

    except Exception as e:
        err_msg = str(e).replace('\n', ' ')
        append_log(f"guideline_compiler — STATUS: ERROR — gate failed: {err_msg}")
        sys.exit(1)

    try:
        # PART B — LLM 1 call to generate 10-page structure
        merged_data = {
            "brand_brief": brand_brief,
            "colour_palette": colour_palette,
            "typography": typography
        }
        
        user_msg = f"""Output ONLY valid JSON with key 'pages' containing an array of exactly 10 page objects.
Each page: {{"page_number" (1-10), "page_type", "title", "background_colour_key", "sections": []}}.
Each section: {{"type", "content"}}.
Page types in order:
  1=cover, 2=about, 3=logo_primary, 4=logo_variants,
  5=colour_palette, 6=typography, 7=usage_rules,
  8=brand_voice, 9=design_system, 10=closing
Page 1 must include background_image: 'cover_art.png' and a logo_display section.
Page 2 must include a mood_board image section at the top.
Page 7 must include exactly 4 rule_card sections with type='do' and 4 with type='dont'.
Page 5 must include one colour_swatch section per colour slot (7 total).
All content must be real, specific to this brand — no placeholder text.
Section types: heading, subheading, body, colour_swatch, logo_display, font_sample, rule_card, spacing_row, spacer.

Brand Context:
{json.dumps(merged_data, indent=2)}
"""

        response_text = call_llm(ANALYTICAL_PERSONA, user_msg)
        
        start = response_text.find("{")
        end = response_text.rfind("}") + 1
        if start == -1 or end == 0:
            raise Exception("No JSON object found in response")
        response = json.loads(response_text[start:end])

        # PART C — Validate + save
        if "pages" not in response:
            raise Exception("'pages' key missing in response")
        pages = response["pages"]
        if not isinstance(pages, list) or len(pages) != 10:
            raise Exception(f"expected exactly 10 pages, got {len(pages) if isinstance(pages, list) else type(pages)}")
        
        page_numbers = [p.get("page_number") for p in pages]
        if page_numbers != list(range(1, 11)):
            raise Exception(f"page_numbers must be 1 through 10 consecutive, got {page_numbers}")

        out_path = os.path.join(workspace, "guideline_pages.json")
        tmp_path = out_path + ".tmp"
        with open(tmp_path, "w", encoding="utf-8") as f:
            json.dump(response, f, indent=2)
        os.replace(tmp_path, out_path)
        
        append_log("guideline_compiler — STATUS: DONE")
        
    except Exception as e:
        err_msg = str(e).replace('\n', ' ')
        append_log(f"guideline_compiler — STATUS: ERROR — {err_msg}")
        sys.exit(1)

if __name__ == "__main__":
    main()
