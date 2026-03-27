# Multi-Agent Logo Designer

A fully autonomous brand identity pipeline powered entirely by NVIDIA's free NIM APIs. It uses seven specialized agents to collaborate and produce a complete, print-ready 10-page brand guideline PDF—including logo designs, color systems, and typography—based on a simple company description input.

## Requirements
- **NVIDIA NIM free account**: Get an API key from [build.nvidia.com](https://build.nvidia.com)
- **Docker**: For running the containerized pipeline

## Quick Start

Run the following 3 commands to generate your brand guidelines:

```bash
cp .env.example .env && echo "NVIDIA_API_KEY=nvapi-..." >> .env
echo '{"company_name":"YourBrand","company_description":"..."}' > user_input.json
docker-compose up
```

Then: open `workspace/brand_guidelines.pdf`

## Maximizing Output Quality

To get the most efficient and high-quality results from the AI agents, follow these guidelines when providing inputs:

- **Be Descriptive**: Instead of just "a coffee shop," try "a specialty coffee subscription service delivering single-origin beans with a minimalist 1950s Italian aesthetic."
- **Define Your Audience**: Mention who your customers are (e.g., "young urban professionals aged 25-40") to help the `brand_strategist` tune the tone.
- **Mention Personalities**: Use 3-5 traits like "Bold, Trustworthy, Playful, or Elegant" in your description.
- **Style Preferences**: If you have a specific logo style in mind (Wordmark, Lettermark, Pictorial, etc.), mention it directly.

> [!TIP]
> The more detail you provide in the `company_description`, the better the AI agents can harmonize. Richer descriptions lead to more cohesive logos and branding guidelines.

---

## Agent Pipeline Diagram

```text
┌─────────────────────────────────────────────────────┐
│              USER INPUT                             │
│  company_name + company_description                 │
│  → user_input.json                                  │
└───────────────────┬─────────────────────────────────┘
                    │
                    ▼
┌─────────────────────────────────────────────────────┐
│     AGENT 1 — brand_strategist                      │
│     API: LLM 1 (analytical persona)                 │
│     In:  user_input.json                            │
│     Out: workspace/brand_brief.json                 │
│     → company name, tagline, archetype, logo        │
│       concept, colour direction, target audience    │
└───────────────────┬─────────────────────────────────┘
                    │
                    ▼
┌─────────────────────────────────────────────────────┐
│     AGENT 2 — logo_designer                         │
│     API: LLM 1 (concept elaboration)                │
│          LLM 2 (SVG visual persona)                 │
│     In:  brand_brief.json                           │
│     Out: logo_primary.svg, logo_white.svg,          │
│          logo_dark.svg, icon_only.svg,              │
│          logo_metadata.json                         │
└───────────────────┬─────────────────────────────────┘
                    │
                    ▼
┌─────────────────────────────────────────────────────┐
│     AGENT 3 — colour_architect       [SEQUENTIAL]   │
│     API: LLM 1                                      │
│     In:  brand_brief.json                           │
│     Out: colour_palette.json                        │
│     ↑ Must complete before image_generator starts   │
│       (image_generator reads primary colour hex)    │
└──────────┬────────────────────────────────┬─────────┘
           │                               │
           ▼                               ▼
┌──────────────────────┐      ┌────────────────────────┐
│  AGENT 4             │      │  AGENT 5               │
│  typography_director │      │  image_generator        │
│                      │      │                        │
│  LLM 1               │      │  Step 1: LLM 1         │
│                      │      │  writes SD3 prompts    │
│  Out:                │      │  Step 2: SD3-medium    │
│  typography.json     │      │  generates images      │
│                      │      │                        │
│  [PARALLEL with      │      │  Out:                  │
│   image_generator]   │      │  cover_art.png         │
│                      │      │  mood_board.png        │
│                      │      │  [PARALLEL with        │
│                      │      │   typography_director] │
└──────────┬───────────┘      └────────────┬───────────┘
           │                               │
           └───────────────┬───────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────┐
│     AGENT 6 — guideline_compiler                    │
│     API: LLM 1 (analytical persona)                 │
│     In:  brand_brief + palette + typography +       │
│          logo_metadata + asset file list            │
│     Quality gates: 5 checks before LLM call        │
│     Out: workspace/guideline_pages.json             │
│          (10-page structured content JSON)          │
└───────────────────┬─────────────────────────────────┘
                    │
                    ▼
┌─────────────────────────────────────────────────────┐
│     AGENT 7 — pdf_renderer                          │
│     API: NONE — pure Python                         │
│     In:  guideline_pages.json + all assets          │
│     Tools: ReportLab + cairosvg + Pillow            │
│     Out: workspace/brand_guidelines.pdf  ✅         │
└─────────────────────────────────────────────────────┘
```

## Output Files

| File Path | Description |
|-----------|-------------|
| `workspace/brand_brief.json` | Strategic brand brief including concepts and audience |
| `workspace/logo_metadata.json` | Metadata related to the logo concept and dimensions |
| `workspace/assets/logo_*.svg` | Rendered logo SVGs for all variants (primary, white, dark, icon) |
| `workspace/assets/*.png` | Converted PNG image assets, plus SD3 cover art and mood board |
| `workspace/colour_palette.json` | The structured 7-color palette definition |
| `workspace/typography.json` | Defined Google Fonts families, scales, and line heights |
| `workspace/guideline_pages.json` | Master layout plan structuring the 10-page content |
| `workspace/brand_guidelines.pdf` | The generated 10-page brand guidelines document |
| `workspace/agent_log.txt` | Multi-agent execution log with success/error statuses |

## Free Tier API Limits Note

The NVIDIA NIM platform offers a free tier covering endpoints used in this project like `meta/llama-3.1-405b-instruct` and `stabilityai/stable-diffusion-3-medium`. Please be mindful of usage rates, as rate ceilings and monthly token limits apply for free accounts.

## Troubleshooting

If any step fails, check `workspace/agent_log.txt` first. This file contains the sequential statuses and any error messages from the individual agents.

## Usage & Contribution Guidelines

1. **Configuration**: Ensure you have copied `.env.example` to `.env` and populated it using a valid NVIDIA API key.
2. **Prompts**: Keep your `company_description` concise but descriptive. Include stylistic preferences (e.g., minimalist, playful, professional) to guide the LLM effectively and yield better logo concepts.
3. **Execution**: The agents run sequentially, then concurrently where possible. Do not interrupt the Docker container while generation is in progress. Wait for the `brand_guidelines.pdf` generation message.
4. **Outputs**: All finalized assets will be stored in `workspace/`. You may safely empty `workspace/assets/` to clear previous image runs before executing again.
5. **Contributing**:
   - Please create a new branch containing your feature (`git checkout -b feature/your-feature-name`).
   - Ensure the scripts inside `agents/` adhere to the existing prompt strategies.
   - Open a Pull Request referencing any open issues.

## License

This project is licensed under the [MIT License](../LICENSE).
