"""Movie Narration Web — 端到端运行脚本

用法:
    python run_pipeline.py                          # 交互式选择
    python run_pipeline.py --movie shawshank_redemption --style suspense_brainburn --platform douyin
    python run_pipeline.py --movie shawshank_redemption --style comedy --platform bilibili --mode auto
"""

import argparse
import asyncio
import json
import os
import sys
import time
from pathlib import Path

# Windows 终端编码修复
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

# 项目根目录
ROOT_DIR = Path(__file__).parent
DATA_DIR = ROOT_DIR / 'data'
OUTPUT_DIR = ROOT_DIR / 'output'
OUTPUT_DIR.mkdir(exist_ok=True)

# 确保 app 可导入
sys.path.insert(0, str(ROOT_DIR))


def load_json(path: Path) -> dict:
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)


async def check_deepseek_api() -> bool:
    """验证 DeepSeek API 连接"""
    import httpx

    api_key = os.getenv('DEEPSEEK_API_KEY', '')
    if not api_key:
        print('[ERROR] DEEPSEEK_API_KEY 环境变量未设置')
        return False

    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            resp = await client.get(
                'https://api.deepseek.com/v1/models',
                headers={'Authorization': f'Bearer {api_key}'},
            )
            if resp.status_code == 200:
                models = resp.json().get('data', [])
                model_ids = [m['id'] for m in models]
                print(f'[OK] DeepSeek API 连接成功')
                print(f'    可用模型: {", ".join(model_ids[:5])}...')
                return True
            else:
                print(f'[ERROR] DeepSeek API 返回 {resp.status_code}: {resp.text[:200]}')
                return False
        except Exception as e:
            print(f'[ERROR] DeepSeek API 连接失败: {e}')
            return False


async def run_deepseek_chat(system_prompt: str, user_prompt: str, model: str = 'deepseek-v4-pro', max_tokens: int = 4096) -> str:
    """调用 DeepSeek Chat API"""
    import httpx

    api_key = os.getenv('DEEPSEEK_API_KEY', '')
    url = 'https://api.deepseek.com/v1/chat/completions'

    payload = {
        'model': model,
        'messages': [
            {'role': 'system', 'content': system_prompt},
            {'role': 'user', 'content': user_prompt},
        ],
        'temperature': 0.8,
        'max_tokens': max_tokens,
        'response_format': {'type': 'json_object'},
    }

    async with httpx.AsyncClient(timeout=180.0) as client:
        resp = await client.post(
            url,
            headers={
                'Authorization': f'Bearer {api_key}',
                'Content-Type': 'application/json',
            },
            json=payload,
        )
        resp.raise_for_status()
        data = resp.json()
        content = data['choices'][0]['message']['content']

        # 使用量
        usage = data.get('usage', {})
        print(f'    tokens: {usage.get("total_tokens", "?")} '
              f'(prompt={usage.get("prompt_tokens", "?")}, '
              f'completion={usage.get("completion_tokens", "?")})')

        return content


# ==================================================================
# Stage 1: 电影理解 (Layer 1)
# ==================================================================

STAGE1_SYSTEM = """你是一位资深电影解说编剧，擅长发现电影中最具传播力的叙事角度。
你需要基于电影元数据，输出 3 个不同的解说角度。

每个角度必须包含:
- 一个能在 3 秒内讲完的"一句话钩子"
- 清晰的情绪弧线
- 三个关键情节点

请严格输出 JSON 格式。"""


def build_stage1_prompt(movie: dict, style: dict) -> str:
    return f"""电影信息：
- 片名：{movie['title']}（{movie['year']}）
- 类型：{', '.join(movie['genre'])}
- 评分：{movie['rating']}
- 导演：{movie.get('director', '')}
- 剧情摘要：{movie['plot_summary']}
- 关键场景：{json.dumps([s['name'] for s in movie.get('key_scenes', [])], ensure_ascii=False)}
- 解说热点：{json.dumps(movie.get('narration_hotspots', []), ensure_ascii=False)}

目标风格：{style['display_name']} —— {style['description']}

请输出 3 个候选解说角度的 JSON：
{{"angles": [{{"name": "...", "perspective": "...", "emotional_arc": "...", "one_liner": "...（3秒内讲完）", "three_key_beats": ["...", "...", "..."]}}]}}"""


