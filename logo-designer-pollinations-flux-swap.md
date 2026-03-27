# Pattern: Logo Designer Pollinations Flux Swap

## Context
The image generation backend for the Multi-Agent Logo Designer has been migrated from NVIDIA's `stable-diffusion-3-medium` to the Pollinations AI `flux` model. The `flux` model offers faster generation times (~5-10s vs ~30s), superior visual quality, and a simpler API (no `steps` or `guidance_scale` needed).

## Changes Made
1. **API Keys & Endpoints**
   - Added `POLLINATIONS_API_KEY` to `.env` and `docker-compose.yml`
   - Added `POLLINATIONS_IMG_URL` (https://gen.pollinations.ai/v1/images/generations)

2. **Image Generator Method (`shared/nvidia_api.py`)**
   - Removed SD3 specific kwargs (`steps`, `cfg_scale`).
   - Implemented standard Pollinations AI payload using the Open-AI compatible `b64_json` output format.
```python
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
```

3. **Agent Integration (`agents/image_generator.py`)**
   - Updated call signatures to omit `steps` and `cfg_scale`.

## Verification
Generating stunning 1024x1024 PNG images properly requires passing the `b64_json` response format to decode natively as `BytesIO`.
