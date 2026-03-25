import sys
import os
import json

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from shared.nvidia_api import call_llm, ANALYTICAL_PERSONA

def main():
    root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    workspace_dir = os.path.join(root_dir, "workspace")
    log_path = os.path.join(workspace_dir, "agent_log.txt")
    os.makedirs(workspace_dir, exist_ok=True)
    
    try:
        input_path = os.path.join(root_dir, "user_input.json")
        with open(input_path, "r", encoding="utf-8") as f:
            user_input = json.load(f)
            
        name = user_input.get("company_name", "")
        description = user_input.get("company_description", "")
        
        user_msg = f"""Company: {name}
Description: {description}

Output ONLY valid JSON (no markdown, no preamble) with exactly these 11 keys:
company_name, tagline, brand_archetype, personality_traits (array of 3),
tone_of_voice, industry, primary_emotion, colour_direction, logo_concept,
logo_style, target_audience.
logo_concept must describe a concrete SVG-drawable icon — a specific shape,
not an abstraction. logo_style must be one of: wordmark/lettermark/pictorial/abstract/combination/emblem."""

        resp = call_llm(ANALYTICAL_PERSONA, user_msg, temperature=0.7)
        
        resp = resp.strip()
        if resp.startswith("```json"):
            resp = resp[7:]
        elif resp.startswith("```"):
            resp = resp[3:]
        if resp.endswith("```"):
            resp = resp[:-3]
        resp = resp.strip()
            
        data = json.loads(resp)
        
        required_keys = [
            "company_name", "tagline", "brand_archetype", "personality_traits",
            "tone_of_voice", "industry", "primary_emotion", "colour_direction",
            "logo_concept", "logo_style", "target_audience"
        ]
        
        missing = [k for k in required_keys if k not in data]
        if missing:
            raise ValueError(f"Missing keys in LLM output: {missing}")
            
        out_path = os.path.join(workspace_dir, "brand_brief.json")
        tmp_path = out_path + ".tmp"
        with open(tmp_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
        os.rename(tmp_path, out_path)
        
        with open(log_path, "a", encoding="utf-8") as f:
            f.write("brand_strategist — STATUS: DONE\n")
            
    except Exception as e:
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(f"brand_strategist — STATUS: ERROR — {e}\n")
        sys.exit(1)

if __name__ == "__main__":
    main()
