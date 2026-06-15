# -*- coding: utf-8 -*-
"""服道化素材工作室 - 预设数据

服装/道具/妆容三类训练预设 + 随机池 + 底模配置
"""

from src.fudaohua_custom import list_custom_presets, get_custom_preset

COSTUME_PRESETS = {'01_white_swordsman': {'id': '01_white_swordsman', 'name_cn': '白衣剑修', 'core_tags': 'white xianxia robe, silver embroidery, jade belt, wide flowing sleeves, layered silk skirt, luxury fabric texture, high detail traditional chinese clothing', 'training_tags': ['white_xianxia_robe', 'silver_embroidery', 'jade_belt', 'wide_sleeves', 'flowing_skirt', 'luxury_fabric']}, '02_sect_sister': {'id': '02_sect_sister', 'name_cn': '宗门大师姐', 'core_tags': 'cyan hanfu, gold trim, cloud pattern embroidery, flowing layered skirt, silk sash, elegant wide sleeves, luxury fabric texture, high detail traditional chinese clothing', 'training_tags': ['cyan_hanfu', 'gold_trim', 'cloud_pattern_embroidery', 'layered_skirt', 'silk_sash', 'wide_sleeves']}, '03_demon_saint': {'id': '03_demon_saint', 'name_cn': '魔教圣女', 'core_tags': 'black silk dress, red sash, silver chain ornaments, dark flowing veil, gothic elegance, fitted bodice, high detail dark fantasy clothing', 'training_tags': ['black_dress', 'red_sash', 'silver_chains', 'dark_veil', 'flowing_black_silk', 'gothic_elegance']}, '04_empress_robe': {'id': '04_empress_robe', 'name_cn': '女帝朝服', 'core_tags': 'golden imperial robe, dragon embroidery, phoenix crown, red silk lining, ornate gold trim, majestic court dress, high detail imperial chinese clothing', 'training_tags': ['golden_imperial_robe', 'dragon_embroidery', 'phoenix_crown', 'ornate_gold_trim', 'court_dress', 'imperial_style']}, '05_dunhuang_flying': {'id': '05_dunhuang_flying', 'name_cn': '敦煌飞天', 'core_tags': 'multicolor ribbon dress, flying silk sash, gold jewelry, flowing rainbow silk, layered thin translucent fabrics, celestial dancer costume, dunhuang mural style clothing', 'training_tags': ['multicolor_ribbon_dress', 'flying_sash', 'gold_jewelry', 'rainbow_silk', 'thin_layered_fabrics', 'celestial_costume']}, '06_green_scholar': {'id': '06_green_scholar', 'name_cn': '青衣书生', 'core_tags': 'green scholar robe, bamboo pattern embroidery, simple clean cut, flowing scholarly sleeves, elegant literati attire, high detail traditional chinese scholar clothing', 'training_tags': ['green_scholar_robe', 'bamboo_pattern', 'simple_cut', 'flowing_sleeves', 'literati_attire', 'scholarly_style']}, '07_battle_warrior': {'id': '07_battle_warrior', 'name_cn': '战损侠客', 'core_tags': 'torn warrior robe, leather armor shoulder pieces, bandages wrapped around torso, battle-damaged fabric edges, weathered martial attire, high detail worn clothing', 'training_tags': ['torn_warrior_robe', 'leather_armor', 'battle_damaged', 'bandages', 'weathered_fabric', 'martial_attire']}, '08_red_wedding': {'id': '08_red_wedding', 'name_cn': '红嫁衣', 'core_tags': 'red wedding dress, gold phoenix embroidery, flowing red veil, silk brocade fabric, intricate gold thread patterns, traditional chinese bridal costume, high detail', 'training_tags': ['red_wedding_dress', 'gold_phoenix_embroidery', 'red_veil', 'silk_brocade', 'gold_patterns', 'bridal_costume']}}

