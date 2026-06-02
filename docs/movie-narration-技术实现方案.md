# Movie Narration Web — 一键出解说片 技术实现方案

> **文档类型**：技术实现方案
> **创建日期**：2026-05-30
> **版本**：v1.0
> **前置文档**：[movie-narration-web-设计方案.md](./movie-narration-web-设计方案.md)
> **调研基础**：NarratoAI / narrator-ai / Pixelle-Video / TwelveLabs / Remotion / B站花生&UpDream

---

## 目录

1. [总体技术架构](#1-总体技术架构)
2. [文案生成引擎](#2-文案生成引擎)
3. [视频理解与画面匹配](#3-视频理解与画面匹配)
4. [配音生成系统](#4-配音生成系统)
5. [视觉模板与组装引擎](#5-视觉模板与组装引擎)
6. [BGM 自动匹配与混音](#6-bgm-自动匹配与混音)
7. [多平台自适应引擎](#7-多平台自适应引擎)
8. [编排决策引擎](#8-编排决策引擎)
9. [Remotion Video-as-Code 方案](#9-remotion-video-as-code-方案)
10. [完整技术栈推荐](#10-完整技术栈推荐)
11. [MVP 落地方案](#11-mvp-落地方案)
12. [附录：竞品技术对标](#12-附录竞品技术对标)

---

## 1. 总体技术架构

### 1.1 架构全景图（基于 2026 年最新技术生态）

```
┌──────────────────────────────────────────────────────────────────┐
│                        浏览器前端 (Next.js 15)                      │
│                                                                  │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────────────┐   │
│  │ 对话面板  │ │ 时间线    │ │ 素材库    │ │ Remotion Player  │   │
│  │ (Agent)  │ │ (Timeline)│ │ (Assets) │ │ (实时预览)       │   │
│  └────┬─────┘ └────┬─────┘ └────┬─────┘ └────────┬─────────┘   │
│       └─────────────┴────────────┴───────────────┘              │
│                         │ WebSocket + HTTP                        │
└─────────────────────────┼────────────────────────────────────────┘
                          │
┌─────────────────────────┼────────────────────────────────────────┐
│                    API Gateway (FastAPI)                          │
│                                                                  │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────────────┐   │
│  │ 用户服务  │ │ 项目管理  │ │ 编排引擎  │ │ 计费服务          │   │
│  └──────────┘ └──────────┘ └────┬─────┘ └──────────────────┘   │
└─────────────────────────────────┼────────────────────────────────┘
                                  │
┌─────────────────────────────────┼────────────────────────────────┐
│                    编排决策引擎 (Orchestrator)                      │
│                                                                  │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │                   工作流引擎 (Temporal)                     │   │
│  │                                                          │   │
│  │  选片 → 风格学习 → 文案生成 → 人工审阅 → 配音 → 剪辑 → 导出  │   │
│  │                                                          │   │
│  │  + 质量决策层：每步完成后自动评估 → 决定：继续/重试/暂停     │   │
│  └──────────────────────────────────────────────────────────┘   │
│                         │                                        │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │                   模型路由层 (Model Router)                 │   │
│  │                                                          │   │
│  │  LLM 路由      │  视频理解路由   │  TTS 路由  │  BGM 路由   │   │
│  │  DeepSeek R1   │  Marengo 3.0   │  CosyVoice │  Suno/     │   │
│  │  Claude/GPT    │  Qwen2.5-VL    │  ElevenLabs│  素材库     │   │
│  └──────────────────────────────────────────────────────────┘   │
└──────────────────────────────────────────────────────────────────┘
                                  │
┌─────────────────────────────────┼────────────────────────────────┐
│                    AI 能力服务层                                   │
│                                                                  │
│  ┌────────────┐ ┌──────────┐ ┌──────────┐ ┌────────────────┐   │
│  │ 文案生成    │ │ 画面匹配  │ │ 配音生成  │ │ 视觉组装        │   │
│  │ Service    │ │ Service  │ │ Service  │ │ Service        │   │
│  │            │ │          │ │          │ │                │   │
│  │ 4-stage    │ │ 多模态    │ │ SSML     │ │ VDL 编译       │   │
│  │ prompt     │ │ 检索     │ │ 标注驱动  │ │ + FFmpeg       │   │
│  │ chain      │ │ pipeline │ │ pipeline  │ │ / Remotion     │   │
│  └────────────┘ └──────────┘ └──────────┘ └────────────────┘   │
└──────────────────────────────────────────────────────────────────┘
                                  │
┌─────────────────────────────────┼────────────────────────────────┐
│                    基础设施层                                      │
│                                                                  │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────────────┐   │
│  │ PostgreSQL│ │ Redis    │ │ S3/MinIO │ │ FFmpeg 渲染集群   │   │
│  │ +pgvector│ │ (缓存/队列)│ │ +CDN    │ │ (K8s Job)        │   │
│  └──────────┘ └──────────┘ └──────────┘ └──────────────────┘   │
└──────────────────────────────────────────────────────────────────┘
```

### 1.2 核心设计原则

```
原则 1：每个 AI 能力模块独立部署、独立扩缩容、独立 fallback
原则 2：素材处理采用"本地优先 + 云端弹性"混合策略
原则 3：视频合成路径支持双引擎：FFmpeg（速度优先）/ Remotion（表现力优先）
原则 4：所有 LLM 调用走统一抽象层，模型可热切换
原则 5：质量评分贯穿全流程——每一步输出都有量化指标
```

---

## 2. 文案生成引擎

### 2.1 为什么需要多 Agent 协作而非单次 LLM 调用

```
单次 LLM 调用的天花板：
  输入："请用励志风格为《肖申克的救赎》写一篇抖音解说文案"
  输出：一篇"看起来像解说"但——信息密度低、钩子无力、节奏平、口语化不足

根本原因：
  一次调用中同时处理 "故事线设计" + "钩子创作" + "句式优化" + "口语化" + "时长控制"
  → prompt 越长，LLM 越是"面面俱到但面面不精"

解法：分层 Agent 协作，每个 Agent 只做一件事
```

### 2.2 四层 Agent 架构

```
┌─────────────────────────────────────────────────────────────────┐
│                    Layer 1: 电影理解层                            │
│                                                                 │
│  输入：电影名称 + 元数据（关键场景、角色、剧情摘要）                │
│  输出：解说角度 × 3                                              │
│  模型：Claude Opus 4.8（需要深度推理和电影知识）                   │
│                                                                 │
│  Prompt 核心逻辑：                                                │
│    1. 识别电影的核心矛盾（人物 vs 体制 / 人物 vs 自我 / 人物 vs 命运）│
│    2. 找到最具情感冲击力的 3 个情节点                              │
│    3. 确定解说角度：从哪个角色的视角？什么情绪基调？                │
│    4. 输出 3 个候选角度 + 每个角度的"一句话钩子"                   │
│                                                                 │
│  输出示例：                                                      │
│  {                                                              │
│    "angles": [                                                  │
│      {                                                          │
│        "name": "绝望中的希望",                                    │
│        "perspective": "安迪视角",                                 │
│        "emotional_arc": "压抑→希望→释放",                         │
│        "one_liner": "一个被关了20年的人，越狱时走的是一条所有人     │
│                      每天都经过的路"                              │
│      },                                                         │
│      {                                                          │
│        "name": "体制化的牢笼",                                    │
│        "perspective": "瑞德视角",                                 │
│        "emotional_arc": "旁观→理解→觉醒",                         │
│        "one_liner": "他在监狱里待了40年，出狱后第一件事，          │
│                      是向经理请假去上厕所"                        │
│      }                                                          │
│    ]                                                            │
│  }                                                              │
└─────────────────────────────────────────────────────────────────┘
                                  │
                                  ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Layer 2: 结构规划层                            │
│                                                                 │
│  输入：选定的解说角度 + 风格指纹                                   │
│  输出：7 段式结构骨架（每段标注：目标情绪、信息密度、预估字数）     │
│  模型：Claude Sonnet 4.6（结构规划不需要极致深度推理）             │
│                                                                 │
│  7 段式标准结构：                                                 │
│  ┌──────────┬────────────┬──────────┬──────────┬─────────────┐  │
│  │ 段落     │ 目标        │ 情绪     │ 字数占比  │ 画面策略     │  │
│  ├──────────┼────────────┼──────────┼──────────┼─────────────┤  │
│  │ 1.开场钩子│ 3秒内抓住   │ 震惊/好奇 │ 10%      │ 视觉冲击力强  │  │
│  │ 2.剧情引入│ 建立认知    │ 铺垫     │ 15%      │ 剧照+文字     │  │
│  │ 3.关键情节1│ 第一个爆点  │ 紧张     │ 18%      │ 原片片段优先  │  │
│  │ 4.转折点  │ 打破预期    │ 意外     │ 15%      │ 原片片段优先  │  │
│  │ 5.关键情节2│ 第二个爆点  │ 悬疑     │ 18%      │ 原片片段优先  │  │
│  │ 6.高潮    │ 情绪峰值    │ 激昂/感动 │ 14%      │ 原片精华片段  │  │
│  │ 7.结尾点评│ 回味/升华   │ 余韵     │ 10%      │ 剧照+文字     │  │
│  └──────────┴────────────┴──────────┴──────────┴─────────────┘  │
│                                                                 │
│  输出示例：                                                      │
│  {                                                              │
│    "structure": [                                               │
│      {                                                          │
│        "segment": 1,                                            │
│        "type": "hook",                                          │
│        "target_emotion": "shock_curiosity",                      │
│        "word_count_estimate": 60,                                │
│        "visual_need": "high_impact_opening_image",               │
│        "bgm_mood": "suspense_build"                              │
│      },                                                         │
│      // ... 其余 6 段                                            │
│    ],                                                           │
│    "estimated_total_duration": 180,  // 秒                       │
│    "estimated_word_count": 850                                   │
│  }                                                              │
└─────────────────────────────────────────────────────────────────┘
                                  │
                                  ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Layer 3: 文案撰写层 (并行)                      │
│                                                                 │
│  输入：结构规划 + 风格指纹                                        │
│  输出：3 版完整文案（含 SSML 标注、情绪标签、画面需求描述）         │
│  模型：DeepSeek R1/V3（中文创意写作最强，成本仅为 GPT-4o 的 1/10） │
│                                                                 │
│  并发策略：3 个 Agent 同时独立撰写，互相不参考（保证多样性）        │
│                                                                 │
│  Agent A：激进型 — 钩子更夸张、节奏更快、多反转                    │
│  Agent B：稳健型 — 叙事饱满、情绪递进、经典结构                     │
│  Agent C：创意型 — 非常规切入、独特比喻、记忆点强化                 │
│                                                                 │
│  每个 Agent 输出的结构化文案格式：                                 │
│  {                                                              │
│    "script_id": "v1_aggressive",                                 │
│    "segments": [                                                │
│      {                                                          │
│        "index": 1,                                              │
│        "type": "hook",                                          │
│        "text": "你有没有想过，一个被判终身监禁的银行家，           │
│                 如何用一把藏在圣经里的小锤子，花了20年，            │
│                 在墙上挖出一条隧道？",                             │
│        "ssml": "<prosody rate='0.95' pitch='+1st'>你有没有        │
│                 想过</prosody><break time='500ms'/>              │
│                 <prosody rate='1.05'>一个被判                    │
│                 <emphasis level='strong'>终身监禁</emphasis>     │
│                 的银行家</prosody><break time='300ms'/>...",     │
│        "emotion": "suspense",                                    │
│        "emphasis_words": ["想过", "终身监禁", "20年", "隧道"],    │
│        "visual_requirement": {                                   │
│          "description": "监狱高墙的压迫感画面 + 安迪入狱时的       │
│                          特写镜头（无助但坚定的眼神）",            │
│          "preferred_source": "original_clip",                    │
│          "scene_hint": "shawshank_prison_exterior",              │
│          "mood": "oppressive_but_hopeful"                        │
│        },                                                       │
│        "estimated_duration_sec": 12.5                            │
│      }                                                          │
│      // ... 其余 6 段                                            │
│    ],                                                           │
│    "hooks_scoreable": {                                          │
│      "opening_hook_type": "information_gap",                     │
│      "surprise_level": 0.85,                                     │
│      "curiosity_gap": 0.90                                       │
│    }                                                            │
│  }                                                              │
└─────────────────────────────────────────────────────────────────┘
                                  │
                                  ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Layer 4: 质量评分层                             │
│                                                                 │
│  输入：3 版文案                                                   │
│  输出：评分报告 + 最佳版本 + 移植建议                              │
│  模型：Claude Haiku 4.5（快速评分，成本极低）                      │
│                                                                 │
│  评分维度：                                                      │
│  ┌────────────────┬──────────┬──────────────────────────────┐   │
│  │ 维度           │ 权重     │ 评估方法                      │   │
│  ├────────────────┼──────────┼──────────────────────────────┤   │
│  │ 钩子吸引力     │ 25%      │ 信息差/惊讶度/好奇心缺口       │   │
│  │ 信息密度       │ 20%      │ 每百字信息点数 / 废话比例      │   │
│  │ 节奏曲线       │ 15%      │ 句子长度方差 / 情绪切换频率    │   │
│  │ 口语化程度     │ 15%      │ 书面语特征词检测 + LLM 评分    │   │
│  │ 时长合规       │ 10%      │ TTS 预估时长 vs 平台限制       │   │
│  │ 风格一致性     │ 10%      │ 与风格指纹的向量余弦相似度      │   │
│  │ 敏感词检查     │ 5%       │ 多平台敏感词库匹配             │   │
│  └────────────────┴──────────┴──────────────────────────────┘   │
│                                                                 │
│  移植策略：                                                      │
│    选最高分版本作为 base → 检查其他版本中是否有单项得分更高的段落   │
│    → 如果某段在另一版本中得分显著更高 → 移植该段落到 base           │
│    → 检查移植后的上下文连贯性 → 微调衔接句                         │
└─────────────────────────────────────────────────────────────────┘
```

### 2.3 Prompt Chain 设计（借鉴 NarratoAI 已验证模式）

```python
# 4-stage prompt chain 伪代码

class ScriptGenerationPipeline:
    """文案生成流水线 —— 借鉴 NarratoAI 的 prompt chain 模式"""

    STAGE_1_PROMPT = """
    你是一位资深电影解说编剧。请分析以下电影，提取关键信息：
    
    电影：{movie_title}
    元数据：{movie_metadata}
    目标风格：{style_name}
    
    请输出 JSON：
    {{
      "core_conflict": "一句话概括核心矛盾",
      "three_key_beats": ["情节点1", "情节点2", "情节点3"],
      "emotional_high_point": "情绪最高点在哪",
      "suggested_perspective": "建议的解说视角及理由"
    }}
    """

    STAGE_2_PROMPT = """
    基于以下分析，规划 7 段式解说结构：
    
    电影分析：{stage_1_output}
    风格参数：{style_fingerprint}
    平台约束：{platform_constraints}
    
    每段需要指定：类型、目标情绪、预估字数、视觉需求、BGM情绪
    
    输出 JSON 结构：...
    """

    STAGE_3_PROMPT = """
    你是一位{style_name}风格的解说文案写手。
    
    结构规划：{stage_2_output}
    风格指纹：{style_fingerprint}
    
    写作要求：
    - 开场钩子必须在 3 秒内制造信息差或情感冲击
    - 每句话都要有清晰的画面需求描述
    - 标注所有停顿位置（用 <#x.x#> 语法）
    - 标注每段的情绪标签
    - 标注重音词
    
    请生成完整文案，输出 JSON...
    """

    STAGE_4_PROMPT = """
    请对以下 3 版文案进行多维度评分：
    
    版本 A：{script_a}
    版本 B：{script_b}
    版本 C：{script_c}
    
    评分维度：钩子吸引力、信息密度、节奏曲线、口语化程度、时长合规、风格一致性
    
    输出：每版各维度得分 + 综合排名 + 最佳版本 + 建议移植的段落
    """
```

### 2.4 风格指纹注入机制

```python
# 风格指纹在 prompt 中的注入方式

STYLE_INJECTION_TEMPLATE = """
## 风格参数（必须严格遵循）

### 叙事节奏
- 句子平均长度：{avg_sentence_length} 字
- 句子长度变化范围：{sentence_length_variance}
- 段落间停顿偏好：{pause_pattern}

### 钩子策略
- 开场方式偏好：{hook_type}（设问 / 反转 / 数据冲击 / 悬念）
- 钩子密度：每 {hook_density} 字一个钩子点

### 情绪曲线
- 情绪切换频率：{emotion_switch_frequency}
- 情绪强度基线：{emotion_intensity_baseline}
- 情绪递进模式：{emotion_progression_pattern}

### 词汇风格
- 高频词库：{high_freq_words}
- 禁用词：{banned_words}
- 句式偏好：{sentence_pattern_preference}

### 口语特征
- 语气词密度：{interjection_density}
- 方言/网络梗使用：{slang_usage}
- 反问句频率：{rhetorical_question_frequency}

## 参考例句（从风格学习中提取）
{reference_sentences}
"""
```

---

## 3. 视频理解与画面匹配

### 3.1 三层匹配架构

```
┌──────────────────────────────────────────────────────────────────┐
│                    画面匹配引擎                                    │
│                                                                  │
│  文案段落："安迪在雨中张开双臂，拥抱自由"                           │
│       │                                                          │
│       ▼                                                          │
│  ┌──────────────────────────────────────────────────────────┐    │
│  │ Layer 1: 精确匹配（原片场景索引）                          │    │
│  │                                                          │    │
│  │  条件：电影在预置素材库中（50 部 MVP / 500+ 长期）         │    │
│  │  方法：多模态向量搜索                                      │    │
│  │  技术：TwelveLabs Marengo 3.0 / CLIP + pgvector           │    │
│  │  精度：帧级（~0.1 秒）                                    │    │
│  │  延迟：~50ms                                              │    │
│  │  适用场景：关键情节段的原片画面                             │    │
│  └──────────────────────────────────────────────────────────┘    │
│                          │                                       │
│                    ┌─────▼─────┐                                 │
│                    │ 置信度 > 0.8?│                                │
│                    └─────┬─────┘                                 │
│                     Yes  │  No                                   │
│                          ▼                                       │
│  ┌──────────────────────────────────────────────────────────┐    │
│  │ Layer 2: 近似匹配（通用素材库 + 视觉模板）                  │    │
│  │                                                          │    │
│  │  条件：精确匹配失败或置信度低                               │    │
│  │  方法：语义检索 + 视觉模板渲染                              │    │
│  │  技术：CLIP 向量检索 + Canvas 渲染                         │    │
│  │  精度：场景级（~3 秒）                                     │    │
│  │  延迟：~200ms                                              │    │
│  │  适用场景：过渡段落、情绪铺垫                               │    │
│  └──────────────────────────────────────────────────────────┘    │
│                          │                                       │
│                    ┌─────▼─────┐                                 │
│                    │ 置信度 > 0.5?│                                │
│                    └─────┬─────┘                                 │
│                     Yes  │  No                                   │
│                          ▼                                       │
│  ┌──────────────────────────────────────────────────────────┐    │
│  │ Layer 3: 降级兜底（纯视觉模板）                            │    │
│  │                                                          │    │
│  │  方法：Canvas 渲染的视觉模板                               │    │
│  │  模板类型：                                                │    │
│  │    - 剧照背景 + 毛玻璃 + 大字标题                          │    │
│  │    - 纯色渐变 + 情绪词 + emoji                             │    │
│  │    - 分屏对比（两个角色/两个场景）                          │    │
│  │    - 时间线动画（事件递进）                                │    │
│  │  延迟：~50ms（纯渲染）                                     │    │
│  └──────────────────────────────────────────────────────────┘    │
└──────────────────────────────────────────────────────────────────┘
```

### 3.2 TwelveLabs Marengo 3.0 集成方案

```python
# TwelveLabs Marengo 3.0 集成 —— 帧级电影画面检索

from twelvelabs import TwelveLabs
from twelvelabs.models import SearchOptions

class MovieSceneIndex:
    """电影场景多模态索引"""

    def __init__(self, api_key: str):
        self.client = TwelveLabs(api_key=api_key)

    def index_movie(self, movie_file_path: str, movie_id: str) -> str:
        """将整部电影建立多模态索引（一次性操作，结果持久化）"""
        # 上传视频文件
        task = self.client.task.create(
            index_id=self._get_or_create_index(movie_id),
            file=movie_file_path,
            language="zh"
        )
        # 等待索引完成（~6 分钟处理 2 小时电影）
        task.wait()
        return task.video_id

    def search_scene(
        self,
        movie_id: str,
        text_query: str,
        image_query: bytes = None,  # 可选的图像参考
        top_k: int = 5
    ) -> list[dict]:
        """多模态搜索：文案描述 → 精确时间戳

        Args:
            text_query: 如 "安迪在雨中张开双臂拥抱自由"
            image_query: 可选，安迪的剧照用于组合搜索
        """
        options = SearchOptions(
            index_id=self._get_index_id(movie_id),
            query=text_query,
            # 组合搜索：文字 + 图像
            query_image=image_query,
            # 只搜索视觉模态
            search_options=["visual"],
            # 返回前 K 个匹配
            max_results=top_k,
            # 置信度阈值
            confidence_threshold=0.6
        )

        results = self.client.search.create(options)

        return [
            {
                "start_time": r.start,
                "end_time": r.end,
                "confidence": r.confidence,
                "thumbnail_url": r.thumbnail_url,
            }
            for r in results
        ]

    def batch_search_script(
        self,
        movie_id: str,
        script_segments: list[dict]
    ) -> list[dict]:
        """批量匹配：文案的每个段落 → 电影中的对应画面

        Args:
            script_segments: 文案生成引擎输出的 segments 数组
        Returns:
            每个 segment 的匹配结果 + 降级策略
        """
        clip_plan = []

        for seg in script_segments:
            # 尝试精确匹配
            results = self.search_scene(
                movie_id=movie_id,
                text_query=seg["visual_requirement"]["description"],
                top_k=3
            )

            best = results[0] if results else None

            if best and best["confidence"] > 0.8:
                # Layer 1: 精确匹配成功
                clip_plan.append({
                    "segment_index": seg["index"],
                    "source": "original_clip",
                    "time_range": [best["start_time"], best["end_time"]],
                    "confidence": best["confidence"],
                    "fallback": None
                })
            elif best and best["confidence"] > 0.5:
                # Layer 2: 近似匹配（可用但标记为建议替换）
                clip_plan.append({
                    "segment_index": seg["index"],
                    "source": "original_clip",
                    "time_range": [best["start_time"], best["end_time"]],
                    "confidence": best["confidence"],
                    "warning": "low_confidence_suggest_review",
                    "fallback": self._get_visual_template(seg)
                })
            else:
                # Layer 3: 降级到视觉模板
                clip_plan.append({
                    "segment_index": seg["index"],
                    "source": "visual_template",
                    "template": self._get_visual_template(seg),
                    "confidence": best["confidence"] if best else 0.0,
                    "fallback": None
                })

        return clip_plan
```

### 3.3 降级方案：CLIP + pgvector（不依赖 TwelveLabs 时）

```python
# 备选方案：CLIP + pgvector 本地检索（MVP 阶段）
# 参考 Pixelle-Video 和 NarratoAI 的做法

import clip
import torch
from pgvector.django import L2Distance

class CLIPSceneMatcher:
    """基于 CLIP 的场景匹配器 —— MVP 阶段使用"""

    def __init__(self):
        self.model, self.preprocess = clip.load("ViT-L/14")

    def extract_keyframes(self, video_path: str, interval_sec: float = 3.0) -> list:
        """每 N 秒抽取关键帧 + 计算 CLIP 嵌入"""
        frames = []
        # FFmpeg 关键帧抽取
        # ffmpeg -i movie.mp4 -vf "fps=1/{interval_sec}" frame_%04d.jpg
        for frame_path in extracted_frames:
            image = self.preprocess(Image.open(frame_path)).unsqueeze(0)
            with torch.no_grad():
                embedding = self.model.encode_image(image)
            frames.append({
                "timecode": extract_timecode(frame_path),
                "embedding": embedding.numpy().tolist(),
                "path": frame_path
            })
        return frames

    def search(self, text_query: str, frames: list, top_k: int = 5) -> list:
        """文本查询 → CLIP 嵌入 → pgvector L2 距离排序"""
        text_tokens = clip.tokenize([text_query])
        with torch.no_grad():
            text_embedding = self.model.encode_text(text_tokens)

        # pgvector 查询
        results = (
            FrameEmbedding.objects
            .order_by(L2Distance("embedding", text_embedding))
            .annotate(distance=L2Distance("embedding", text_embedding))
            [:top_k]
        )
        return results

    # 优势：免费、本地运行、隐私安全
    # 劣势：精度不如 Marengo 3.0（约 70% vs 90%+）
    #      不支持组合搜索（文字+图像）
    #      不支持时序推理（跨场景关系理解）
```

### 3.4 画面构成策略

```
解说视频的实际画面来源配比（基于 B站 影视解说区实际数据分析）：

┌──────────────────────────────────────────────────────────────┐
│  画面来源                  占比    技术方案                  │
├──────────────────────────────────────────────────────────────┤
│  视觉模板（剧照+文字+特效）  40%    Canvas/Remotion 渲染     │
│  原片精确匹配片段            30%    Marengo 3.0 / CLIP 检索  │
│  表情包/meme/网络素材       15%    预置素材库 + 搜索          │
│  纯色背景+大字标题           10%    Canvas 渲染               │
│  AI 生成画面                 5%    Kling/Seedance（可选）     │
└──────────────────────────────────────────────────────────────┘

核心洞察：70% 的画面不需要原片精准匹配，可以靠视觉模板 + 素材库覆盖
这意味着 MVP 阶段即使没有 TwelveLabs，也能做出"基本能看"的解说视频
```

---

## 4. 配音生成系统

### 4.1 SSML 标注驱动架构

```
核心设计理念：
  不让用户手动调配音参数 → 让 LLM 在写文案时同步输出发音标注
  用户只需选择"配音角色"，其余全部自动

┌──────────────────────────────────────────────────────────────────┐
│                    配音生成 Pipeline                              │
│                                                                  │
│  文案（含 SSML 标注）                                             │
│       │                                                          │
│       ▼                                                          │
│  ┌──────────────┐                                                │
│  │ SSML 校验器   │ ← XML 合法性 + 停顿范围合理性 + 总时长预估      │
│  └──────┬───────┘                                                │
│         │                                                        │
│         ▼                                                        │
│  ┌──────────────┐                                                │
│  │ 配音角色路由  │ → narrator-ai TTS / CosyVoice2 / ElevenLabs    │
│  └──────┬───────┘                                                │
│         │                                                        │
│         ▼                                                        │
│  ┌──────────────┐                                                │
│  │ 音频后处理    │ ← 音量归一化 / 去噪 / 静音段裁剪               │
│  └──────┬───────┘                                                │
│         │                                                        │
│         ▼                                                        │
│  ┌──────────────┐                                                │
│  │ 时间轴对齐    │ ← 每段配音的实际时长 vs 预估时长 → 调整画面持续  │
│  └──────────────┘                                                │
└──────────────────────────────────────────────────────────────────┘
```

### 4.2 LLM 输出的 SSML 标注格式

```xml
<!-- LLM 在写文案时同步输出的 SSML 标注 -->
<speak>
  <!-- 开场钩子：悬念感 -->
  <prosody rate="0.95" pitch="+1st">
    你有没有<emphasis level="strong">想过</emphasis>
  </prosody>
  <break time="500ms"/>

  <!-- 信息揭露：语速稍快，强调关键信息 -->
  <prosody rate="1.05">
    一个被判<emphasis level="strong">终身监禁</emphasis>的银行家
  </prosody>
  <break time="350ms"/>

  <!-- 高潮揭示：语速放缓，制造期待 -->
  <prosody rate="0.85" pitch="-1st">
    如何用<break time="200ms"/>20年时间
  </prosody>
  <break time="400ms"/>

  <!-- 钩子收尾：语调上扬，重音在"隧道" -->
  <prosody rate="1.0" pitch="+2st">
    挖出一条<emphasis level="moderate">隧道</emphasis>？
  </prosody>
  <break time="800ms"/>
</speak>
```

### 4.3 narrator-ai `<#x#>` 停顿语法与 SSML 的互转

```python
# narrator-ai 独创的 <#x#> 停顿语法 ←→ 标准 SSML 互转

class PauseSyntaxConverter:
    """停顿语法转换器"""

    @staticmethod
    def narrator_to_ssml(text: str) -> str:
        """将 narrator-ai 的 <#x.x#> 转换为标准 SSML <break>"""
        import re

        def replace_pause(match):
            seconds = float(match.group(1))
            ms = int(seconds * 1000)
            return f'<break time="{ms}ms"/>'

        return re.sub(r'<#(\d+\.?\d*)#>', replace_pause, text)

    @staticmethod
    def ssml_to_narrator(ssml: str) -> str:
        """将标准 SSML <break> 转换为 narrator-ai 的 <#x.x#>"""
        import re

        def replace_break(match):
            time_str = match.group(1)
            # 解析 "500ms" 或 "1.2s" 格式
            if 'ms' in time_str:
                seconds = float(time_str.replace('ms', '')) / 1000
            else:
                seconds = float(time_str.replace('s', ''))
            return f'<#{seconds:.1f}#>'

        return re.sub(r'<break time="([^"]+)"\s*/>', replace_break, ssml)

# 示例：
# 输入:  "你有没有<#0.5#>想过<#0.3#>这件事？"
# 输出:  "你有没有<break time="500ms"/>想过<break time="300ms"/>这件事？"
```

### 4.4 TTS 引擎选型与路由

```python
class TTSRouter:
    """TTS 引擎智能路由 —— 质量/成本/延迟 三角平衡"""

    ENGINES = {
        "narrator-ai": {
            "type": "api",
            "voices": 63,
            "languages": 11,
            "pause_syntax": "narrator",     # 支持 <#x#>
            "emotion_control": "basic",     # SSML prosody
            "voice_clone": True,            # 30s 样本
            "cost_per_minute": 0.15,        # ¥
            "latency_ratio": 1.2,           # 实时倍率
            "quality_score": 8.0,
            "best_for": "影视解说（风格最匹配）"
        },
        "cosyvoice2": {
            "type": "self-hosted",
            "voices": "zero-shot clone",
            "languages": ["zh", "en"],
            "pause_syntax": "ssml",
            "emotion_control": "basic",
            "voice_clone": True,            # 零样本！
            "cost_per_minute": 0.0,         # 自部署，边际成本接近零
            "latency_ratio": 0.8,
            "quality_score": 7.5,
            "best_for": "高频批量 + 语音克隆（零边际成本）"
        },
        "elevenlabs": {
            "type": "api",
            "voices": 1000+,
            "languages": 29,
            "pause_syntax": "ssml",
            "emotion_control": "advanced",  # 情绪标注支持最好
            "voice_clone": True,
            "cost_per_minute": 0.50,        # ¥（最贵）
            "latency_ratio": 1.5,
            "quality_score": 9.0,
            "best_for": "最高质量要求 / 情绪表达复杂场景"
        },
        "edge-tts": {
            "type": "free",
            "voices": 400+,
            "languages": 50+,
            "pause_syntax": "ssml",
            "emotion_control": "none",
            "voice_clone": False,
            "cost_per_minute": 0.0,
            "latency_ratio": 0.5,
            "quality_score": 6.0,
            "best_for": "MVP 快速验证 / 草稿预览"
        }
    }

    def route(self, task: dict) -> str:
        """根据任务需求自动选择最佳 TTS 引擎"""
        # 决策逻辑
        if task["priority"] == "quality":
            return "elevenlabs"
        elif task["voice_clone"] and task["budget"] == "low":
            return "cosyvoice2"
        elif task["style"] in ["热血动作", "烧脑悬疑", "爆笑喜剧"]:
            return "narrator-ai"  # narrator-ai 的解说风格匹配最好
        elif task["mode"] == "preview":
            return "edge-tts"      # 预览用免费的
        else:
            return "narrator-ai"   # 默认
```

---

## 5. 视觉模板与组装引擎

### 5.1 视觉模板系统

```
核心思路（来自 B站解说视频实际构成分析）：
  70% 的画面可以用预设模板覆盖，不需要原片素材
  让这 70% 的"非原片画面"看起来专业、统一、有品牌感

┌──────────────────────────────────────────────────────────────────┐
│                    视觉模板系统                                    │
│                                                                  │
│  ┌────────────────────────────────────────────────────────────┐  │
│  │ 模板 A：剧照卡片                                            │  │
│  │                                                            │  │
│  │  ┌──────────────────────────┐                              │  │
│  │  │                          │                              │  │
│  │  │    [电影剧照·模糊背景]     │                              │  │
│  │  │                          │                              │  │
│  │  │   ┌─────────────────┐    │                              │  │
│  │  │   │                 │    │                              │  │
│  │  │   │  核心台词/标题    │    │                              │  │
│  │  │   │                 │    │                              │  │
│  │  │   └─────────────────┘    │                              │  │
│  │  │                          │                              │  │
│  │  └──────────────────────────┘                              │  │
│  │  适用：剧情引入、关键情节点题、情绪转场                      │  │
│  │  参数：背景图片 URL、文字内容、字体大小、毛玻璃程度、动画效果  │  │
│  └────────────────────────────────────────────────────────────┘  │
│                                                                  │
│  ┌────────────────────────────────────────────────────────────┐  │
│  │ 模板 B：分屏对比                                            │  │
│  │                                                            │  │
│  │  ┌──────────┐    ┌──────────┐                              │  │
│  │  │          │    │          │                              │  │
│  │  │  角色 A   │ VS │  角色 B   │                              │  │
│  │  │          │    │          │                              │  │
│  │  │  "希望"   │    │ "绝望"    │                              │  │
│  │  │          │    │          │                              │  │
│  │  └──────────┘    └──────────┘                              │  │
│  │  适用：对立关系、冲突升级、选择时刻                           │  │
│  └────────────────────────────────────────────────────────────┘  │
│                                                                  │
│  ┌────────────────────────────────────────────────────────────┐  │
│  │ 模板 C：时间线递进                                          │  │
│  │                                                            │  │
│  │  [事件 1] ────→ [事件 2] ────→ [事件 3]                    │  │
│  │    入狱           适应           越狱                        │  │
│  │                                                            │  │
│  │  适用：剧情推进、因果链条、时间跨度大的叙事                   │  │
│  └────────────────────────────────────────────────────────────┘  │
│                                                                  │
│  ┌────────────────────────────────────────────────────────────┐  │
│  │ 模板 D：情绪卡片                                            │  │
│  │                                                            │  │
│  │  ┌──────────────────────────┐                              │  │
│  │  │                          │                              │  │
│  │  │       😱 震惊！           │                              │  │
│  │  │                          │                              │  │
│  │  │   原来凶手一直在身边      │                              │  │
│  │  │                          │                              │  │
│  │  └──────────────────────────┘                              │  │
│  │  适用：情绪转折、关键揭示、评论观点                           │  │
│  └────────────────────────────────────────────────────────────┘  │
│                                                                  │
│  ┌────────────────────────────────────────────────────────────┐  │
│  │ 模板 E：字幕动画（抖音/快手风格）                            │  │
│  │                                                            │  │
│  │  逐字弹出 / 卡拉OK高亮 / 关键词语义着色                      │  │
│  │  适用：强钩子段、核心金句、结尾升华                           │  │
│  └────────────────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────────────────┘
```

### 5.2 视觉模板参数化配置

```typescript
// 视觉模板的标准化参数接口

interface VisualTemplateConfig {
  templateId: string
  // 基础画布
  canvas: {
    width: number        // 1080 (抖音竖屏) / 1920 (B站横屏)
    height: number       // 1920 / 1080
    backgroundColor: string
  }

  // 背景层
  background: {
    type: 'image' | 'gradient' | 'solid' | 'blurred_poster'
    imageUrl?: string
    blurRadius?: number       // 毛玻璃模糊程度 (px)
    gradientColors?: string[] // 渐变色
    opacity?: number
  }

  // 前景文字层
  textLayers: Array<{
    content: string           // 文字内容
    fontSize: number
    fontFamily: string
    color: string
    position: { x: number; y: number }  // 百分比定位
    alignment: 'left' | 'center' | 'right'
    animation: {
      type: 'fadeIn' | 'slideUp' | 'typewriter' | 'scaleIn' | 'none'
      duration: number        // ms
      delay: number           // ms
    }
    highlight?: {             // 关键词高亮
      words: string[]
      color: string
      style: 'bold' | 'colored' | 'underline'
    }
  }>

  // 装饰元素
  decorations?: Array<{
    type: 'border' | 'icon' | 'divider' | 'watermark'
    style: Record<string, string | number>
  }>

  // 持续时间
  duration: number            // 秒
}
```

### 5.3 声明式视频组装语言（VDL）

```typescript
// VDL (Video Description Language) —— 声明式视频描述
// 借鉴 Pixelle-Video 的 JSON pipeline 设计 + Remotion 的组件化思路

interface VDLDocument {
  version: '1.0'
  metadata: {
    title: string
    movieName: string
    style: string
    platform: 'douyin' | 'bilibili' | 'kuaishou' | 'xiaohongshu'
    totalDuration: number
  }
  canvas: {
    width: number
    height: number
    fps: number
  }

  // 全局样式（字幕、转场等默认样式）
  defaults: {
    subtitleStyle: SubtitleStyle
    transition: TransitionConfig
    bgmVolume: number
    ttsVolume: number
  }

  // 分段时间线
  segments: VDLSegment[]
}

interface VDLSegment {
  index: number
  startTime: number           // 在视频中的开始时间（秒）
  duration: number            // 持续时长

  // 音频层
  audio: {
    tts: {
      engine: 'narrator-ai' | 'cosyvoice2' | 'elevenlabs'
      voiceId: string
      ssml: string             // SSML 标注
      volume: number
    }
    bgm?: {
      source: 'library' | 'suno'
      trackId?: string         // 素材库曲目 ID
      emotion?: string         // Suno 情绪描述
      startOffset: number      // 从 BGM 的哪个位置开始播
      volume: number
      fadeIn: number
      fadeOut: number
    }
    originalAudio?: {
      source: 'movie_clip'
      timeRange: [number, number]
      volume: number
      mode: 'silent' | 'mixed' | 'full'  // OST 模式
    }
  }

  // 视频层
  video: {
    primary: {
      source: 'movie_clip' | 'visual_template' | 'ai_generated' | 'stock'
      // 素材剪辑
      clipRef?: {
        movieId: string
        timeRange: [number, number]
        effects?: VideoEffect[]
      }
      // 视觉模板
      templateId?: string
      templateConfig?: VisualTemplateConfig
      // AI 生成
      aiGeneration?: {
        engine: 'kling' | 'seedance'
        prompt: string
        duration: number
      }
    }
    overlay?: {
      type: 'subtitle' | 'watermark' | 'sticker' | 'emoji'
      config: Record<string, unknown>
    }
  }

  // 转场（进入当前段落的过渡效果）
  transition: {
    type: 'cut' | 'dissolve' | 'fade' | 'slide' | 'zoom'
    duration: number          // ms
  }
}
```

### 5.4 VDL → FFmpeg 编译器

```python
# VDL 编译器：将声明式 VDL 文档编译为 FFmpeg filter_complex 图

class VDLCompiler:
    """VDL → FFmpeg filter_complex 编译器"""

    def compile(self, vdl: VDLDocument) -> FFmpegCommand:
        """编译 VDL 文档为 FFmpeg 执行命令"""
        filter_parts = []
        inputs = []

        for seg in vdl.segments:
            # 1. 视频输入
            video_input = self._resolve_video_input(seg.video.primary)
            inputs.append(video_input)

            # 2. 音频输入
            audio_inputs = self._resolve_audio_inputs(seg.audio)
            inputs.extend(audio_inputs)

            # 3. 滤镜链
            filter_chain = self._build_filter_chain(
                seg,
                video_input_index=len(inputs) - len(audio_inputs) - 1,
                audio_input_indices=[...]
            )
            filter_parts.append(filter_chain)

        # 4. 拼接所有片段
        concat_filter = self._build_concat(filter_parts)

        # 5. 输出
        return FFmpegCommand(
            inputs=inputs,
            filter_complex=concat_filter,
            output_options={
                "c:v": "libx264",
                "preset": "medium",
                "crf": "18",
                "c:a": "aac",
                "b:a": "192k",
            }
        )

    def _build_filter_chain(
        self, seg: VDLSegment, vid_idx: int, aud_indices: list[int]
    ) -> str:
        """为单个段落构建 FFmpeg 滤镜链"""
        filters = []

        # 画面处理
        if seg.video.primary.source == "visual_template":
            # 用 Canvas 预渲染为 PNG 序列或 MP4
            # 然后在此处引用
            filters.append(f"[{vid_idx}:v] trim=... setpts=... [v{seg.index}]")
        elif seg.video.primary.source == "movie_clip":
            cr = seg.video.primary.clipRef
            start, end = cr.timeRange
            filters.append(
                f"[{vid_idx}:v] "
                f"trim=start={start}:end={end}, "
                f"setpts=PTS-STARTPTS, "
                f"scale={vdl.canvas.width}:{vdl.canvas.height}:force_original_aspect_ratio=decrease, "
                f"pad={vdl.canvas.width}:{vdl.canvas.height}:(ow-iw)/2:(oh-ih)/2 "
                f"[v{seg.index}]"
            )

        # 转场
        if seg.transition.type != "cut":
            filters.append(
                f"[v{seg.index}] "
                f"fade=t=in:d={seg.transition.duration/1000} "
                f"[v{seg.index}_transitioned]"
            )

        return "; ".join(filters)
```

---

## 6. BGM 自动匹配与混音

### 6.1 智能匹配架构

```
┌──────────────────────────────────────────────────────────────────┐
│                    BGM 自动匹配引擎                                │
│                                                                  │
│  文案情绪标签序列：                                                │
│  [suspense] → [buildup] → [tense] → [revelation] → [climax]      │
│       │           │          │           │            │          │
│       ▼           ▼          ▼           ▼            ▼          │
│  ┌──────────────────────────────────────────────────────────┐    │
│  │                   情绪→BGM 映射表                          │    │
│  │                                                          │    │
│  │  suspense   → BGM-027 (紧张电子) / BGM-089 (心跳)        │    │
│  │  buildup    → BGM-034 (渐强弦乐) / BGM-056 (钢琴铺底)    │    │
│  │  tense      → BGM-041 (鼓点渐强) / BGM-112 (电子氛围)    │    │
│  │  revelation → BGM-018 (管弦释放) / BGM-073 (钢琴华彩)    │    │
│  │  climax     → BGM-005 (史诗交响) / BGM-066 (电子高潮)    │    │
│  │  reflection → BGM-022 (钢琴独奏) / BGM-091 (吉他叙事)    │    │
│  └──────────────────────────────────────────────────────────┘    │
│                            │                                     │
│                            ▼                                     │
│  ┌──────────────────────────────────────────────────────────┐    │
│  │                   BGM 切点规划器                           │    │
│  │                                                          │    │
│  │  对每段 BGM：                                             │    │
│  │    1. 查找该 BGM 的预标注切点（自然小节结尾）              │    │
│  │    2. 计算配音覆盖时长 → 决定 BGM 的起止点                │    │
│  │    3. 生成交叉淡化计划（前一段 BGM fade_out 与后一段       │    │
│  │       fade_in 重叠 2 秒）                                 │    │
│  │    4. 检查相邻 BGM 的调性/BPM 是否冲突 → 如需调整          │    │
│  └──────────────────────────────────────────────────────────┘    │
└──────────────────────────────────────────────────────────────────┘
```

### 6.2 BGM 预标注数据结构

```python
# BGM 素材预标注 —— 这是自动匹配能跑起来的前提

@dataclass
class BGMTrackMetadata:
    """BGM 曲目元数据（人工标注一次，自动匹配终身受用）"""
    track_id: str
    title: str
    duration: float

    # 情绪标签（多标签）
    emotions: list[str]          # ["suspense", "tense", "dark"]

    # 音乐特征
    bpm: int                     # 节拍速度
    key: str                     # 调性 "C minor"
    energy: float                # 能量 0-1
    instruments: list[str]       # ["piano", "strings", "electronic"]

    # 结构标注（关键！决定自然切出的位置）
    sections: list[dict]         # [
                                 #   {"start": 0, "end": 8.5, "type": "intro"},
                                 #   {"start": 8.5, "end": 32.0, "type": "main"},
                                 #   {"start": 32.0, "end": 45.0, "type": "climax"},
                                 #   {"start": 45.0, "end": 52.0, "type": "outro"}
                                 # ]

    # 自然切出点（小节/乐句结尾，可以在此处自然切出而不显突兀）
    natural_cut_points: list[float]  # [8.5, 16.0, 24.0, 32.0, 40.5, 45.5, 52.0]

    # 适用场景
    usage: list[str]             # ["hook", "buildup", "climax", "ending"]

    # 授权信息
    license: str                 # "cc0" | "licensed" | "suno_generated"
```

### 6.3 BGM 混音计划生成

```python
class BGMMixPlanner:
    """BGM 混音计划生成器 —— 借鉴 NarratoAI 的 OST 三模式"""

    def plan(
        self,
        segments: list,           # 文案段落 + 情绪标签
        tts_durations: list[float], # 每段配音实际时长
        ost_mode: int = 0         # 0=纯配音, 1=纯原声, 2=混合
    ) -> BGMMixPlan:
        """生成 BGM 混音计划"""

        mix_plan = BGMMixPlan()
        current_bgm = None

        for i, seg in enumerate(segments):
            # 1. 根据情绪标签匹配 BGM
            candidates = self.bgm_library.search(
                emotion=seg.emotion,
                bpm_range=None,     # 不限 BPM
                duration_min=tts_durations[i]
            )

            best_bgm = candidates[0]  # 取最佳匹配

            # 2. 决定是否需要切换 BGM
            if current_bgm and current_bgm.track_id == best_bgm.track_id:
                # 继续使用当前 BGM（相邻段情绪相同）
                crossfade = False
            elif current_bgm:
                # 需要切换 BGM → 计算交叉淡化
                crossfade = True
                fade_out_start = segments[i]["start_time"] - 2.0  # 提前 2s 开始淡出
                fade_in_end = segments[i]["start_time"] + 2.0      # 2s 内淡入完成

            # 3. 找到自然切出点
            cut_point = self._find_nearest_cut_point(
                best_bgm,
                target_time=tts_durations[i]
            )

            # 4. 确定 BGM 播放区间
            mix_plan.add_track(
                segment_index=i,
                track_id=best_bgm.track_id,
                play_start=best_bgm.sections[0]["start"],  # 从头播
                play_end=cut_point,                        # 自然切出点
                volume=0.3,                                # BGM 默认 30% 音量
                fade_in=1.0 if i == 0 else (2.0 if crossfade else 0),
                fade_out=2.0,
                tts_ducking=True                          # TTS 时 BGM 自动降低
            )

            current_bgm = best_bgm

        return mix_plan

    def _find_nearest_cut_point(self, bgm, target_time: float) -> float:
        """找到最接近目标时长的自然切出点"""
        cut_points = bgm.metadata.natural_cut_points
        # 找 >= target_time 的最近切点
        for cp in cut_points:
            if cp >= target_time:
                return cp
        return cut_points[-1]  # 兜底：最后一切点
```

---

## 7. 多平台自适应引擎

### 7.1 不止是"格式转换"，而是"语体翻译"

```
关键洞察（来自 B站/抖音/快手实际解说内容对比分析）：

  不同平台的解说视频差异，核心不是分辨率/时长/字幕大小
  而是完全不同的"话语体系"和"语体风格"

  ┌──────────┬──────────────────┬──────────────────┬──────────────────┐
  │ 平台     │ 抖音              │ B站               │ 快手              │
  ├──────────┼──────────────────┼──────────────────┼──────────────────┤
  │ 语体     │ "家人们/宝子们"    │ "兄弟们/各位观众"  │ "老铁们"          │
  │ 开场风格 │ 强hook + 信息差   │ 背景铺垫 + 深度   │ 接地气 + 亲切感   │
  │ 语气     │ 激情/夸张         │ 理性/深度          │ 自然/真实         │
  │ 热梗密度 │ 高（紧跟热点）    │ 中（二次元梗）     │ 中（社会梗）      │
  │ 信息深度 │ 浅（3分钟讲完）   │ 深（15分钟挖透）   │ 浅（3分钟核心）   │
  │ 结尾     │ "关注我下期更精彩"│ "求三连"          │ "觉得好的双击"   │
  └──────────┴──────────────────┴──────────────────┴──────────────────┘
```

### 7.2 平台适配 Pipeline

```python
class PlatformAdapter:
    """多平台自适应引擎 —— 不只是格式转换，而是语体翻译"""

    PLATFORM_CONFIGS = {
        "douyin": {
            "display_name": "抖音",
            "duration_range": (60, 180),       # 秒
            "hook_window": 3,                  # 前 3 秒必须有强钩子
            "aspect_ratio": (9, 16),
            "resolution": (1080, 1920),
            "speech_rate": 1.15,               # 语速偏快
            "subtitle_style": "large_keyword_highlight",  # 大字幕+关键词高亮
            "max_words": 600,
            "style_params": {
                "opening_tone": "aggressive_hook",    # 强钩子开场
                "address_term": "家人们",             # 称呼方式
                "closing": "关注我，下期更精彩",       # 结尾话术
                "slang_density": 0.8,                # 网络用语密度
                "sentence_length": "short",           # 短句为主
            }
        },
        "bilibili": {
            "display_name": "B站",
            "duration_range": (180, 900),       # 5-15 分钟
            "hook_window": 15,                  # 前 15 秒信息密度
            "aspect_ratio": (16, 9),
            "resolution": (1920, 1080),
            "speech_rate": 1.0,                 # 正常语速
            "subtitle_style": "standard_with_notes",  # 标准字幕+注释
            "max_words": 3000,
            "style_params": {
                "opening_tone": "informative_hook",   # 信息型开场
                "address_term": "各位观众",
                "closing": "如果喜欢这个视频，记得一键三连",
                "slang_density": 0.4,
                "sentence_length": "mixed",
            }
        },
        "kuaishou": {
            "display_name": "快手",
            "duration_range": (60, 180),
            "hook_window": 3,
            "aspect_ratio": (9, 16),
            "resolution": (1080, 1920),
            "speech_rate": 1.1,
            "subtitle_style": "colloquial_large",
            "max_words": 600,
            "style_params": {
                "opening_tone": "down_to_earth",      # 接地气开场
                "address_term": "老铁们",
                "closing": "觉得好的给老弟来个双击",
                "slang_density": 0.7,
                "sentence_length": "short",
            }
        },
        "xiaohongshu": {
            "display_name": "小红书",
            "duration_range": (60, 300),
            "hook_window": 5,
            "aspect_ratio": (3, 4),
            "resolution": (1080, 1440),
            "speech_rate": 0.9,                 # 偏慢，娓娓道来
            "subtitle_style": "literary_elegant",
            "max_words": 1000,
            "style_params": {
                "opening_tone": "emotional_resonance",  # 情感共鸣开场
                "address_term": "姐妹们/宝子们",
                "closing": "你觉得呢？评论区聊聊吧",
                "slang_density": 0.5,
                "sentence_length": "medium",
            }
        }
    }

    def adapt_script(
        self, base_script: dict, target_platform: str
    ) -> dict:
        """将基础文案适配到目标平台

        核心逻辑：
        1. 调用 LLM 做"语体翻译"——不只是缩写，而是改变话语体系
        2. 调整停顿分布和语速
        3. 适配钩子策略
        4. 替换平台特定话术（称呼/结尾）
        """
        config = self.PLATFORM_CONFIGS[target_platform]

        # LLM 语体翻译 prompt
        prompt = f"""
        你是一位{config['display_name']}平台的资深影视解说博主。
        请将以下基础解说文案改写为适合{config['display_name']}平台的版本。

        改写要求：
        - 时长控制在 {config['duration_range'][0]}-{config['duration_range'][1]} 秒
        - 开场必须在 {config['hook_window']} 秒内建立钩子
        - 称呼用户为"{config['style_params']['address_term']}"
        - 结尾使用"{config['style_params']['closing']}"风格
        - 网络用语密度：{config['style_params']['slang_density']}（0-1）
        - 语速参数：{config['speech_rate']}x
        - 字数上限：{config['max_words']}

        原始文案：
        {base_script['text']}

        请输出改写后的完整文案（含 SSML 标注和情绪标签）。
        """

        adapted = self.llm.generate(prompt)

        # 调整画面参数
        adapted["canvas"] = {
            "width": config["resolution"][0],
            "height": config["resolution"][1]
        }
        adapted["subtitle_style"] = config["subtitle_style"]

        return adapted

    def batch_adapt(
        self, base_script: dict, platforms: list[str]
    ) -> dict[str, dict]:
        """一键适配多平台 —— 并行生成"""
        results = {}
        for platform in platforms:
            results[platform] = self.adapt_script(base_script, platform)
        return results
```

---

## 8. 编排决策引擎

### 8.1 为什么需要编排决策引擎而非纯粹的工作流

```
Temporal 工作流的角色：执行者
  "按顺序执行步骤 1→2→3→4→5→6，每步完成后暂停等用户确认"

编排决策引擎的角色：决策者
  "步骤 1 完成，质量评分 92 → 自动继续步骤 2"
  "步骤 2 完成，质量评分 55 → 自动重试（换角度），不打扰用户"
  "步骤 3 完成，质量评分 78 → 暂停，标记'建议审阅'，但不强制"
  "用户连续 3 次修改同一段 → 学习修改模式 → 应用到后续段落"

本质区别：
  工作流引擎 = 硬编码的 if-else
  编排决策引擎 = 基于质量指标的动态路由 + 用户行为学习
```

### 8.2 决策规则引擎

```python
class OrchestrationDecisionEngine:
    """编排决策引擎 —— 每步完成后自动决定下一步"""

    # 质量阈值配置（可热更新，可 A/B 测试）
    thresholds = {
        "script_quality": {
            "auto_continue": 85,     # >= 85 分 → 自动继续
            "suggest_review": 65,    # 65-84 分 → 标记建议审阅
            "auto_retry": 0,         # < 65 分 → 自动重写（换角度）
        },
        "scene_match_rate": {
            "auto_continue": 0.70,   # >= 70% 匹配率 → 正常合成
            "use_templates": 0.40,   # 40-70% → 启用视觉模板替代
            "downgrade_mode": 0.0,   # < 40% → 降级为纯剧照模式
        },
        "voice_quality": {
            "auto_continue": 80,
            "suggest_retry": 60,
        }
    }

    def decide_after_script_generation(
        self, quality_report: dict, user_history: list
    ) -> OrchestrationDecision:
        """文案生成后的决策"""

        overall_score = quality_report["overall_score"]

        if overall_score >= self.thresholds["script_quality"]["auto_continue"]:
            return OrchestrationDecision(
                action="auto_continue",
                next_stage="voice_generation",
                message=f"文案质量 {overall_score} 分，自动进入配音阶段"
            )

        elif overall_score >= self.thresholds["script_quality"]["suggest_review"]:
            # 检查用户偏好
            if user_history.get("prefers_auto_mode"):
                return OrchestrationDecision(
                    action="auto_continue",
                    next_stage="voice_generation",
                    message=f"文案质量 {overall_score} 分，按偏好自动继续"
                )
            else:
                return OrchestrationDecision(
                    action="wait_for_review",
                    next_stage=None,
                    message=f"文案已生成（{overall_score} 分），建议审阅",
                    review_highlights=self._get_review_highlights(quality_report)
                )

        else:  # < 65 分
            return OrchestrationDecision(
                action="auto_retry",
                next_stage="script_generation",
                message=f"文案质量不足（{overall_score} 分），自动换个角度重写",
                retry_params={"change_angle": True, "previous_angles": quality_report["angles_tried"]}
            )

    def decide_after_scene_matching(
        self, match_report: dict
    ) -> OrchestrationDecision:
        """画面匹配后的决策"""

        match_rate = match_report["overall_match_rate"]

        if match_rate >= self.thresholds["scene_match_rate"]["auto_continue"]:
            return OrchestrationDecision(
                action="auto_continue",
                next_stage="video_composition",
                composition_mode="clip_priority",  # 素材优先
                message=f"画面匹配率 {match_rate:.0%}，正常合成"
            )

        elif match_rate >= self.thresholds["scene_match_rate"]["use_templates"]:
            return OrchestrationDecision(
                action="auto_continue",
                next_stage="video_composition",
                composition_mode="hybrid",  # 素材 + 模板混合
                template_replacements=self._get_template_assignments(match_report),
                message=f"画面匹配率 {match_rate:.0%}，启用视觉模板补充"
            )

        else:
            return OrchestrationDecision(
                action="auto_continue",
                next_stage="video_composition",
                composition_mode="template_only",  # 纯模板模式
                message=f"画面匹配率 {match_rate:.0%}，降级为纯剧照+文字模式"
            )

    def learn_from_user_edits(
        self, original_segment: dict, user_edited_segment: dict, edit_count: int
    ) -> dict:
        """学习用户的修改模式"""
        if edit_count < 3:
            return {}

        # 分析修改类型
        edit_patterns = self._analyze_edit_diff(original_segment, user_edited_segment)

        # 更新用户偏好模型
        return {
            "learned_preferences": edit_patterns,
            "apply_to_remaining_segments": edit_count >= 3,
            "confidence": min(0.3 + edit_count * 0.1, 0.9)
        }


@dataclass
class OrchestrationDecision:
    action: str              # "auto_continue" | "wait_for_review" | "auto_retry"
    next_stage: str | None
    message: str
    composition_mode: str = "clip_priority"
    retry_params: dict | None = None
    review_highlights: list[str] | None = None
    template_replacements: list | None = None
```

### 8.3 Temporal 工作流集成

```python
# Temporal Workflow + OrchestrationDecisionEngine 的协作

@workflow.defn
class MovieNarrationWorkflow:
    """电影解说一键出片工作流"""

    @workflow.run
    async def run(self, params: NarrationParams) -> NarrationResult:
        decision_engine = OrchestrationDecisionEngine()

        # Stage 1: 文案生成
        script_result = await workflow.execute_activity(
            generate_script,
            params,
            start_to_close_timeout=timedelta(minutes=5)
        )

        # → 决策引擎评估
        decision = decision_engine.decide_after_script_generation(
            script_result.quality_report,
            user_history=params.user_history
        )

        if decision.action == "auto_retry":
            # 自动重写
            script_result = await workflow.execute_activity(
                generate_script,
                {**params, **decision.retry_params},
                start_to_close_timeout=timedelta(minutes=5)
            )
        elif decision.action == "wait_for_review":
            # 暂停工作流，等待用户审阅
            await workflow.wait_for_signal("user_review_complete")
            script_result = await workflow.execute_activity(
                get_user_approved_script,
                params.project_id
            )

        # Stage 2: 画面匹配
        match_result = await workflow.execute_activity(
            match_scenes,
            MatchSceneParams(
                script=script_result,
                movie_id=params.movie_id,
                use_marengo=params.feature_flags.get("marengo_3.0", False)
            ),
            start_to_close_timeout=timedelta(minutes=10)
        )

        decision = decision_engine.decide_after_scene_matching(match_result)

        # Stage 3 & 4: 配音 + BGM（并行）
        voice_task = workflow.execute_activity(
            generate_voice,
            VoiceParams(script=script_result, voice_id=params.voice_id),
            start_to_close_timeout=timedelta(minutes=5)
        )

        bgm_task = workflow.execute_activity(
            plan_bgm,
            BGMParams(script=script_result),
            start_to_close_timeout=timedelta(minutes=3)
        )

        voice_result, bgm_result = await asyncio.gather(voice_task, bgm_task)

        # Stage 5: 视频合成
        composition_result = await workflow.execute_activity(
            compose_video,
            ComposeParams(
                script=script_result,
                match_plan=match_result,
                voice=voice_result,
                bgm=bgm_result,
                mode=decision.composition_mode
            ),
            start_to_close_timeout=timedelta(minutes=15)
        )

        # Stage 6: 自动质检
        qc_result = await workflow.execute_activity(
            quality_check,
            QCParams(video_path=composition_result.output_path),
            start_to_close_timeout=timedelta(minutes=3)
        )

        if not qc_result.passed:
            # 自动修复
            composition_result = await workflow.execute_activity(
                auto_fix,
                FixParams(
                    video_path=composition_result.output_path,
                    issues=qc_result.issues
                )
            )

        return NarrationResult(
            video_path=composition_result.output_path,
            script=script_result,
            quality_report=qc_result,
            total_time=workflow.now() - workflow.start_time
        )
```

---

## 9. Remotion Video-as-Code 方案

### 9.1 为什么考虑 Remotion

```
传统 FFmpeg 方案的痛点：
  - 复杂的 filter_complex 图难以调试
  - 动画/特效/转场用 FFmpeg 滤镜拼接极其痛苦
  - 修改一个参数要重新渲染整个视频
  - 非开发人员完全无法理解和修改

Remotion "Video as Code" 方案的突破（2026）：
  - LLM 可以直接输出 JSX 代码（已验证：video-as-code-for-agents）
  - React 组件天然支持动画/特效/转场
  - 组件化：视觉模板 = 一个 React 组件
  - @remotion/web-renderer：浏览器端出片（无需服务器）
  - 修改参数 = 修改 props，即时预览
```

### 9.2 LLM → Remotion 代码生成

```typescript
// LLM 直接生成 Remotion 视频代码（Video-as-Code 范式）

// 这是 LLM 根据解说文案自动生成的视频组件
// 参考：remotion-ad-video-skill 和 video-as-code-for-agents

import { AbsoluteFill, Sequence, useCurrentFrame, useVideoConfig,
         interpolate, spring, Audio, Img, OffthreadVideo } from "remotion"

// ============================================================
// 全局配置（LLM 根据平台参数自动填充）
// ============================================================
const CANVAS = {
  douyin:  { width: 1080, height: 1920, fps: 30 },
  bilibili: { width: 1920, height: 1080, fps: 30 },
}

// ============================================================
// 视觉模板组件（每个模板是一个 React 组件）
// ============================================================

// 模板 A：剧照卡片
const PhotoCard: React.FC<{
  imageUrl: string
  title: string
  subtitle?: string
  blurRadius?: number
}> = ({ imageUrl, title, subtitle, blurRadius = 20 }) => {
  const frame = useCurrentFrame()
  const fadeIn = spring({ frame, fps: 30, config: { damping: 20 } })

  return (
    <AbsoluteFill>
      {/* 模糊背景 */}
      <Img
        src={imageUrl}
        style={{
          width: '100%', height: '100%', objectFit: 'cover',
          filter: `blur(${blurRadius}px) brightness(0.4)`,
          transform: `scale(${1 + interpolate(fadeIn, [0, 1], [0.1, 0])})`
        }}
      />
      {/* 文字层 */}
      <div style={{
        position: 'absolute', inset: 0,
        display: 'flex', flexDirection: 'column',
        justifyContent: 'center', alignItems: 'center',
        opacity: fadeIn
      }}>
        <h1 style={{
          fontSize: 72, fontWeight: 'bold', color: '#fff',
          textShadow: '0 4px 20px rgba(0,0,0,0.5)',
          textAlign: 'center', maxWidth: '80%'
        }}>
          {title}
        </h1>
        {subtitle && (
          <p style={{
            fontSize: 36, color: 'rgba(255,255,255,0.8)',
            marginTop: 24
          }}>
            {subtitle}
          </p>
        )}
      </div>
    </AbsoluteFill>
  )
}

// 模板 D：情绪卡片
const EmotionCard: React.FC<{
  emotion: string
  emoji: string
  text: string
  color: string
}> = ({ emotion, emoji, text, color }) => {
  const frame = useCurrentFrame()
  const scale = spring({ frame, fps: 30, config: { mass: 0.5 } })

  return (
    <AbsoluteFill style={{
      background: `linear-gradient(135deg, ${color}22, ${color}44)`,
      justifyContent: 'center', alignItems: 'center'
    }}>
      <div style={{
        transform: `scale(${scale})`,
        textAlign: 'center'
      }}>
        <div style={{ fontSize: 120 }}>{emoji}</div>
        <h2 style={{ fontSize: 64, color, marginTop: 20 }}>{emotion}</h2>
        <p style={{ fontSize: 36, color: '#fff', marginTop: 16, maxWidth: '70%' }}>
          {text}
        </p>
      </div>
    </AbsoluteFill>
  )
}

// 字幕组件（卡拉OK高亮 + 逐字动画）
const AnimatedSubtitle: React.FC<{
  text: string
  highlightWords: string[]
  startFrame: number
}> = ({ text, highlightWords, startFrame }) => {
  const frame = useCurrentFrame()
  const localFrame = frame - startFrame
  const words = text.split('')

  return (
    <div style={{
      position: 'absolute', bottom: 120, left: 0, right: 0,
      display: 'flex', justifyContent: 'center', flexWrap: 'wrap',
      gap: 8, padding: '0 60px'
    }}>
      {words.map((char, i) => {
        const charDelay = i * 2
        const opacity = interpolate(localFrame - charDelay, [0, 5], [0, 1], {
          extrapolateRight: 'clamp'
        })
        const isHighlighted = highlightWords.some(w => text.includes(w) && i >= text.indexOf(w) && i < text.indexOf(w) + w.length)

        return (
          <span key={i} style={{
            fontSize: 42, fontWeight: isHighlighted ? 'bold' : 'normal',
            color: isHighlighted ? '#FFD700' : '#fff',
            opacity,
            textShadow: '0 2px 8px rgba(0,0,0,0.8)'
          }}>
            {char}
          </span>
        )
      })}
    </div>
  )
}

// ============================================================
// 主视频组件（LLM 自动生成整个视频结构）
// ============================================================
export const ShawshankNarration: React.FC<{
  platform: 'douyin' | 'bilibili'
}> = ({ platform = 'douyin' }) => {
  const canvas = CANVAS[platform]
  const fps = canvas.fps

  // 时长计算（由 TTS 实际音频时长决定）
  const SEGMENTS = [
    { type: 'hook',     startSec: 0,    durationSec: 12.5, template: 'emotion' },
    { type: 'intro',    startSec: 12.5, durationSec: 22.0, template: 'photo_card' },
    { type: 'plot_1',   startSec: 34.5, durationSec: 28.0, template: 'clip' },
    { type: 'twist',    startSec: 62.5, durationSec: 20.0, template: 'clip' },
    { type: 'plot_2',   startSec: 82.5, durationSec: 25.0, template: 'clip' },
    { type: 'climax',   startSec: 107.5, durationSec: 22.0, template: 'clip' },
    { type: 'ending',   startSec: 129.5, durationSec: 15.0, template: 'photo_card' },
  ]

  // 转场配置
  const TRANSITIONS = {
    dissolve: { from: 'dissolve', to: 'dissolve', duration: 0.5 },
    zoom: { from: 'zoom', to: 'zoom', duration: 0.3 },
  }

  return (
    <AbsoluteFill style={{ backgroundColor: '#000' }}>
      {/* ===== 音频轨道 ===== */}
      {/* TTS 配音（整段音频） */}
      <Audio src="/audio/shawshank-narration-tts.mp3" />

      {/* BGM 轨道（根据情绪切换） */}
      <Sequence from={0}>
        <Audio src="/bgm/suspense-intro.mp3" volume={0.3} />
      </Sequence>
      <Sequence from={Math.round(82.5 * fps)}>
        <Audio src="/bgm/epic-climax.mp3" volume={0.3} />
      </Sequence>

      {/* ===== 视频轨道 ===== */}
      {/* Segment 1: 开场钩子 → 情绪卡片 */}
      <Sequence
        from={0}
        durationInFrames={Math.round(12.5 * fps)}
      >
        <EmotionCard
          emotion="震惊"
          emoji="😱"
          text="一个被判终身监禁的银行家\n如何用20年挖出一条隧道？"
          color="#FF4444"
        />
        <AnimatedSubtitle
          text="你有没有想过，一个被判终身监禁的银行家，如何用20年时间挖出一条隧道？"
          highlightWords={["终身监禁", "20年", "隧道"]}
          startFrame={Math.round(0.5 * fps)}
        />
      </Sequence>

      {/* Segment 2: 剧情引入 → 剧照卡片 */}
      <Sequence
        from={Math.round(12.5 * fps)}
        durationInFrames={Math.round(22.0 * fps)}
        premountFor={30}
      >
        <PhotoCard
          imageUrl="/assets/shawshank-poster.jpg"
          title="肖申克的救赎"
          subtitle="豆瓣评分 9.7 | 1994"
          blurRadius={15}
        />
        <AnimatedSubtitle
          text="1994年，弗兰克·德拉邦特拍出了这部传世经典..."
          highlightWords={["1994年", "传世经典"]}
          startFrame={Math.round(13.5 * fps)}
        />
      </Sequence>

      {/* Segment 3-6: 原片片段（精确匹配） */}
      {SEGMENTS.filter(s => s.template === 'clip').map(seg => (
        <Sequence
          key={seg.type}
          from={Math.round(seg.startSec * fps)}
          durationInFrames={Math.round(seg.durationSec * fps)}
          premountFor={60}  // 提前 2 秒预加载
        >
          <OffthreadVideo
            src={`/clips/shawshank-${seg.type}.mp4`}
            style={{ width: '100%', height: '100%', objectFit: 'cover' }}
            volume={0}  // 原片静音（OST=0 模式）
          />
        </Sequence>
      ))}

      {/* Segment 7: 结尾 → 剧照 + 引导关注 */}
      <Sequence
        from={Math.round(129.5 * fps)}
        durationInFrames={Math.round(15.0 * fps)}
        premountFor={30}
      >
        <PhotoCard
          imageUrl="/assets/shawshank-ending.jpg"
          title="希望是好事，也许是人间至善"
          subtitle={platform === 'douyin' ? '关注我，下期更精彩' : '如果喜欢，记得一键三连'}
        />
      </Sequence>
    </AbsoluteFill>
  )
}
```

### 9.3 Remotion vs FFmpeg 的混合策略

```
不同场景选择不同渲染引擎：

┌──────────────────────┬─────────────────┬──────────────────┐
│ 场景                  │ 推荐引擎         │ 原因              │
├──────────────────────┼─────────────────┼──────────────────┤
│ 纯素材拼接 + 简单字幕 │ FFmpeg concat   │ 快 10x+、无编码  │
│ 视觉模板 + 动画特效   │ Remotion        │ 组件化、可调试    │
│ 复杂转场 + 3D 效果   │ Remotion Three  │ FFmpeg 做不到    │
│ 批量 100+ 条          │ FFmpeg + GPU    │ 硬件编码吞吐量    │
│ 实时预览              │ Remotion Player │ 浏览器原生渲染    │
│ 最终高清导出           │ FFmpeg          │ GPU 编码效率     │
└──────────────────────┴─────────────────┴──────────────────┘

推荐策略：Remotion 做"创作和预览"，FFmpeg 做"最终批量导出"
```

---

## 10. 完整技术栈推荐

### 10.1 技术选型总表

| 层级 | 模块 | MVP 方案 | 生产方案 | 备注 |
|------|------|---------|---------|------|
| **前端** | 框架 | Next.js 15 | Next.js 15 | SSR + API Routes |
| | UI | shadcn/ui + Tailwind | shadcn/ui + Tailwind | |
| | 视频播放 | Remotion Player | Remotion Player | 实时预览 |
| | 时间线 | 自研 Timeline 组件 | 自研 + Remotion Timeline | |
| | 浏览器渲染 | @remotion/web-renderer (实验) | @remotion/web-renderer | 浏览器端出片 |
| **后端** | API | FastAPI | FastAPI + Kong | |
| | 工作流 | Celery + Redis | Temporal | MVP 可先不用 Temporal |
| | 数据库 | PostgreSQL + pgvector | PostgreSQL + pgvector | 向量搜索内置 |
| | 缓存 | Redis | Redis Cluster | |
| | 文件存储 | MinIO (S3) | MinIO + CDN | |
| **AI 能力** | 文案生成 | DeepSeek R1 (prompt chain) | 四层 Agent 协作 | 成本降低 90% |
| | 风格学习 | narrator-ai API | narrator-ai API + 自研 | |
| | 视频理解 | CLIP + pgvector | TwelveLabs Marengo 3.0 | |
| | 配音 TTS | narrator-ai API + Edge TTS | CosyVoice2 (自部署) | 边际成本趋零 |
| | BGM | 预置 146 首库 | 预置库 + Suno 生成 | |
| | 画面生成 | 不做（素材+模板） | Kling/Seedance（可选） | MVP 不需要 |
| **视频处理** | 合成引擎 | FFmpeg (K8s Job) | FFmpeg + Remotion 双引擎 | |
| | 硬件加速 | NVENC | NVENC / QSV / VAAPI | |
| **DevOps** | 容器 | Docker | Docker + K8s | |
| | CI/CD | GitHub Actions | GitHub Actions | |
| | 监控 | Sentry + Grafana | Sentry + Prometheus + Grafana | |

### 10.2 模型成本估算

```
单条解说视频（3 分钟，抖音规格）的 AI 调用成本：

┌──────────────────────┬──────────┬──────────┬──────────┐
│ 环节                  │ MVP 方案  │ 成本     │ 生产方案  │
├──────────────────────┼──────────┼──────────┼──────────┤
│ 文案生成 (4-stage)    │ DeepSeek │ ¥0.02    │ Claude   │
│ 风格匹配              │ narrator │ ¥0.10    │ narrator │
│ 画面匹配              │ CLIP     │ ¥0.00    │ Marengo  │
│ 配音 TTS              │ Edge TTS │ ¥0.00    │ CosyVoice│
│ BGM                   │ 素材库   │ ¥0.00    │ 素材库   │
│ 视频合成              │ FFmpeg   │ ¥0.05    │ FFmpeg   │
│                      │          │          │ GPU      │
├──────────────────────┼──────────┼──────────┼──────────┤
│ 合计                  │          │ ~¥0.17   │ ~¥0.50   │
└──────────────────────┴──────────┴──────────┴──────────┘

对比：narrator-ai API 约 ¥3/条
对比：人工制作约 ¥50-200/条（按剪辑师时薪 ¥50×1-4 小时）

结论：即使全用商业 API，一条解说视频的 AI 成本也在 ¥0.5 以内
```

---

## 11. MVP 落地方案

### 11.1 MVP 技术范围（4-6 周）

```
✅ 包含（对标 NarratoAI + B站花生已验证的能力）：
  • DeepSeek R1 4-stage prompt chain 文案生成
  • narrator-ai API 风格注入 + TTS 配音
  • CLIP + pgvector 画面匹配（降级方案）
  • 4 种核心视觉模板（剧照卡片/情绪卡片/时间线/字幕动画）
  • FFmpeg 视频合成（K8s Job）
  • Next.js 前端（Remotion Player 预览）
  • 预置 50 部电影 + 146 首 BGM
  • 基础工作流（选片→风格→生成→审阅→合成→导出）

❌ 不含（Phase 2/3 加入）：
  • Temporal 工作流引擎（MVP 用 Celery 够用）
  • TwelveLabs Marengo 3.0（成本 + 集成复杂度）
  • CosyVoice2 自部署（先用 narrator-ai API）
  • Remotion Video-as-Code 生成（先用 VDL + FFmpeg）
  • 风格市场 + 团队协作 + 多平台一键适配
  • 语音克隆 + AI 画面生成
```

### 11.2 MVP 核心开发任务

```
Week 1-2: 文案引擎
  □ 4-stage prompt chain 实现
  □ 3 种核心风格模板（悬疑/励志/爆笑）JSON 配置
  □ narrator-ai API 集成（风格学习 + TTS）
  □ 文案质量评分模块

Week 3-4: 画面匹配 + 合成
  □ CLIP + pgvector 帧嵌入 + 检索
  □ 4 种视觉模板 React 组件（Remotion）
  □ VDL 编译器 + FFmpeg 渲染 Job
  □ 预置 50 部电影关键帧抽取 + 嵌入

Week 5-6: 前端 + 集成
  □ Next.js 创作工作台（项目列表 + 文案编辑 + 时间线）
  □ Remotion Player 集成（实时预览）
  □ 工作流串联：选片→生成→审阅→合成→导出
  □ 用户注册/登录 + 基础计费
```

---

## 12. 附录：竞品技术对标

### 12.1 完整竞品技术矩阵

| 能力 | NarratoAI | narrator-ai | Pixelle-Video | B站花生 | B站 UpDream | **本方案** |
|------|-----------|-------------|---------------|---------|-------------|-----------|
| **文案生成** | 4-stage prompt chain (DeepSeek/GPT) | 风格学习模型 API | 单次 LLM (GPT/通义) | 单次 LLM (未公开) | 长期记忆 + Skill | **4-stage + 风格指纹注入** |
| **视频理解** | Qwen2.5-VL 场景分析 | 无（依赖预置元数据） | 无（AI 生成画面） | 未公开 | 未公开 | **CLIP/Marengo 3.0 多模态检索** |
| **视觉组装** | 原片片段 + MoviePy | FFmpeg 素材拼接 | ComfyUI 工作流 | 自动素材匹配 | 非线性画布 | **VDL + FFmpeg/Remotion 双引擎** |
| **视觉模板** | 无（纯素材） | 无 | ComfyUI 模板 | 有（未公开细节） | 有 | **4 类参数化模板** |
| **配音 TTS** | Edge/Azure/ElevenLabs | 63 角色 + 11 语言 | Edge/Index/ChatTTS | 40 公共音色 | 未公开 | **多引擎路由 + SSML 标注驱动** |
| **语音克隆** | CosyVoice2 (零样本) | 30s 样本 | Index-TTS | 10s 样本 | 未公开 | **CosyVoice2 (自部署零成本)** |
| **BGM** | 素材 API (Pexels/Pixabay) | 无内置 | 无 | 素材库 | 未公开 | **146 首预标注 + 智能匹配** |
| **多平台** | OST 三模式 | 抖音/B站/快手参数 | 9:16/16:9/1:1 | B站一键发布 | B站一键发布 | **语体翻译 + 格式适配** |
| **风格生态** | 无 | 12 种风格 + 风格学习 | 无（prompt 前缀） | 无 | 个性化技能库 | **风格指纹 + 风格市场** |
| **门槛** | 低 (Web UI) | 中高 (CLI) | 低 (Web UI) | 极低 | 极低 | **极低 (Web)** |
| **开源** | ✅ Apache 2.0 | ❌ (API 需付费) | ✅ Apache 2.0 | ❌ | ❌ | - |
| **价格** | 免费 + 云端 ¥2/10min | ¥3/条 (~305 点) | 免费 (自部署) | ¥188/年 | 未公布 | **目标 ¥0.5/条** |

### 12.2 参考资源

| 序号 | 资源 | 类型 |
|------|------|------|
| 1 | [NarratoAI GitHub](https://github.com/linyqh/NarratoAI) | 开源代码 |
| 2 | [NarratoAI DeepWiki 架构文档](https://deepwiki.com/linyqh/NarratoAI) | 架构文档 |
| 3 | [Pixelle-Video GitHub](https://github.com/AIDC-AI/Pixelle-Video) | 开源代码 |
| 4 | [narrator-ai API 文档](https://docs.jieshuo.cn) | API 文档 |
| 5 | [narrator-ai-cli GitHub](https://github.com/NarratorAI-Studio/narrator-ai-cli) | 开源代码 |
| 6 | [narrator-ai-cli-skill GitHub](https://github.com/NarratorAI-Studio/narrator-ai-cli-skill) | Agent Skill |
| 7 | [TwelveLabs Marengo 3.0](https://www.twelvelabs.io/blog/marengo-3-0) | 产品发布 |
| 8 | [Remotion GitHub](https://github.com/remotion-dev/remotion) | 开源框架 |
| 9 | [video-as-code-for-agents](https://github.com/zPy52/video-as-code-for-agents) | 开源项目 |
| 10 | [remotion-ad-video-skill](https://github.com/leosssvip-dot/remotion-ad-video-skill) | 开源项目 |
| 11 | [AWS Bedrock 多模态视频理解](https://aws.amazon.com/cn/blogs/machine-learning/unlocking-video-insights-at-scale-with-amazon-bedrock-multimodal-models/) | 技术博客 |
| 12 | [B站花生 AI 工具](https://www.bianews.com/news/details?id=226197) | 产品报道 |
| 13 | [B站 UpDream 内测](https://ai.zol.com.cn/1157/11576550.html) | 产品报道 |
| 14 | [基于CLI与AgentSkill构建工业级AI影视解说自动化链路](https://developer.aliyun.com/article/1727140) | 技术文章 |

---

> **文档状态**：v1.0 完成
> **覆盖模块**：文案生成 / 画面匹配 / 配音系统 / 视觉模板 / BGM匹配 / 多平台适配 / 编排引擎 / Remotion Video-as-Code / 技术栈推荐
> **下一步**：MVP 开发计划细化 → 各模块 POC 验证 → 技术选型最终确认
