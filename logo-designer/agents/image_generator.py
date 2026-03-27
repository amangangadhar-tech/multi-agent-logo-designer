import sys
import os
import json

# FIX (Issue 5): portable sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from shared.nvidia_api import call_llm, generate_image, ANALYTICAL_PERSONA

def write_log(msg):
    log_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "workspace", "agent_log.txt")
    with open(log_path, "a", encoding="utf-8") as f:
        f.write(msg + "\n")

def main():
    workspace_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "workspace")
    assets_dir = os.path.join(workspace_dir, "assets")
    
    try:
        brief_path = os.path.join(workspace_dir, "brand_brief.json")
        palette_path = os.path.join(workspace_dir, "colour_palette.json")
        
        os.makedirs(assets_dir, exist_ok=True)

        with open(brief_path, "r", encoding="utf-8") as f:
            brand_brief = json.load(f)
            
        with open(palette_path, "r", encoding="utf-8") as f:
            colour_palette = json.load(f)

        # STEP A — Write SD3 prompts (LLM 1)
        user_message = f"""Write two Stable Diffusion image generation prompts as JSON
with keys: cover_prompt and moodboard_prompt.
Each prompt: 40-80 words, highly descriptive, photographic or illustrative.
CRITICAL: Do NOT include any company name, text, letters, or words in the prompts.
Stable Diffusion cannot render text reliably — describe only visual elements.
Focus on: abstract shapes, lighting, texture, mood, colours, materials.
Brand: {brand_brief.get('company_name', '')}
Industry: {brand_brief.get('industry', '')}
Archetype: {brand_brief.get('brand_archetype', '')}
Primary emotion: {brand_brief.get('primary_emotion', '')}
Colour direction: {brand_brief.get('colour_direction', '')}
Primary colour hex: {colour_palette.get('primary', dict()).get('hex', '')}
Secondary colour hex: {colour_palette.get('secondary', dict()).get('hex', '')}"""

        response = call_llm(ANALYTICAL_PERSONA, user_message)
        
        clean_resp = response.strip()
        if clean_resp.startswith("```json"):
            clean_resp = clean_resp[7:]
        elif clean_resp.startswith("```"):
            clean_resp = clean_resp[3:]
        if clean_resp.endswith("```"):
            clean_resp = clean_resp[:-3]
        clean_resp = clean_resp.strip()
        
        prompts = json.loads(clean_resp)
        
    except Exception as e:
        write_log(f"image_generator — STATUS: ERROR — {e}")
        sys.exit(1)

    # STEP B — Generate images (SD3-medium)
    # generate_image() never raises — it self-heals it to gradient fallback.
    cover_path = os.path.join(assets_dir, "cover_art.png")
    generate_image(
        prompts.get('cover_prompt', ''),
        cover_path,
        width=1024, height=1024, steps=35, cfg_scale=7.5, seed=42
    )
    
    mood_path = os.path.join(assets_dir, "mood_board.png")
    generate_image(
        prompts.get('moodboard_prompt', ''),
        mood_path,
        width=1024, height=512, steps=30, cfg_scale=7.0, seed=99
    )
    
    write_log("image_generator — STATUS: DONE")

if __name__ == "__main__":
    main()