# ==================================================================
# Stage 2: 结构规划 (Layer 2)
# ==================================================================

STAGE2_SYSTEM = """你是影视解说结构规划师。请将解说内容规划为标准的7段式结构。

7段式：hook(开场钩子) → intro(剧情引入) → plot_1(关键情节1) → twist(转折点) → plot_2(关键情节2) → climax(高潮) → ending(结尾点评)

每段需指定：目标情绪、目标字数范围、画面需求、BGM情绪

请严格输出 JSON 格式。"""


def build_stage2_prompt(angle: dict, style: dict, platform: str) -> str:
    platform_durations = {'douyin': '60-180秒', 'bilibili': '180-900秒', 'kuaishou': '60-180秒'}
    return f"""解说角度：{angle['name']} —— {angle['perspective']}
一句话钩子：{angle['one_liner']}
情绪弧线：{angle['emotional_arc']}

风格：{style['display_name']}（平均句长 {style['avg_sentence_length']} 字）
平台：{platform}（时长 {platform_durations.get(platform, '60-180秒')}）

请规划7段式结构，输出 JSON：
{{"structure": [{{"index": 1, "type": "hook", "target_emotion": "suspense", "word_count_target": 50, "visual_need": "...", "bgm_mood": "suspense"}}, ...]}}"""


# ==================================================================
# Stage 3: 文案撰写 (Layer 3)
# ==================================================================

STAGE3_SYSTEM = """你是影视解说文案写手。请根据结构规划，撰写完整的解说文案。

要求：
1. 开场钩子必须在 3 秒内制造信息差或情感冲击
2. 每句话都要自然口语化（不要书面语）
3. 为每段标注：emotion 情绪标签、emphasis_words 重音词
4. 为每段写 visual_requirement（画面需求描述）
5. 用 <#x.x#> 语法标注段落间停顿（如 <#0.5#> 表示停0.5秒）

请严格输出 JSON 格式。"""


def build_stage3_prompt(structure: list, style: dict, platform: str, movie_title: str) -> str:
    return f"""电影：《{movie_title}》
风格：{style['display_name']}
平台：{platform}

结构规划：
{json.dumps(structure, ensure_ascii=False, indent=2)}

风格要求：
- 高频词参考：{', '.join(style.get('high_freq_words', [])[:10])}
- 禁用词：{', '.join(style.get('banned_words', [])[:5])}
- 参考句式：{', '.join(style.get('sentence_pattern_preferences', []))}

请逐段输出完整文案，每段包含 text/emotion/emphasis_words/visual_requirement：
{{"segments": [{{"index": 1, "type": "hook", "text": "...", "emotion": "suspense", "emphasis_words": ["..."], "visual_requirement": {{"description": "...", "mood": "..."}}}}, ...], "total_words": 0}}"""


# ==================================================================
# Stage 4: 质量评分 (Layer 4)
# ==================================================================

def score_script(script: dict, style: dict) -> dict:
    """本地评分（不调 LLM，直接用规则引擎）"""
    segments = script.get('segments', [])
    if not segments:
        return {'overall_score': 0, 'scores': {}}

    all_text = ' '.join(s.get('text', '') for s in segments)

    # 钩子吸引力
    hook_text = segments[0].get('text', '')
    hook_score = 5.0
    if any(kw in hook_text for kw in ['?', '？', '有没有', '想过', '知道吗']):
        hook_score += 2.0
    if any(kw in hook_text for kw in ['但是', '然而', '居然', '竟然']):
        hook_score += 1.5
    if any(kw in hook_text for kw in ['万', '亿', '20年', '最']):
        hook_score += 1.0
    if len(hook_text) > 80:
        hook_score -= 1.0
    hook_score = min(round(hook_score, 1), 10.0)

    # 信息密度
    filler_words = ['然后', '就是', '其实', '所以', '总而言之', '众所周知']
    filler_count = sum(all_text.count(w) for w in filler_words)
    info_markers = sum(1 for c in all_text if c.isdigit())
    density_score = min(round(5.0 - filler_count * 0.5 + info_markers * 0.3, 1), 10.0)

    # 口语化
    formal_markers = ['该片', '影片', '通过', '展现', '呈现', '诠释', '综上所述']
    colloquial_markers = ['离谱', '绝了', '太', '真的', '吗', '吧', '啊', '简直']
    formal_count = sum(all_text.count(w) for w in formal_markers)
    colloquial_count = sum(all_text.count(w) for w in colloquial_markers)
    colloquial_score = min(round(5.0 - formal_count * 2 + colloquial_count * 1.5, 1), 10.0)

    # 风格一致性
    style_hit = sum(all_text.count(w) for w in style.get('high_freq_words', []))
    style_ban = sum(all_text.count(w) for w in style.get('banned_words', []))
    style_score = min(round(5.0 + style_hit * 0.5 - style_ban * 2, 1), 10.0)

    scores = {
        'hook_attraction': hook_score,
        'information_density': max(0, density_score),
        'colloquialism': max(0, colloquial_score),
        'style_consistency': max(0, style_score),
    }

    weights = {'hook_attraction': 0.35, 'information_density': 0.25,
               'colloquialism': 0.25, 'style_consistency': 0.15}
    overall = sum(scores[k] * weights[k] for k in weights)

    return {
        'overall_score': round(overall, 1),
        'scores': scores,
        'total_words': script.get('total_words', len(all_text)),
    }


