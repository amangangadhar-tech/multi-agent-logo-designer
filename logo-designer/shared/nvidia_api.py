import os
import time
import requests
import base64
from io import BytesIO
from PIL import Image
import numpy as np

NVIDIA_API_KEY = os.environ.get("NVIDIA_API_KEY", "")
POLLINATIONS_API_KEY = os.environ.get("POLLINATIONS_API_KEY", "")
LLM_URL = "https://integrate.api.nvidia.com/v1/chat/completions"
POLLINATIONS_IMG_URL = "https://gen.pollinations.ai/v1/images/generations"
MODEL = "meta/llama-3.1-405b-instruct"
HEADERS_LLM = {
    "Authorization": f"Bearer {NVIDIA_API_KEY}",
    "Content-Type": "application/json"
}

ANALYTICAL_PERSONA = """You are a senior brand strategist and design consultant with 20 years of experience
at top branding agencies. You think systematically, output precise JSON only, and
never add markdown formatting, code fences, or preamble. Your outputs are
deterministic and structured."""

VISUAL_PERSONA = """You are an expert SVG logo designer and vector artist. You think in shapes, paths,
and coordinates. You have deep mastery of SVG viewBox, path commands (M L C A Z),
and text layout. You output clean, valid SVG markup that is visually distinctive
and brand-appropriate. You never add markdown, code fences, or explanations —
only the requested SVG or JSON output."""

def call_llm(system_prompt: str, user_message: str, temperature: float = 0.7, max_tokens: int = 4096, retries: int = 5) -> str:
    payload = {
        "model": MODEL,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message}
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
        except (requests.exceptions.HTTPError, requests.exceptions.Timeout, requests.exceptions.ConnectionError) as e:
            if getattr(e, "response", None) is not None:
                code = e.response.status_code
                if code != 429 and code < 500:
                    raise
            time.sleep(10 * (attempt + 1))
            continue
    raise RuntimeError(f"LLM call failed after {retries} retries")

def generate_image(prompt: str, output_path: str,
                   width: int = 1024, height: int = 1024,
                   seed: int = 42, retries: int = 3) -> str:
    payload = {
        "prompt": prompt,
        "model": "flux",
        "size": f"{width}x{height}",
        "response_format": "b64_json",
        "seed": seed
    }
    headers = {
        "Authorization": f"Bearer {POLLINATIONS_API_KEY}",
        "Content-Type": "application/json"
    }
    for attempt in range(retries):
        try:
            resp = requests.post(POLLINATIONS_IMG_URL, headers=headers,
                                 json=payload, timeout=120)
            resp.raise_for_status()
            img_b64 = resp.json()["data"][0]["b64_json"]
            img = Image.open(BytesIO(base64.b64decode(img_b64)))
            img.save(output_path, "PNG")
            return output_path
        except requests.exceptions.HTTPError as e:
            if getattr(e, "response", None) is not None:
                if e.response.status_code == 429:
                    time.sleep(15 * (attempt + 1))
                    continue
            break
        except Exception:
            break
    
    _gradient_fallback("#1a1a2e", "#16213e", width, height, output_path)
    return output_path

def _gradient_fallback(hex1: str, hex2: str, w: int, h: int, path: str):
    def to_rgb(h): return tuple(int(h.lstrip('#')[i:i+2], 16) for i in (0,2,4))
    r1, g1, b1 = to_rgb(hex1)
    r2, g2, b2 = to_rgb(hex2)
    arr = np.zeros((h, w, 3), dtype=np.uint8)
    for x in range(w):
        t = x / w
        arr[:, x] = [int(r1*(1-t)+r2*t), int(g1*(1-t)+g2*t), int(b1*(1-t)+b2*t)]
    Image.fromarray(arr).save(path)
