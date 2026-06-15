makeup.json WORKFLOW DOC
============================
Engine: SDXL RealVisXL V5.0 (RealVisXL_V5.0_fp16)
Purpose: Face makeup close-up (cosmetic reference/character makeup design)
CLIP: built-in, VAE: built-in
LoRA: ip-adapter-faceid-plusv2_sdxl_lora (strength 0.8)

Nodes (8 + LoRA):
  Node4  CheckpointLoaderSimple -> load RealVisXL
  Node5  CLIPTextEncode         -> positive prompt
  Node6  CLIPTextEncode         -> negative prompt
  Node7  EmptyLatentImage       -> canvas
  Node8  KSampler               -> sampler
  Node9  VAEDecode              -> decode
  Node10 SaveImage              -> output
  Node13 CLIPSetLastLayer       -> CLIP Skip -2
  Node102 LoraLoader (runtime)  -> FaceID LoRA

Params:
  Resolution: 896x1152 (3:4 portrait)
  Steps: 25, CFG: 4.5, Sampler: dpmpp_2m+karras

Positive Prompt template:
  masterpiece, best quality, ultra detailed,
  close-up portrait, face focus, head and shoulders,
  1girl, asian features, delicate skin,
  {makeup_keywords},
  elegant makeup, detailed eye makeup,
  soft studio lighting, beauty photography,
  sharp focus on eyes, professional retouching

Makeup examples:
  - red lipstick, winged eyeliner, light blush, traditional chinese makeup
  - natural makeup, dewy skin, pink lips, light mascara, no-makeup makeup look
  - smokey eyes, bold eyeliner, dark lipstick, contoured cheekbones