# ==================================================================
# 主流程
# ==================================================================

async def run_pipeline(
    movie_id: str,
    style_id: str,
    platform: str = 'douyin',
    mode: str = 'interactive',
):
    """执行完整的出片流程"""
    print('=' * 60)
    print('  Movie Narration Web — 一键出片 Pipeline')
    print('=' * 60)

    # 0. 加载数据
    print('\n[0/4] 加载数据...')
    movie_lib = load_json(DATA_DIR / 'movie_library.json')
    style_lib = load_json(DATA_DIR / 'style_fingerprints.json')

    movie = next((m for m in movie_lib['movies'] if m['movie_id'] == movie_id), None)
    style = next((s for s in style_lib['styles'] if s['style_id'] == style_id), None)

    if not movie:
        print(f'[ERROR] 未找到电影: {movie_id}')
        return
    if not style:
        print(f'[ERROR] 未找到风格: {style_id}')
        return

    print(f'  电影: {movie["title"]} ({movie["year"]}) ⭐{movie["rating"]}')
    print(f'  风格: {style["display_name"]}')
    print(f'  平台: {platform}')

    # 检查 API
    if not await check_deepseek_api():
        return

    # ================================================================
    # Stage 1: 电影理解 → 3 个解说角度
    # ================================================================
    print(f'\n[1/4] 电影理解 — 生成解说角度...')
    t1 = time.time()

    try:
        angles_raw = await run_deepseek_chat(
            system_prompt=STAGE1_SYSTEM,
            user_prompt=build_stage1_prompt(movie, style),
        )
        angles_data = json.loads(angles_raw.strip().lstrip('```json').rstrip('```'))
        angles = angles_data.get('angles', [])
        print(f'  [OK] 生成了 {len(angles)} 个候选角度 ({time.time()-t1:.1f}s)')
        for a in angles:
            print(f'    • {a["name"]}: "{a["one_liner"][:60]}..."')
    except Exception as e:
        print(f'  [ERROR] Stage 1 失败: {e}')
        return

    best_angle = angles[0]
    if mode == 'interactive' and len(angles) > 1:
        print('\n  选择角度（输入序号，默认 1）：')
        for i, a in enumerate(angles):
            print(f'    {i+1}. {a["name"]}')
        choice = input('  > ').strip()
        if choice.isdigit() and 1 <= int(choice) <= len(angles):
            best_angle = angles[int(choice) - 1]

    # ================================================================
    # Stage 2: 结构规划
    # ================================================================
    print(f'\n[2/4] 结构规划 — 7段式骨架...')
    t2 = time.time()

    try:
        structure_raw = await run_deepseek_chat(
            system_prompt=STAGE2_SYSTEM,
            user_prompt=build_stage2_prompt(best_angle, style, platform),
        )
        structure_data = json.loads(structure_raw.strip().lstrip('```json').rstrip('```'))
        structure = structure_data.get('structure', [])
        print(f'  [OK] 规划了 {len(structure)} 段 ({time.time()-t2:.1f}s)')
        for s in structure:
            print(f'    [{s["type"]}] {s["target_emotion"]:12s} ~{s["word_count_target"]}字')
    except Exception as e:
        print(f'  [ERROR] Stage 2 失败: {e}')
        return

    # ================================================================
    # Stage 3: 文案撰写
    # ================================================================
    print(f'\n[3/4] 文案撰写 — 生成完整文案...')
    t3 = time.time()

    try:
        script_raw = await run_deepseek_chat(
            system_prompt=STAGE3_SYSTEM,
            user_prompt=build_stage3_prompt(structure, style, platform, movie['title']),
            max_tokens=8192,  # 文案生成需要更大的输出空间
        )
        script_data = json.loads(script_raw.strip().lstrip('```json').rstrip('```'))
        segments = script_data.get('segments', [])
        total_words = script_data.get('total_words', sum(len(s.get('text', '')) for s in segments))
        print(f'  [OK] 生成 {len(segments)} 段文案，共 {total_words} 字 ({time.time()-t3:.1f}s)')
    except Exception as e:
        print(f'  [ERROR] Stage 3 失败: {e}')
        return

    # ================================================================
    # Stage 4: 质量评分
    # ================================================================
    print(f'\n[4/4] 质量评分...')

    quality = score_script({'segments': segments, 'total_words': total_words}, style)
    print(f'  综合评分: {quality["overall_score"]}/10')
    print(f'  钩子吸引力: {quality["scores"]["hook_attraction"]}/10')
    print(f'  信息密度:   {quality["scores"]["information_density"]}/10')
    print(f'  口语化程度: {quality["scores"]["colloquialism"]}/10')
    print(f'  风格一致性: {quality["scores"]["style_consistency"]}/10')

    if quality['overall_score'] >= 7.0:
        print(f'  [✓] 质量过关，可进入配音阶段')
    elif quality['overall_score'] >= 5.0:
        print(f'  [!] 质量中等，建议人工审阅')
    else:
        print(f'  [✗] 质量不足，建议换个角度重写')

    # ================================================================
    # 保存结果
    # ================================================================
    output = {
        'movie': movie['title'],
        'style': style['display_name'],
        'platform': platform,
        'angle': best_angle,
        'structure': structure,
        'script': {
            'segments': segments,
            'total_words': total_words,
        },
        'quality': quality,
        'generated_at': time.strftime('%Y-%m-%d %H:%M:%S'),
    }

    output_path = OUTPUT_DIR / f'{movie_id}_{style_id}_{platform}.json'
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    # ================================================================
    # 打印文案预览
    # ================================================================
    print(f'\n{"="*60}')
    print(f'  完整文案预览')
    print(f'{"="*60}')
    for seg in segments:
        print(f'\n  [{seg["type"]}] {seg.get("emotion", "")}')
        print(f'  {seg["text"][:200]}')
        if len(seg['text']) > 200:
            print(f'  ...（共 {len(seg["text"])} 字）')

    print(f'\n{"="*60}')
    print(f'  结果已保存到: {output_path}')
    print(f'{"="*60}')

    return output


