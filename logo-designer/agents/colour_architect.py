import sys
import os
import json

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
        out_path = os.path.join(workspace_dir, "colour_palette.json")

        with open(brief_path, "r", encoding="utf-8") as f:
            brand_brief = json.load(f)

        user_message = f"""Given this brand data, output ONLY valid JSON (no markdown)
with exactly these 7 keys: primary, secondary, accent, neutral_dark, neutral_light, white, black.
Each key maps to: {{"name": "...", "hex": "...", "rgb": "...", "cmyk": "...", "use": "..."}}.
Constraints:
  - Colours must match the brand archetype, industry, and colour_direction
  - primary hex must have WCAG AA contrast >= 4.5:1 against #FFFFFF
  - accent hue must differ from primary by >= 30 degrees (HSL)
  - white is always #FFFFFF; black is always #000000
Brand archetype: {brand_brief.get('brand_archetype', '')}
Industry: {brand_brief.get('industry', '')}
Primary emotion: {brand_brief.get('primary_emotion', '')}
Colour direction: {brand_brief.get('colour_direction', '')}"""

        response = call_llm(ANALYTICAL_PERSONA, user_message)
        
        clean_resp = response.strip()
        if clean_resp.startswith("```json"):
            clean_resp = clean_resp[7:]
        elif clean_resp.startswith("```"):
            clean_resp = clean_resp[3:]
        if clean_resp.endswith("```"):
            clean_resp = clean_resp[:-3]
        clean_resp = clean_resp.strip()
        
        palette = json.loads(clean_resp)

        def relative_luminance(hex_str):
            hex_str = hex_str.strip()
            r, g, b = [int(hex_str.lstrip('#')[i:i+2], 16) / 255 for i in (0, 2, 4)]
            channels = [c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4 for c in [r, g, b]]
            return 0.2126 * channels[0] + 0.7152 * channels[1] + 0.0722 * channels[2]

        def contrast_ratio(hex1, hex2):
            l1, l2 = relative_luminance(hex1), relative_luminance(hex2)
            return (max(l1, l2) + 0.05) / (min(l1, l2) + 0.05)

        if contrast_ratio(palette.get('primary', {}).get('hex', '#000000'), '#FFFFFF') < 4.5:
            correction_msg = user_message + f"\n\nNOTE: The previous primary colour ({palette.get('primary', {}).get('hex', '')}) failed WCAG AA. Please darken it significantly."
            response2 = call_llm(ANALYTICAL_PERSONA, correction_msg)
            
            clean_resp2 = response2.strip()
            if clean_resp2.startswith("```json"):
                clean_resp2 = clean_resp2[7:]
            elif clean_resp2.startswith("```"):
                clean_resp2 = clean_resp2[3:]
            if clean_resp2.endswith("```"):
                clean_resp2 = clean_resp2[:-3]
            clean_resp2 = clean_resp2.strip()
            
            palette2 = json.loads(clean_resp2)
            palette['primary'] = palette2['primary']

        required_keys = ["primary", "secondary", "accent", "neutral_dark", "neutral_light", "white", "black"]
        missing = [k for k in required_keys if k not in palette]
        if missing:
            raise ValueError(f"Missing keys in LLM output: {missing}")

        os.makedirs(workspace_dir, exist_ok=True)
        tmp_path = out_path + ".tmp"
        with open(tmp_path, "w", encoding="utf-8") as f:
            json.dump(palette, f, indent=2)
        os.replace(tmp_path, out_path)

        write_log("colour_architect — STATUS: DONE")

    except Exception as e:
        write_log(f"colour_architect — STATUS: ERROR — {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
