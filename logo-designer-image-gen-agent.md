# Logo Designer Image Generator Agent Pattern

## Context
When building autonomous design agents that use image generation APIs, handling prompt construction properly and dealing with generation failures without halting the entire pipeline is essential.

## Implementation Details
1. **Separation of Concerns**: 
   - A language model (analytical persona) is used to generate the stable diffusion prompt based on upstream output (like colour palettes and brand definitions).
   - This ensures constraints, such as NOT containing text (because image models struggle with text), are tightly managed.
2. **Deterministic Inputs**: The step requires the exact hex codes of the selected colours, which means it **must run sequentially AFTER** the `colour_architect` agent has finished.
3. **Resiliency via Self-Healing**: 
   - The image generation API (SD3-medium via NVIDIA API) explicitly catches specific 429 backoff paths and generic exceptions.
   - On error, rather than crashing or throwing an error state (which halts the multi-agent orchestration), it uses a pure numpy/Pillow implementation to generate a visually acceptable gradient image using the primary and secondary hex colours.
   - The pipeline is preserved, always writing a `STATUS: DONE` state.
