import sys
import os
import json
import xml.etree.ElementTree as ET

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from shared.nvidia_api import call_llm, ANALYTICAL_PERSONA, VISUAL_PERSONA

def geometric_lettermark_fallback(name: str, hex_colour: str) -> str:
    letter = name[0].upper() if name else "L"
    return f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 400 120" width="400" height="120">
    <circle cx="60" cy="60" r="40" fill="{hex_colour}" />
    <text x="60" y="75" font-family="sans-serif" font-size="48" font-weight="bold" fill="#ffffff" text-anchor="middle">{letter}</text>
    <text x="120" y="75" font-family="sans-serif" font-size="48" font-weight="bold" fill="#1a1a2e">{name}</text>
</svg>"""

def main():
    root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    workspace_dir = os.path.join(root_dir, "workspace")
    log_path = os.path.join(workspace_dir, "agent_log.txt")
    assets_dir = os.path.join(workspace_dir, "assets")
    os.makedirs(assets_dir, exist_ok=True)
    
    try:
        brief_path = os.path.join(workspace_dir, "brand_brief.json")
        with open(brief_path, "r", encoding="utf-8") as f:
            brand_brief = json.load(f)
            
        step_a_prompt = f"""Expand this logo concept into precise SVG construction instructions.
Output ONLY JSON with keys:
  icon_shape_description: exact geometric description (use SVG terms: circle, rect, path, polygon)
  spatial_layout: 'horizontal' or 'stacked'
  icon_to_text_ratio: e.g. 'icon 80px tall, company name 36px tall'
  recommended_primary_hex: from colour_direction field
  recommended_font_style: e.g. 'bold geometric sans-serif'
Logo concept: {brand_brief.get('logo_concept', '')}
Logo style: {brand_brief.get('logo_style', '')}
Colour direction: {brand_brief.get('colour_direction', '')}"""
        
        resp_a = call_llm(ANALYTICAL_PERSONA, step_a_prompt, temperature=0.7)
        resp_a = resp_a.strip()
        if resp_a.startswith("```json"): resp_a = resp_a[7:]
        elif resp_a.startswith("```"): resp_a = resp_a[3:]
        if resp_a.endswith("```"): resp_a = resp_a[:-3]
        concept = json.loads(resp_a.strip())
        
        step_b_prompt = f"""Generate 4 SVG logo variants as JSON with keys:
primary_svg, white_svg, dark_svg, icon_svg.
Each value is a complete valid SVG string.
Rules:
  - primary_svg viewBox '0 0 400 120', icon LEFT of wordmark
  - white_svg: all elements #FFFFFF
  - dark_svg: all elements #1a1a2e (or concept.recommended_primary_hex darkened)
  - icon_svg viewBox '0 0 100 100', icon only, no wordmark
  - Embed Google Font @import inside <style> tag
  - font-weight 700 for company name
  - Include <title> tag with company name
  - All SVG paths closed with Z
  - Icon concept: {concept.get('icon_shape_description', '')}
  - Company: {brand_brief.get('company_name', '')}
  - Tagline: {brand_brief.get('tagline', '')}

Output ONLY valid JSON with the 4 keys. No markdown."""

        def generate_and_validate(prompt: str, is_retry: bool = False):
            resp = call_llm(VISUAL_PERSONA, prompt, temperature=0.5 if not is_retry else 0.2)
            resp = resp.strip()
            if resp.startswith("```json"): resp = resp[7:]
            elif resp.startswith("```"): resp = resp[3:]
            if resp.endswith("```"): resp = resp[:-3]
            
            svg_data = json.loads(resp.strip())
            
            for key in ['primary_svg', 'white_svg', 'dark_svg', 'icon_svg']:
                if key not in svg_data:
                    raise KeyError(f"Missing SVG key: {key}")
                svg_str = svg_data[key].strip()
                if svg_str.startswith("```xml"): svg_str = svg_str[6:]
                elif svg_str.startswith("```svg"): svg_str = svg_str[6:]
                elif svg_str.startswith("```"): svg_str = svg_str[3:]
                if svg_str.endswith("```"): svg_str = svg_str[:-3]
                svg_str = svg_str.strip()
                
                ET.fromstring(svg_str)
                svg_data[key] = svg_str
                
            return svg_data

        try:
            svg_data = generate_and_validate(step_b_prompt, is_retry=False)
        except Exception as e:
            retry_prompt = step_b_prompt + f"\n\nPrevious SVG was invalid XML or JSON parsing failed ({e}). Simplify the icon. Try again."
            try:
                svg_data = generate_and_validate(retry_prompt, is_retry=True)
            except Exception:
                fallback_svg = geometric_lettermark_fallback(brand_brief.get('company_name', 'C'), concept.get('recommended_primary_hex', '#333333'))
                svg_data = {
                    'primary_svg': fallback_svg,
                    'white_svg': fallback_svg.replace(concept.get('recommended_primary_hex', '#333333'), '#FFFFFF').replace('#1a1a2e', '#FFFFFF'),
                    'dark_svg': fallback_svg.replace('#ffffff', '#1a1a2e'),
                    'icon_svg': fallback_svg
                }

        file_mapping = {
            'primary_svg': 'logo_primary.svg',
            'white_svg': 'logo_white.svg',
            'dark_svg': 'logo_dark.svg',
            'icon_svg': 'icon_only.svg'
        }
        
        for key, svg_content in svg_data.items():
            out_path = os.path.join(assets_dir, file_mapping[key])
            with open(out_path, "w", encoding="utf-8") as f:
                f.write(svg_content)
                
        metadata = {
            "spatial_layout": concept.get("spatial_layout", "horizontal"),
            "viewbox_dimensions": {
                "logo": "0 0 400 120",
                "icon": "0 0 100 100"
            },
            "safe_zone_px": 24
        }
        with open(os.path.join(workspace_dir, "logo_metadata.json"), "w", encoding="utf-8") as f:
            json.dump(metadata, f, indent=2)

        with open(log_path, "a", encoding="utf-8") as f:
            f.write("logo_designer — STATUS: DONE\n")
            
    except Exception as e:
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(f"logo_designer — STATUS: ERROR — {e}\n")
        sys.exit(1)

if __name__ == "__main__":
    main()
