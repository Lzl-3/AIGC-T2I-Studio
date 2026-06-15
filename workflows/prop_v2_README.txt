prop_v2.json WORKFLOW DOC
===============================
Engine: Flux 2 Klein 9B (flux-2-klein-base-9b-fp8)
Purpose: Prop/costume/weapon product-shot generation
CLIP: gemma_3_12B_it_fp4_mixed
VAE:  flux2-vae.safetensors

Nodes (3):
  Node1 FluxStartSettings  -> UNET/CLIP/VAE/resolution
  Node2 Fluxstarsampler     -> sampler
  Node3 SaveImage           -> output

Params:
  Resolution: 1024x1024 (1:1 square)
  Steps: 30, CFG: 3.5, Sampler: euler+simple

Prompt injected at: Node1 FluxStartSettings.text

Prompt template:
  masterpiece, product photography, commercial shot,
  {item_type}, {material}, {style},
  studio lighting, white background, softbox,
  isolated, centered, no humans, no hands,
  ultra detailed texture, 8k resolution,
  sharp focus on object

Materials: crystal/metal/wood/fabric/jade/paper
Styles: ancient_chinese/modern/fantasy/retro/minimalist
