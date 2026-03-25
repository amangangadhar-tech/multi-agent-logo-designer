# Two-Step SVG Generation Pattern

When generating functional SVGs (code rather than raster images), the most reliable method uses a two-step LLM approach with persona bridging.

## The Strategy

Instead of asking an LLM to "design and draw an SVG logo" from a vague description in one go, break it down:

1. **Analytical Persona (LLM 1)**: Elaborates the concept into concrete geometry, layout metrics, and exact path definitions. Output is JSON instructions.
2. **Visual Persona (LLM 2)**: Translates the spatial/geometric instructions into clean SVG markup. Output is JSON mapping filenames to raw SVG markup.

## Step A (Analytical)

**System Prompt (Analytical):**
> You are a senior brand strategist and design consultant with 20 years of experience...

**User Prompt:**
```text
Expand this logo concept into precise SVG construction instructions.
Output ONLY JSON with keys:
  icon_shape_description: exact geometric description (use SVG terms: circle, rect, path, polygon)
  spatial_layout: 'horizontal' or 'stacked'
  ...
```

## Step B (Visual)

**System Prompt (Visual):**
> You are an expert SVG logo designer and vector artist. You think in shapes, paths, and coordinates. You have deep mastery of SVG viewBox, path commands (M L C A Z), and text layout...

**User Prompt:**
```text
Generate 4 SVG logo variants as JSON with keys: primary_svg, white_svg, dark_svg, icon_svg.
Each value is a complete valid SVG string.
Rules:
  - primary_svg viewBox '0 0 400 120', etc...
```

## Validation & Fallback

Always include an XML parser validation step (`xml.etree.ElementTree.fromstring(svg_string)`) and provide a single LLM retry if parsing fails. If the retry also fails, fall back to a programmatic deterministic geometric lettermark layout to guarantee pipeline execution never blocks.
