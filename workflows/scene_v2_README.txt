scene_v2.json WORKFLOW DOC
================================
Engine: Flux 2 Klein 9B (flux-2-klein-base-9b-fp8)
Purpose: Environment/background generation (mountains, palaces, cities, bamboo forests)
CLIP: gemma_3_12B_it_fp4_mixed
VAE:  flux2-vae.safetensors

Nodes (3):
  Node1 FluxStartSettings  -> UNET/CLIP/VAE/resolution config
  Node2 Fluxstarsampler     -> sampler
  Node3 SaveImage           -> output

Params:
  Resolution: 1344x768 (16:9 landscape)
  Steps: 28, CFG: 3.5, Sampler: euler+simple

Prompt injected at: Node1 FluxStartSettings.text
  No negative prompt (Flux 2 doesnt support)

Prompt template:
  masterpiece, breathtaking scenery, landscape,
  {scene_type}, {time_of_day}, {atmosphere},
  cinematic composition, wide angle,
  ultra detailed background, 8k, HDR,
  no humans, no people, no characters