PROP_PRESETS = {'01_jade_flute': {'id': '01_jade_flute', 'name_cn': '玉箫', 'core_tags': 'jade flute, green jade material, carved chinese patterns, tassel hanging, smooth polished surface, traditional chinese musical instrument, detailed prop', 'training_tags': ['jade_flute', 'green_jade', 'carved_patterns', 'tassel', 'chinese_instrument', 'polished_jade']}, '02_wine_gourd': {'id': '02_wine_gourd', 'name_cn': '酒葫芦', 'core_tags': 'wine gourd, brown calabash, red rope tied around waist, smooth wooden surface, traditional chinese wine container, rustic prop, detailed', 'training_tags': ['wine_gourd', 'calabash', 'red_rope', 'wooden_surface', 'rustic_prop', 'chinese_container']}, '03_fly_whisk': {'id': '03_fly_whisk', 'name_cn': '拂尘', 'core_tags': 'fly whisk, white horsehair bristles, wooden handle with carvings, taoist ritual tool, flowing soft bristles, detailed prop, traditional chinese', 'training_tags': ['fly_whisk', 'white_bristles', 'wooden_handle', 'taoist_tool', 'flowing_bristles', 'ritual_prop']}, '04_flying_sword': {'id': '04_flying_sword', 'name_cn': '飞剑', 'core_tags': 'flying sword, silver blade with glowing blue runes, ornate golden hilt, floating in air, sharp edge, xianxia magic weapon, detailed prop', 'training_tags': ['flying_sword', 'silver_blade', 'glowing_runes', 'golden_hilt', 'floating', 'magic_weapon']}, '05_folding_fan': {'id': '05_folding_fan', 'name_cn': '折扇', 'core_tags': 'folding fan, white paper with ink landscape painting, bamboo ribs, open fan, elegant chinese accessory, detailed prop', 'training_tags': ['folding_fan', 'ink_painting', 'bamboo_ribs', 'open_fan', 'chinese_accessory', 'elegant_prop']}, '06_ancient_book': {'id': '06_ancient_book', 'name_cn': '古籍', 'core_tags': 'ancient chinese book, blue fabric cover, string-bound binding, yellowed paper pages, vertical chinese text, scholarly prop, detailed', 'training_tags': ['ancient_book', 'blue_cover', 'string_bound', 'yellowed_pages', 'chinese_text', 'scholarly_prop']}, '07_jade_pendant': {'id': '07_jade_pendant', 'name_cn': '玉佩', 'core_tags': 'jade pendant, round bi disc shape, dragon carving, red silk cord, polished green jade, traditional chinese jewelry, detailed prop', 'training_tags': ['jade_pendant', 'bi_disc', 'dragon_carving', 'red_cord', 'green_jade', 'chinese_jewelry']}, '08_ink_brush': {'id': '08_ink_brush', 'name_cn': '毛笔', 'core_tags': 'calligraphy brush, dark wood handle, white goat hair tip, ink stained tip, traditional chinese writing tool, detailed prop', 'training_tags': ['calligraphy_brush', 'wood_handle', 'goat_hair_tip', 'ink_stained', 'writing_tool', 'chinese_brush']}, '09_lotus_lantern': {'id': '09_lotus_lantern', 'name_cn': '莲花灯', 'core_tags': 'lotus lantern, pink lotus petals, golden base, glowing warm light inside, paper lantern, traditional chinese festival prop, detailed', 'training_tags': ['lotus_lantern', 'pink_petals', 'golden_base', 'glowing_light', 'paper_lantern', 'festival_prop']}, '10_ancient_mirror': {'id': '10_ancient_mirror', 'name_cn': '古铜镜', 'core_tags': 'ancient bronze mirror, round shape, polished reflective surface, cloud pattern carving on back, green patina edges, traditional chinese artifact, detailed prop', 'training_tags': ['bronze_mirror', 'round_shape', 'cloud_pattern', 'green_patina', 'reflective_surface', 'chinese_artifact']}}

