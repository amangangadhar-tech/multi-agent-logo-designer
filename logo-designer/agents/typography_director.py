import sys
import os
import json
import requests

# FIX (Issue 5): portable sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from shared.nvidia_api import call_llm, ANALYTICAL_PERSONA

def write_log(msg):
    log_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "workspace", "agent_log.txt")
    with open(log_path, "a", encoding="utf-8") as f:
        f.write(msg + "\n")

def main():
    try:
        workspace_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "workspace")
        brief_path = os.path.join(workspace_dir, "brand_brief.json")
        out_path = os.path.join(workspace_dir, "typography.json")

        with open(brief_path, "r", encoding="utf-8") as f:
            brand_brief = json.load(f)

        user_message = f"""Output ONLY valid JSON (no markdown) with these keys:
heading_font, body_font, accent_font, scale, line_height, letter_spacing.
Rules:
  - heading_font and body_font must be DIFFERENT Google Fonts
  - body_font MUST be one of: Inter, DM Sans, Source Sans 3, Nunito Sans, Lato
  - Each font object: {{"family": "...", "weights": [400, 500], "google_import_url": "...", "character": "..."}}
  - scale: {{"h1_px": 48, "h2_px": 36, "h3_px": 28, "h4_px": 22, "body_px": 16, "caption_px": 12}}
  - line_height: {{"headings": 1.2, "body": 1.6}}
  - letter_spacing: {{"headings_em": -0.02, "body_em": 0, "caps_em": 0.08}}
Brand archetype: {brand_brief.get('brand_archetype', '')}
Tone: {brand_brief.get('tone_of_voice', '')}
Industry: {brand_brief.get('industry', '')}"""

        response = call_llm(ANALYTICAL_PERSONA, user_message)
        
        clean_resp = response.strip()
        if clean_resp.startswith("```json"):
            clean_resp = clean_resp[7:]
        elif clean_resp.startswith("```"):
            clean_resp = clean_resp[3:]
        if clean_resp.endswith("```"):
            clean_resp = clean_resp[:-3]
        clean_resp = clean_resp.strip()
            
        typography = json.loads(clean_resp)

        for font_key, default_family, default_url in [
            ("heading_font", "Poppins", "https://fonts.googleapis.com/css2?family=Poppins:wght@600;700;800"),
            ("body_font", "Inter", "https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600")
        ]:
            font_obj = typography.get(font_key, {})
            url = font_obj.get("google_import_url", "")
            valid = False
            if url:
                try:
                    resp = requests.head(url, timeout=10)
                    if resp.status_code < 400:
                        valid = True
                except requests.RequestException:
                    pass
            
            if not valid:
                font_obj["family"] = default_family
                font_obj["google_import_url"] = default_url
                typography[font_key] = font_obj

        os.makedirs(workspace_dir, exist_ok=True)
        tmp_path = out_path + ".tmp"
        with open(tmp_path, "w", encoding="utf-8") as f:
            json.dump(typography, f, indent=2)
        os.replace(tmp_path, out_path)

        write_log("typography_director — STATUS: DONE")

    except Exception as e:
        write_log(f"typography_director — STATUS: ERROR — {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