# ==================================================================
# CLI 入口
# ==================================================================

def main():
    parser = argparse.ArgumentParser(description='Movie Narration Web — 一键出片')
    parser.add_argument('--movie', default='shawshank_redemption', help='电影 ID')
    parser.add_argument('--style', default='suspense_brainburn', help='风格 ID')
    parser.add_argument('--platform', default='douyin', choices=['douyin', 'bilibili', 'kuaishou', 'xiaohongshu'])
    parser.add_argument('--mode', default='interactive', choices=['interactive', 'auto'])
    parser.add_argument('--list-movies', action='store_true', help='列出所有可用电影')
    parser.add_argument('--list-styles', action='store_true', help='列出所有可用风格')
    parser.add_argument('--check-api', action='store_true', help='仅检查 API 连接')

    args = parser.parse_args()

    if args.list_movies:
        lib = load_json(DATA_DIR / 'movie_library.json')
        for m in lib['movies']:
            print(f'  {m["movie_id"]:30s} {m["title"]} ({m["year"]}) ⭐{m["rating"]}')
        return

    if args.list_styles:
        lib = load_json(DATA_DIR / 'style_fingerprints.json')
        for s in lib['styles']:
            print(f'  {s["style_id"]:25s} {s["display_name"]} — {s["description"]}')
        return

    if args.check_api:
        asyncio.run(check_deepseek_api())
        return

    asyncio.run(run_pipeline(
        movie_id=args.movie,
        style_id=args.style,
        platform=args.platform,
        mode=args.mode,
    ))


if __name__ == '__main__':
    main()