MAKEUP_PRESETS = {'01_phoenix_huadian': {'id': '01_phoenix_huadian', 'name_cn': '凤尾花钿妆', 'core_tags': 'phoenix tail huadian forehead mark, red gem between eyebrows, elegant thin eyebrows, red lips, pale porcelain skin, traditional chinese palace makeup, detailed face', 'training_tags': ['phoenix_huadian', 'red_forehead_gem', 'thin_eyebrows', 'red_lips', 'porcelain_skin', 'palace_makeup']}, '02_cat_eye_smokey': {'id': '02_cat_eye_smokey', 'name_cn': '猫眼烟熏妆', 'core_tags': 'cat eye eyeliner, winged liner, smokey dark eyeshadow, defined cheekbones contour, nude matte lips, dramatic eye makeup, bold look', 'training_tags': ['cat_eye_liner', 'smokey_eyeshadow', 'winged_liner', 'contoured_cheekbones', 'nude_lips', 'dramatic_makeup']}, '03_peach_blossom': {'id': '03_peach_blossom', 'name_cn': '桃花妆', 'core_tags': 'pink eyeshadow around eyes, peach blossom petal decoration on temple, rosy blush on cheeks, glossy pink lips, dewy skin, fresh youthful chinese makeup, detailed face', 'training_tags': ['pink_eyeshadow', 'peach_blossom_decoration', 'rosy_blush', 'glossy_pink_lips', 'dewy_skin', 'youthful_makeup']}, '04_golden_phoenix': {'id': '04_golden_phoenix', 'name_cn': '金凤朝阳妆', 'core_tags': 'golden eyeshadow with shimmer, gold foil flakes on cheekbones, sharp winged eyebrows, deep red lips, luminous skin, luxurious imperial makeup, detailed face', 'training_tags': ['golden_eyeshadow', 'gold_foil_flakes', 'sharp_eyebrows', 'deep_red_lips', 'luminous_skin', 'imperial_makeup']}, '05_jade_pure': {'id': '05_jade_pure', 'name_cn': '玉净素颜妆', 'core_tags': 'barely there makeup, natural skin texture visible, clear dewy complexion, light pink tint on lips, groomed natural brows, fresh faced clean look, minimal makeup', 'training_tags': ['bare_makeup', 'natural_skin', 'dewy_complexion', 'light_pink_lips', 'natural_brows', 'clean_look']}, '06_demon_crimson': {'id': '06_demon_crimson', 'name_cn': '魔纹血妆', 'core_tags': 'crimson red eye shadow extending to temples, dark red lipstick with gradient, sharp angular eyebrows, pale white foundation, blood-red tear streak mark, demonic elegant makeup, detailed face', 'training_tags': ['crimson_eyeshadow', 'dark_red_lips', 'angular_eyebrows', 'pale_foundation', 'blood_tear_mark', 'demonic_makeup']}, '07_lotus_pure': {'id': '07_lotus_pure', 'name_cn': '莲花清透妆', 'core_tags': 'lotus petal shaped pink eyeshadow, translucent glowing skin, soft pink gradient lips, natural straight eyebrows, pearl highlight on cheekbones, pure elegant chinese makeup, detailed face', 'training_tags': ['lotus_eyeshadow', 'translucent_skin', 'gradient_lips', 'straight_eyebrows', 'pearl_highlight', 'pure_makeup']}, '08_war_paint': {'id': '08_war_paint', 'name_cn': '战纹妆', 'core_tags': 'tribal war paint stripes on cheeks, dark charcoal lines, fierce expression lines, neutral lips, bold intimidating makeup, warrior face paint, detailed', 'training_tags': ['war_paint_stripes', 'charcoal_lines', 'fierce_makeup', 'neutral_lips', 'tribal_marks', 'warrior_paint']}}

