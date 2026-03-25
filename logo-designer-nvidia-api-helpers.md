# NVIDIA API Helpers Pattern
This pattern serves as the canonical approach for integrating NVIDIA NIM APIs (LLMs and image generation).

## Base Configuration
```python
NVIDIA_API_KEY = os.environ.get("NVIDIA_API_KEY", "")
LLM_URL = "https://integrate.api.nvidia.com/v1/chat/completions"
IMG_URL = "https://ai.api.nvidia.com/v1/genai/stabilityai/stable-diffusion-3-medium"
MODEL = "meta/llama-3.1-405b-instruct"
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

## LLM Calling Pattern
Implement robust error handling around simple single-turn or multi-turn conversational payloads.
Includes intelligent backoff for rate limiting (429) or server errors (5xx).

```python
def call_llm(system_prompt: str, user_message: str, temperature: float = 0.7, max_tokens: int = 4096, retries: int = 3) -> str:
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
        except requests.exceptions.HTTPError as e:
            code = e.response.status_code
            if code == 429 or code >= 500:
                time.sleep(5 * (attempt + 1))
                continue
            raise
    raise RuntimeError(f"LLM call failed after {retries} retries")
```

## Image Generation Pattern (Stable Diffusion 3)
Returns the generated image or applies a graceful fallback (like a deterministic gradient). Pipeline blocking is prevented even if the image service is degraded.

```python
def generate_image(prompt: str, output_path: str, width: int = 1024, height: int = 1024, steps: int = 30, cfg_scale: float = 7.0, seed: int = 42, retries: int = 3) -> str:
    payload = {
        "prompt": prompt,
        "negative_prompt": "text, letters, words, watermark, blurry, distorted, ugly, logo",
        "width": width,
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
    
    _gradient_fallback("#1a1a2e", "#16213e", width, height, output_path)
    return output_path
```
