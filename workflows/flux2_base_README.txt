flux2_base.json - Flux 2 Klein 9B 文生图工作流说明
==================================================

来源: 用户提供的 ComfyUI 工作流 JSON
引擎: Flux 2 Klein 9B (flux-2-klein-base-9b-fp8)
用途: 场景 / 道具 / 通用文生图
CLIP: qwen_3_8b_fp8mixed (类型: flux2)
VAE:  full_encoder_small_decoder.safetensors

节点结构 (15 节点):
  75:70 UNETLoader           -> 加载 flux-2-klein-base-9b-fp8
  75:71 CLIPLoader            -> 加载 qwen_3_8b_fp8mixed (flux2)
  75:72 VAELoader             -> 加载 full_encoder_small_decoder
  75:74 CLIPTextEncode (+)    -> 正向 Prompt 注入点
  75:67 CLIPTextEncode (-)    -> 负向 Prompt 注入点
  75:68 PrimitiveInt          -> 宽度 (注射为 value)
  75:69 PrimitiveInt          -> 高度 (注射为 value)
  75:66 EmptyFlux2LatentImage -> 空 Latent
  75:73 RandomNoise           -> 随机噪波 (种子注入 noise_seed)
  75:61 KSamplerSelect        -> 采样器选择 (euler)
  75:62 Flux2Scheduler        -> 调度器 (步数注入 steps)
  75:63 CFGGuider             -> CFG 引导器 (cfg 注入)
  75:64 SamplerCustomAdvanced -> 自定义高级采样器
  75:65 VAEDecode             -> 图像解码
  9     SaveImage             -> 保存输出 (filename_prefix=Flux2-Klein)

与旧版 Flux 工作流的关键区别:
  1. 使用 UNETLoader + CLIPLoader + VAELoader 独立加载
     (旧版用 FluxStartSettings 一体化加载)
  2. 使用 Flux2Scheduler + SamplerCustomAdvanced
     (旧版用 Fluxstarsampler)
  3. 使用 CFGGuider 引导器
     (旧版无 CFG 控制)
  4. 支持负向 Prompt
     (旧版 Flux 不支持负向)
  5. 使用 PrimitiveInt 节点控制宽高
     (旧版在 FluxStartSettings 中设置)

默认参数:
  宽度: 1024
  高度: 1024
  步数: 20
  CFG:  5
  采样器: euler

后端注入映射 (workflow_engine.py):
  75:70.unet_name      <- model_name
  75:74.text           <- positive_prompt
  75:67.text           <- negative_prompt
  75:68.value          <- width
  75:69.value          <- height
  75:62.steps          <- steps
  75:63.cfg            <- cfg
  75:73.noise_seed     <- seed

当前使用此工作流的分类:
  - scene (场景)
  - costume (道具/服装)

推荐 Prompt:
  正向: 中文自然语言描述 (Flux 2 + Qwen CLIP 支持中文)
  负向: low quality, blurry, distorted, ugly, watermark, text