CHARACTER_POOL = ['young asian woman, natural face, unique facial features, smooth skin', 'mature asian woman, elegant face, refined bone structure, different nose shape', 'young asian man, natural masculine face, sharp jawline, unique features', 'mature asian man, weathered handsome face, broad facial structure', 'young mixed-race woman, soft features, natural beauty, distinct face shape', 'young mixed-race man, sharp features, defined cheekbones, natural look', 'middle-aged asian woman, graceful features, mature beauty', 'middle-aged asian man, dignified face, distinguished appearance', 'teenage asian girl, youthful face, innocent features, round face', 'teenage asian boy, youthful face, fresh appearance, angular features']

HAIRSTYLE_POOL = ['long straight black hair, flowing naturally', 'shoulder-length black hair, soft waves, natural texture', 'long black hair tied in high ponytail, sleek', 'traditional chinese bun with hairpin, elegant updo', 'short neat black hair, clean cut', 'medium-length hair, half-up half-down style', 'long hair in low braid, practical style', 'short bob cut, modern clean look', 'long hair loose with side braid, romantic style', 'top knot bun, martial arts style']

MAKEUP_POOL = ['natural makeup, no visible cosmetics, bare face', 'light makeup, subtle pink lips, barely visible eye shadow', 'elegant makeup, defined eyebrows, soft red lips', 'bold makeup, dark eyeliner, red lips, dramatic look', 'smokey eye makeup, dark eyeshadow, nude lips', 'fresh dewy makeup, glossy lips, minimal eye makeup', 'traditional chinese makeup, red lips, delicate brows', 'no makeup at all, completely bare face, natural skin']

PROP_POOL = ['holding a long sword, blade visible', 'holding a folding fan, open', 'holding an ancient book, reading pose', 'holding a jade cup, drinking gesture', 'holding a calligraphy brush', 'holding a silk umbrella', 'holding a jade pendant, examining', 'holding nothing, empty hands, natural hand position', 'holding nothing, hands behind back', 'holding nothing, arms crossed']

BACKGROUND_POOL = ['pure white background, seamless studio, clean blank backdrop', 'pure white background, seamless studio, clean blank backdrop', 'pure white background, seamless studio, clean blank backdrop', 'pure white background, seamless studio, clean blank backdrop', 'pure white background, seamless studio, clean blank backdrop', 'pure white background, seamless studio, clean blank backdrop', 'neutral gray background, seamless studio, minimal backdrop', 'neutral gray background, seamless studio, minimal backdrop', 'pure black background, dark void, seamless black studio', 'simple studio with soft lighting, clean minimal backdrop']

ANGLE_POOL = ['front view, facing camera, full frontal', 'side view, profile, looking to the side', 'back view, from behind, turned away from camera', 'three-quarter view, slightly turned, 45 degree angle', 'full body shot, head to toe, complete figure visible', 'half body shot, waist up, upper body portrait']

ACTION_POOL = ['standing pose, upright posture, natural stance, relaxed arms', 'walking pose, mid-stride, flowing movement, dynamic walk', 'sitting pose, seated position, relaxed posture, hands on lap', 'turning pose, looking back over shoulder, dynamic twist', 'standing with one hand raised, pointing gesture', 'leaning against wall, casual pose, relaxed', 'walking forward, confident stride, looking ahead', 'sitting on ground, one knee up, casual resting pose']

LIGHTING_POOL = ['studio lighting, soft diffused light, clean shadows, even illumination', 'soft natural lighting, gentle illumination, even exposure', 'high key lighting, bright and airy, soft shadows', 'neutral studio lighting, balanced exposure, minimal shadows']

QUALITY_TAG = 'masterpiece, best quality, ultra detailed, 8k, sharp focus, professional photography, high resolution fabric texture'

NEGATIVE_PROMPT = 'worst quality, low quality, lowres, blurry, bad anatomy, extra fingers, missing fingers, fused fingers, too many fingers, watermark, text, logo, signature, username, distorted face, ugly face, deformed face, bad face, nsfw, nude, naked, cropped, out of frame, specific person, celebrity, famous face, same face, dark atmosphere, battle damage, blood, magic glow, complex background, messy composition'

BASE_MODELS = [{'key': 'flux2_klein', 'name': 'Flux 2 Klein 9B', 'type': 'flux', 'width': 1024, 'height': 1024, 'checkpoint': 'flux-2-klein-base-9b-fp8.safetensors'}, {'key': 'realvisxl_v50', 'name': 'RealVisXL V5.0', 'type': 'sdxl', 'width': 1024, 'height': 1024, 'checkpoint': 'RealVisXL_V5.0_fp16.safetensors'}, {'key': 'juggernaut_xl', 'name': 'Juggernaut XL', 'type': 'sdxl', 'width': 1024, 'height': 1024, 'checkpoint': 'juggernautXL_juggernautX.safetensors'}, {'key': 'z_image', 'name': 'Z-Image', 'type': 'zimage', 'width': 1920, 'height': 1088, 'checkpoint': 'z_image_turbo_bf16.safetensors'}, {'key': 'dreamshaper_xl', 'name': 'DreamShaper XL', 'type': 'sdxl', 'width': 1024, 'height': 1024, 'checkpoint': 'dreamshaperXL_alpha2Xl10.safetensors'}]

COSTUME_TEMPLATE = "{core_tags} on {character}, {hairstyle}, {makeup}, {action}, {prop}, {background}, {angle}, {lighting}, {quality}"

PROP_TEMPLATE = "{character}, {hairstyle}, holding a {core_tags}, {hand_position}, {background}, {angle}, {lighting}, {quality}"

MAKEUP_TEMPLATE = "close-up portrait of a {character} person with {core_tags}, {face_shape}, {hairstyle}, wearing {clothing}, {expression}, {background}, {lighting}, {quality}"

HAND_POSITION_POOL = [
    "hand extended forward, palm visible, object held clearly",
    "hands at chest level, presenting the object naturally",
    "hand raised, object shown against plain background",
    "holding at waist height, natural grip",
    "both hands holding, centered composition",
]

FACE_SHAPE_POOL = [
    "oval face shape, balanced proportions",
    "round face shape, soft jawline",
    "heart shaped face, pointed chin",
    "square face shape, strong jaw",
    "diamond face shape, high cheekbones",
    "long face shape, elegant proportions",
]

EXPRESSION_POOL = [
    "neutral expression, calm, serene",
    "slight smile, gentle, peaceful",
    "serious expression, intense gaze",
    "soft look, dreamy eyes, relaxed",
    "confident expression, direct eye contact",
    "melancholic expression, distant gaze",
]

CLOTHING_POOL = [
    "simple white hanfu, minimal style",
    "plain colored robe, unadorned",
    "basic traditional chinese dress, simple design",
    "plain black robe, simple cut",
]

def get_costume(costume_id):
    preset = COSTUME_PRESETS.get(costume_id)
    if preset: return preset
    return get_custom_preset("costume", costume_id)
def list_costumes():
    builtin = [{"id":v["id"],"name_cn":v["name_cn"],"tag_count":len(v["training_tags"]),"training_tags":v["training_tags"]} for v in COSTUME_PRESETS.values()]
    custom = list_custom_presets("costume")
    return builtin + custom
def get_prop(prop_id):
    preset = PROP_PRESETS.get(prop_id)
    if preset: return preset
    return get_custom_preset("prop", prop_id)
def list_props():
    builtin = [{"id":v["id"],"name_cn":v["name_cn"],"tag_count":len(v["training_tags"]),"training_tags":v["training_tags"]} for v in PROP_PRESETS.values()]
    custom = list_custom_presets("prop")
    return builtin + custom
def get_makeup(makeup_id):
    preset = MAKEUP_PRESETS.get(makeup_id)
    if preset: return preset
    return get_custom_preset("makeup", makeup_id)
def list_makeups():
    builtin = [{"id":v["id"],"name_cn":v["name_cn"],"tag_count":len(v["training_tags"]),"training_tags":v["training_tags"]} for v in MAKEUP_PRESETS.values()]
    custom = list_custom_presets("makeup")
    return builtin + custom