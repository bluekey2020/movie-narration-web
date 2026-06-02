#!/usr/bin/env python3
"""Generate the complete BGM library JSON with 146 tracks."""
import json
import random
import math

# Seed for reproducibility
random.seed(42)

# === Existing 5 tracks (preserved exactly) ===
existing_tracks = [
    {
        "track_id": "bgm_001",
        "title": "悬疑铺垫",
        "duration_sec": 120.0,
        "emotions": ["suspense", "dark", "mysterious"],
        "bpm": 85,
        "key": "C minor",
        "energy": 0.3,
        "instruments": ["piano", "strings"],
        "sections": [
            {"start": 0, "end": 15, "type": "intro"},
            {"start": 15, "end": 90, "type": "main"},
            {"start": 90, "end": 120, "type": "outro"}
        ],
        "natural_cut_points": [15.0, 30.0, 45.0, 60.0, 75.0, 90.0, 105.0, 120.0],
        "usage_tags": ["buildup", "hook", "transition"],
        "license_type": "cc0",
        "file_path": "/bgm/suspense_buildup.mp3"
    },
    {
        "track_id": "bgm_002",
        "title": "紧张追逐",
        "duration_sec": 90.0,
        "emotions": ["tense", "intense", "urgent"],
        "bpm": 140,
        "key": "D minor",
        "energy": 0.8,
        "instruments": ["electronic", "drums", "strings"],
        "sections": [
            {"start": 0, "end": 10, "type": "intro"},
            {"start": 10, "end": 70, "type": "main"},
            {"start": 70, "end": 90, "type": "climax"}
        ],
        "natural_cut_points": [10.0, 25.0, 40.0, 55.0, 70.0, 90.0],
        "usage_tags": ["climax", "action"],
        "license_type": "cc0",
        "file_path": "/bgm/tense_chase.mp3"
    },
    {
        "track_id": "bgm_003",
        "title": "史诗高潮",
        "duration_sec": 180.0,
        "emotions": ["epic", "triumphant", "heroic"],
        "bpm": 100,
        "key": "C major",
        "energy": 0.9,
        "instruments": ["orchestra", "choir", "brass", "drums"],
        "sections": [
            {"start": 0, "end": 20, "type": "intro"},
            {"start": 20, "end": 120, "type": "main"},
            {"start": 120, "end": 160, "type": "climax"},
            {"start": 160, "end": 180, "type": "outro"}
        ],
        "natural_cut_points": [20.0, 40.0, 60.0, 80.0, 100.0, 120.0, 140.0, 160.0, 180.0],
        "usage_tags": ["climax", "ending"],
        "license_type": "licensed",
        "file_path": "/bgm/epic_climax.mp3"
    },
    {
        "track_id": "bgm_004",
        "title": "温暖回忆",
        "duration_sec": 150.0,
        "emotions": ["warm", "nostalgic", "hopeful"],
        "bpm": 75,
        "key": "G major",
        "energy": 0.4,
        "instruments": ["piano", "guitar", "strings"],
        "sections": [
            {"start": 0, "end": 20, "type": "intro"},
            {"start": 20, "end": 130, "type": "main"},
            {"start": 130, "end": 150, "type": "outro"}
        ],
        "natural_cut_points": [20.0, 50.0, 80.0, 110.0, 130.0, 150.0],
        "usage_tags": ["reflection", "ending", "transition"],
        "license_type": "cc0",
        "file_path": "/bgm/warm_memories.mp3"
    },
    {
        "track_id": "bgm_005",
        "title": "暗黑氛围",
        "duration_sec": 100.0,
        "emotions": ["dark", "tense", "mysterious", "horror"],
        "bpm": 60,
        "key": "F minor",
        "energy": 0.5,
        "instruments": ["electronic", "piano", "ambient"],
        "sections": [
            {"start": 0, "end": 15, "type": "intro"},
            {"start": 15, "end": 80, "type": "main"},
            {"start": 80, "end": 100, "type": "outro"}
        ],
        "natural_cut_points": [15.0, 30.0, 50.0, 65.0, 80.0, 100.0],
        "usage_tags": ["buildup", "hook"],
        "license_type": "cc0",
        "file_path": "/bgm/dark_atmosphere.mp3"
    }
]


# === Helper functions ===
def make_sections(duration, with_climax=False):
    """Generate intro/main/[climax]/outro sections based on duration."""
    intro_end = round(duration * random.uniform(0.08, 0.15))
    outro_start = round(duration * random.uniform(0.80, 0.90))

    sections = []
    sections.append({"start": 0, "end": intro_end, "type": "intro"})

    if with_climax:
        climax_start = round(duration * random.uniform(0.60, 0.75))
        sections.append({"start": intro_end, "end": climax_start, "type": "main"})
        sections.append({"start": climax_start, "end": outro_start, "type": "climax"})
    else:
        sections.append({"start": intro_end, "end": outro_start, "type": "main"})

    sections.append({"start": outro_start, "end": duration, "type": "outro"})
    return sections


def make_cut_points(duration, sections):
    """Generate natural cut points at regular intervals aligned to section boundaries."""
    points = []
    interval = duration / random.randint(4, 8)
    # Include section boundaries
    boundary_points = set()
    for s in sections:
        boundary_points.add(float(s["start"]))
        boundary_points.add(float(s["end"]))
    # Add regular intervals
    t = interval
    while t < duration:
        points.append(round(t, 1))
        t += interval
    # Merge with boundary points
    all_points = sorted(set(points) | boundary_points)
    # Ensure endpoints
    if duration not in all_points:
        all_points.append(float(duration))
    # Remove 0.0 if present
    all_points = [p for p in all_points if p > 0.0]
    return all_points


def track(idx, title, emotions, bpm_range, key_pool, energy_range, instruments, usage_tags,
          license_type, duration_range=(60, 240), with_climax=False):
    """Create a track dictionary."""
    duration = random.randint(*duration_range)
    # Round to nearest 5 for neatness
    duration = round(duration / 5) * 5
    if duration < 60:
        duration = 60
    if duration > 240:
        duration = 240

    sections = make_sections(duration, with_climax)
    cut_points = make_cut_points(duration, sections)

    return {
        "track_id": f"bgm_{idx:03d}",
        "title": title,
        "duration_sec": float(duration),
        "emotions": emotions,
        "bpm": random.randint(*bpm_range),
        "key": random.choice(key_pool),
        "energy": round(random.uniform(*energy_range), 1),
        "instruments": instruments,
        "sections": sections,
        "natural_cut_points": [round(p, 1) for p in cut_points],
        "usage_tags": usage_tags,
        "license_type": license_type,
        "file_path": f"/bgm/bgm_{idx:03d}.mp3"
    }


# === License distribution ===
# We need 100 cc0 and 46 licensed out of 146 total
# Existing: bgm_001 cc0, bgm_002 cc0, bgm_003 licensed, bgm_004 cc0, bgm_005 cc0
# So 4 cc0, 1 licensed in existing
# Need: 96 cc0, 45 licensed in new 141 tracks

# Pre-generate license assignments for new tracks (bgm_006 to bgm_146)
new_license_pool = ["cc0"] * 96 + ["licensed"] * 45
random.shuffle(new_license_pool)

license_iter = iter(new_license_pool)


def next_license():
    return next(license_iter)


# === Track definitions by category ===
new_tracks = []

# ---- Suspense/Mystery: 20 tracks ----
suspense_keys = ["C minor", "D minor", "E minor", "F minor", "G minor", "A minor", "B minor", "C# minor", "Eb minor"]
suspense_tracks = [
    ("暗夜追踪", ["suspense", "mysterious", "dark"], (70, 95), (0.2, 0.5),
     ["piano", "strings"], ["buildup", "hook", "transition"], False),
    ("迷雾重重", ["mysterious", "suspense", "tense"], (65, 85), (0.2, 0.45),
     ["piano", "electronic", "strings"], ["buildup", "hook"], False),
    ("阴影逼近", ["dark", "suspense", "tense"], (75, 100), (0.25, 0.55),
     ["strings", "piano", "drums"], ["buildup", "transition"], True),
    ("潜伏危机", ["suspense", "dark", "mysterious"], (60, 80), (0.15, 0.4),
     ["electronic", "piano", "ambient"], ["hook", "buildup"], False),
    ("深夜独白", ["mysterious", "dark", "tense"], (55, 75), (0.1, 0.35),
     ["piano", "strings", "ambient"], ["intro", "transition", "buildup"], False),
    ("暗流涌动", ["suspense", "tense", "dark"], (80, 105), (0.3, 0.6),
     ["electronic", "drums", "strings"], ["buildup", "transition", "hook"], True),
    ("心灵迷宫", ["mysterious", "suspense", "dark"], (70, 90), (0.2, 0.4),
     ["piano", "electronic", "strings"], ["buildup", "transition"], False),
    ("无形威胁", ["dark", "tense", "suspense"], (65, 85), (0.25, 0.5),
     ["strings", "brass", "drums"], ["buildup", "hook"], False),
    ("午夜谜题", ["mysterious", "suspense", "dark"], (75, 95), (0.2, 0.45),
     ["piano", "electronic", "ambient"], ["intro", "buildup", "hook"], False),
    ("暗黑心跳", ["suspense", "dark", "intense"], (85, 110), (0.35, 0.6),
     ["electronic", "drums", "piano"], ["buildup", "hook", "transition"], True),
    ("窥探", ["mysterious", "suspense", "tense"], (60, 80), (0.15, 0.4),
     ["piano", "strings", "electronic"], ["hook", "buildup"], False),
    ("蛛丝马迹", ["suspense", "mysterious", "dark"], (70, 90), (0.2, 0.5),
     ["strings", "piano", "drums"], ["buildup", "transition"], False),
    ("嫌疑人", ["dark", "suspense", "mysterious", "tense"], (65, 85), (0.25, 0.5),
     ["electronic", "piano", "ambient"], ["hook", "buildup", "transition"], False),
    ("密室逃脱", ["suspense", "intense", "dark"], (85, 115), (0.35, 0.65),
     ["electronic", "drums", "strings"], ["buildup", "action", "transition"], True),
    ("真相边缘", ["mysterious", "suspense", "tense"], (70, 90), (0.2, 0.45),
     ["piano", "strings", "electronic"], ["buildup", "hook"], False),
    ("暗夜行者", ["dark", "mysterious", "suspense"], (60, 80), (0.15, 0.35),
     ["piano", "ambient", "strings"], ["intro", "transition"], False),
    ("不可告人", ["suspense", "dark", "mysterious", "tense"], (75, 95), (0.3, 0.55),
     ["strings", "piano", "drums", "electronic"], ["buildup", "hook", "transition"], True),
    ("秘密基地", ["mysterious", "suspense", "dark"], (65, 85), (0.2, 0.4),
     ["electronic", "piano", "ambient"], ["buildup", "hook"], False),
    ("渐近脚步", ["suspense", "tense", "dark"], (80, 100), (0.3, 0.6),
     ["drums", "strings", "piano"], ["buildup", "transition", "action"], True),
    ("谜底揭晓", ["mysterious", "suspense", "dark", "dramatic"], (70, 90), (0.25, 0.55),
     ["orchestra", "piano", "strings"], ["buildup", "hook", "climax"], True),
]

for i, (title, emotions, bpm_range, energy_range, instruments, usage_tags, with_climax) in enumerate(suspense_tracks):
    new_tracks.append(track(6 + i, title, emotions, bpm_range, suspense_keys, energy_range,
                            instruments, usage_tags, next_license(), with_climax=with_climax))

# ---- Action/Epic: 24 tracks ----
action_keys = ["C major", "D major", "E minor", "F minor", "G minor", "A minor", "B minor", "Eb major", "C minor"]
action_tracks = [
    ("雷霆万钧", ["epic", "heroic", "triumphant"], (90, 130), (0.7, 1.0),
     ["orchestra", "choir", "brass", "drums"], ["climax", "action", "ending"], True),
    ("决战时刻", ["epic", "intense", "heroic"], (100, 140), (0.75, 1.0),
     ["orchestra", "drums", "brass", "strings"], ["climax", "action"], True),
    ("冲锋陷阵", ["heroic", "epic", "action"], (110, 150), (0.8, 1.0),
     ["orchestra", "drums", "brass", "choir"], ["action", "climax"], True),
    ("王者归来", ["triumphant", "epic", "heroic"], (85, 115), (0.7, 0.95),
     ["orchestra", "choir", "brass"], ["ending", "climax", "action"], True),
    ("钢铁洪流", ["epic", "intense", "action"], (100, 135), (0.75, 1.0),
     ["electronic", "drums", "orchestra", "brass"], ["action", "climax"], True),
    ("不屈战魂", ["heroic", "epic", "dramatic"], (90, 120), (0.65, 0.9),
     ["orchestra", "choir", "drums", "strings"], ["climax", "action"], True),
    ("破晓之战", ["epic", "heroic", "intense"], (95, 130), (0.7, 0.95),
     ["orchestra", "drums", "brass", "electronic"], ["action", "climax", "transition"], True),
    ("胜利序曲", ["triumphant", "epic", "grand"], (80, 110), (0.65, 0.9),
     ["orchestra", "brass", "choir", "drums"], ["ending", "climax"], True),
    ("烈火燎原", ["intense", "epic", "action"], (110, 150), (0.8, 1.0),
     ["electronic", "drums", "orchestra", "strings"], ["action", "climax"], True),
    ("帝国崛起", ["epic", "grand", "heroic"], (80, 110), (0.6, 0.85),
     ["orchestra", "choir", "brass", "drums"], ["buildup", "climax", "ending"], True),
    ("荒野追逐", ["action", "intense", "epic"], (120, 155), (0.8, 1.0),
     ["electronic", "drums", "orchestra"], ["action", "climax"], True),
    ("无尽征程", ["epic", "heroic", "hopeful"], (85, 115), (0.6, 0.85),
     ["orchestra", "choir", "strings", "brass"], ["buildup", "action", "ending"], True),
    ("暴风骤雨", ["intense", "epic", "dramatic"], (105, 140), (0.75, 1.0),
     ["orchestra", "drums", "brass", "choir"], ["climax", "action"], True),
    ("英雄悲歌", ["heroic", "epic", "dramatic", "emotional"], (75, 100), (0.55, 0.8),
     ["orchestra", "choir", "strings"], ["buildup", "climax", "ending"], True),
    ("战鼓雷鸣", ["intense", "epic", "heroic"], (100, 140), (0.8, 1.0),
     ["drums", "orchestra", "brass", "electronic"], ["action", "climax"], True),
    ("巅峰对决", ["epic", "intense", "action", "heroic"], (105, 145), (0.75, 1.0),
     ["orchestra", "drums", "electronic", "strings"], ["climax", "action"], True),
    ("黎明之光", ["heroic", "triumphant", "hopeful", "grand"], (80, 110), (0.6, 0.85),
     ["orchestra", "choir", "strings", "brass"], ["ending", "climax", "transition"], True),
    ("暗夜骑士", ["epic", "dark", "heroic"], (90, 120), (0.65, 0.9),
     ["orchestra", "drums", "electronic", "choir"], ["action", "climax", "buildup"], True),
    ("铁血军魂", ["epic", "heroic", "intense", "grand"], (95, 130), (0.7, 0.95),
     ["orchestra", "drums", "brass"], ["climax", "ending", "action"], True),
    ("征程万里", ["epic", "heroic", "action"], (90, 120), (0.65, 0.9),
     ["orchestra", "drums", "strings", "brass"], ["buildup", "action", "transition"], True),
    ("命运之轮", ["epic", "dramatic", "intense"], (85, 115), (0.6, 0.85),
     ["orchestra", "choir", "drums", "strings"], ["buildup", "climax", "transition"], True),
    ("终极之战", ["epic", "intense", "triumphant"], (110, 155), (0.85, 1.0),
     ["orchestra", "drums", "brass", "choir", "electronic"], ["climax", "action"], True),
    ("荣耀时刻", ["triumphant", "epic", "grand", "heroic"], (75, 100), (0.55, 0.8),
     ["orchestra", "choir", "brass", "strings"], ["ending", "climax"], True),
    ("不灭传奇", ["epic", "heroic", "grand", "triumphant"], (85, 120), (0.65, 0.9),
     ["orchestra", "choir", "drums", "brass"], ["ending", "climax"], True),
]

for i, (title, emotions, bpm_range, energy_range, instruments, usage_tags, with_climax) in enumerate(action_tracks):
    new_tracks.append(track(26 + i, title, emotions, bpm_range, action_keys, energy_range,
                            instruments, usage_tags, next_license(), with_climax=with_climax))

# ---- Emotional/Warm: 24 tracks ----
emotional_keys = ["C major", "G major", "D major", "F major", "A major", "E major", "Bb major", "E minor", "A minor"]
emotional_tracks = [
    ("阳光洒落", ["warm", "hopeful", "peaceful"], (60, 80), (0.2, 0.45),
     ["piano", "guitar", "strings"], ["reflection", "transition", "intro"], False),
    ("家的温暖", ["warm", "nostalgic", "emotional"], (55, 75), (0.15, 0.4),
     ["piano", "strings", "guitar"], ["reflection", "ending", "transition"], False),
    ("金色时光", ["nostalgic", "warm", "hopeful"], (60, 80), (0.2, 0.4),
     ["guitar", "piano", "strings"], ["reflection", "intro", "transition"], False),
    ("微风轻拂", ["peaceful", "warm", "calm"], (50, 70), (0.1, 0.3),
     ["piano", "strings", "ambient"], ["intro", "reflection", "transition"], False),
    ("童年记忆", ["nostalgic", "warm", "happy"], (65, 85), (0.25, 0.5),
     ["piano", "guitar", "strings", "flute"], ["reflection", "transition", "intro"], False),
    ("雨后彩虹", ["hopeful", "warm", "peaceful"], (55, 75), (0.2, 0.4),
     ["piano", "strings", "guitar"], ["ending", "reflection", "transition"], False),
    ("星月夜话", ["warm", "nostalgic", "calm"], (45, 65), (0.1, 0.3),
     ["piano", "guitar", "ambient"], ["intro", "reflection", "ending"], False),
    ("春日漫步", ["happy", "warm", "hopeful"], (70, 90), (0.3, 0.5),
     ["guitar", "piano", "strings", "flute"], ["intro", "transition", "reflection"], False),
    ("烛光晚餐", ["warm", "romantic", "peaceful"], (55, 75), (0.15, 0.35),
     ["piano", "strings", "guitar"], ["reflection", "ending", "intro"], False),
    ("盛夏果实", ["hopeful", "warm", "nostalgic"], (60, 80), (0.2, 0.45),
     ["guitar", "piano", "strings"], ["reflection", "transition"], False),
    ("秋水长天", ["warm", "emotional", "peaceful"], (50, 70), (0.15, 0.35),
     ["piano", "strings", "guitar", "ambient"], ["reflection", "ending", "intro"], False),
    ("友谊之歌", ["warm", "hopeful", "happy"], (65, 85), (0.25, 0.5),
     ["guitar", "piano", "strings"], ["reflection", "transition", "ending"], False),
    ("晨光熹微", ["peaceful", "hopeful", "warm"], (50, 70), (0.1, 0.3),
     ["piano", "strings", "ambient"], ["intro", "reflection"], False),
    ("暮色归途", ["nostalgic", "warm", "peaceful"], (55, 75), (0.15, 0.35),
     ["guitar", "piano", "strings"], ["ending", "reflection", "transition"], False),
    ("心中的光", ["hopeful", "warm", "emotional"], (60, 80), (0.25, 0.5),
     ["piano", "strings", "choir"], ["buildup", "reflection", "ending"], True),
    ("远方来信", ["nostalgic", "warm", "hopeful"], (55, 75), (0.15, 0.4),
     ["piano", "guitar", "strings"], ["reflection", "intro", "transition"], False),
    ("温暖拥抱", ["warm", "emotional", "peaceful"], (50, 70), (0.15, 0.35),
     ["piano", "strings", "guitar"], ["reflection", "ending"], False),
    ("希望之翼", ["hopeful", "warm", "emotional", "grand"], (65, 85), (0.3, 0.55),
     ["piano", "strings", "orchestra"], ["buildup", "reflection", "ending"], True),
    ("岁月静好", ["peaceful", "warm", "nostalgic"], (45, 65), (0.1, 0.25),
     ["piano", "guitar", "ambient"], ["intro", "reflection", "transition"], False),
    ("梦想起航", ["hopeful", "warm", "energetic"], (70, 90), (0.3, 0.55),
     ["guitar", "piano", "drums", "strings"], ["buildup", "transition", "reflection"], False),
    ("山涧清泉", ["peaceful", "warm", "calm"], (45, 65), (0.1, 0.25),
     ["piano", "guitar", "ambient"], ["intro", "reflection", "transition"], False),
    ("落日余晖", ["nostalgic", "warm", "emotional", "sad"], (50, 70), (0.15, 0.35),
     ["piano", "strings", "guitar"], ["ending", "reflection"], False),
    ("安魂曲", ["peaceful", "emotional", "sad", "warm"], (40, 60), (0.1, 0.3),
     ["piano", "strings", "choir"], ["ending", "reflection"], False),
    ("生命礼赞", ["hopeful", "warm", "emotional", "grand"], (60, 80), (0.3, 0.6),
     ["orchestra", "piano", "strings", "choir"], ["reflection", "ending", "climax"], True),
]

for i, (title, emotions, bpm_range, energy_range, instruments, usage_tags, with_climax) in enumerate(emotional_tracks):
    new_tracks.append(track(50 + i, title, emotions, bpm_range, emotional_keys, energy_range,
                            instruments, usage_tags, next_license(), with_climax=with_climax))

# ---- Horror/Terror: 14 tracks ----
horror_keys = ["C minor", "C# minor", "D minor", "Eb minor", "F minor", "F# minor", "B minor"]
horror_tracks = [
    ("深渊凝视", ["horror", "dark", "scary"], (40, 60), (0.2, 0.5),
     ["electronic", "ambient", "piano"], ["buildup", "hook", "transition"], False),
    ("鬼影幢幢", ["scary", "dark", "horror", "tense"], (50, 70), (0.25, 0.55),
     ["electronic", "strings", "ambient", "drums"], ["buildup", "hook"], True),
    ("地下室", ["horror", "dark", "mysterious", "suspense"], (40, 55), (0.15, 0.4),
     ["ambient", "electronic", "piano"], ["hook", "buildup", "intro"], False),
    ("无声尖叫", ["scary", "horror", "tense", "intense"], (55, 80), (0.3, 0.65),
     ["electronic", "strings", "drums"], ["climax", "hook", "action"], True),
    ("阴森走廊", ["dark", "horror", "suspense", "mysterious"], (35, 50), (0.1, 0.3),
     ["ambient", "piano", "electronic"], ["intro", "hook", "buildup"], False),
    ("午夜凶铃", ["horror", "scary", "tense", "dark"], (45, 65), (0.2, 0.5),
     ["electronic", "piano", "drums", "strings"], ["hook", "buildup", "climax"], False),
    ("恶魔低语", ["dark", "horror", "scary", "mysterious"], (40, 55), (0.15, 0.35),
     ["ambient", "electronic", "choir"], ["buildup", "hook", "intro"], False),
    ("血色月光", ["horror", "dark", "scary", "tense"], (50, 75), (0.25, 0.6),
     ["electronic", "strings", "drums", "piano"], ["hook", "buildup", "climax"], True),
    ("恐惧降临", ["scary", "horror", "tense", "intense"], (55, 85), (0.35, 0.7),
     ["electronic", "drums", "strings", "ambient"], ["climax", "buildup", "action"], True),
    ("空旷病房", ["dark", "horror", "scary", "mysterious"], (30, 50), (0.1, 0.25),
     ["ambient", "piano", "electronic"], ["intro", "hook", "transition"], False),
    ("荒废古宅", ["horror", "dark", "mysterious", "suspense"], (40, 60), (0.15, 0.4),
     ["ambient", "electronic", "piano", "strings"], ["buildup", "hook", "intro"], False),
    ("亡灵序曲", ["dark", "scary", "horror", "dramatic"], (45, 65), (0.2, 0.5),
     ["choir", "orchestra", "electronic", "drums"], ["buildup", "climax"], True),
    ("镜中人", ["horror", "scary", "dark", "mysterious"], (35, 55), (0.15, 0.4),
     ["electronic", "ambient", "piano", "strings"], ["hook", "buildup"], False),
    ("末路狂奔", ["tense", "horror", "scary", "intense"], (60, 90), (0.4, 0.75),
     ["electronic", "drums", "strings"], ["action", "climax", "transition"], True),
]

for i, (title, emotions, bpm_range, energy_range, instruments, usage_tags, with_climax) in enumerate(horror_tracks):
    new_tracks.append(track(74 + i, title, emotions, bpm_range, horror_keys, energy_range,
                            instruments, usage_tags, next_license(), with_climax=with_climax))

# ---- Comedy/Light: 14 tracks ----
comedy_keys = ["C major", "G major", "D major", "F major", "A major", "Bb major", "E major", "A minor"]
comedy_tracks = [
    ("欢乐日常", ["happy", "light", "funky"], (90, 130), (0.35, 0.65),
     ["jazz", "piano", "drums", "bass"], ["intro", "transition", "reflection"], False),
    ("滑稽时刻", ["quirky", "playful", "light"], (85, 120), (0.3, 0.6),
     ["jazz", "piano", "brass", "drums"], ["hook", "transition"], False),
    ("小熊跳舞", ["playful", "happy", "light"], (100, 140), (0.4, 0.7),
     ["jazz", "piano", "flute", "drums"], ["intro", "transition"], False),
    ("阳光爵士", ["jazzy", "light", "happy"], (95, 130), (0.35, 0.6),
     ["jazz", "saxophone", "piano", "bass", "drums"], ["intro", "transition", "reflection"], False),
    ("轻松漫步", ["light", "happy", "peaceful"], (80, 110), (0.25, 0.5),
     ["piano", "guitar", "flute"], ["intro", "transition", "reflection"], False),
    ("马戏团", ["quirky", "playful", "funky", "happy"], (100, 140), (0.4, 0.75),
     ["brass", "drums", "jazz", "accordion"], ["hook", "action", "intro"], False),
    ("快乐节拍", ["funky", "happy", "energetic"], (105, 140), (0.45, 0.7),
     ["jazz", "bass", "drums", "brass"], ["transition", "action", "hook"], False),
    ("搞怪进行曲", ["quirky", "playful", "light"], (90, 125), (0.3, 0.6),
     ["brass", "drums", "piano", "jazz"], ["intro", "hook", "transition"], False),
    ("甜美时光", ["light", "happy", "playful"], (85, 115), (0.25, 0.5),
     ["piano", "flute", "guitar", "strings"], ["intro", "reflection", "transition"], False),
    ("街头艺人", ["funky", "jazzy", "happy", "energetic"], (95, 130), (0.4, 0.65),
     ["jazz", "guitar", "bass", "drums"], ["intro", "hook", "transition"], False),
    ("开心农场", ["happy", "playful", "light"], (90, 120), (0.3, 0.55),
     ["guitar", "banjo", "piano", "flute"], ["intro", "transition", "reflection"], False),
    ("周末派对", ["funky", "happy", "energetic", "jazzy"], (100, 135), (0.45, 0.75),
     ["jazz", "bass", "drums", "brass", "piano"], ["hook", "action", "transition"], False),
    ("幸运时刻", ["light", "happy", "quirky"], (80, 110), (0.25, 0.5),
     ["piano", "flute", "strings", "guitar"], ["intro", "hook", "transition"], False),
    ("童趣", ["playful", "light", "happy", "nostalgic"], (85, 115), (0.25, 0.5),
     ["piano", "guitar", "flute", "strings"], ["reflection", "intro", "transition"], False),
]

for i, (title, emotions, bpm_range, energy_range, instruments, usage_tags, with_climax) in enumerate(comedy_tracks):
    new_tracks.append(track(88 + i, title, emotions, bpm_range, comedy_keys, energy_range,
                            instruments, usage_tags, next_license(), with_climax=with_climax))

# ---- Oriental/Chinese: 14 tracks ----
oriental_keys = ["D minor", "E minor", "G major", "A minor", "C minor", "F major", "B minor"]
oriental_tracks = [
    ("水墨江南", ["peaceful", "nostalgic", "emotional"], (50, 70), (0.15, 0.35),
     ["guzheng", "pipa", "dizi", "strings"], ["intro", "reflection", "transition"], False),
    ("龙腾虎跃", ["energetic", "epic", "heroic"], (90, 130), (0.6, 0.9),
     ["guzheng", "drums", "erhu", "orchestra"], ["climax", "action", "transition"], True),
    ("古韵悠长", ["peaceful", "nostalgic", "emotional"], (40, 60), (0.1, 0.3),
     ["guzheng", "dizi", "erhu"], ["intro", "reflection", "ending"], False),
    ("侠客风云", ["heroic", "epic", "intense"], (80, 115), (0.55, 0.85),
     ["erhu", "guzheng", "drums", "orchestra"], ["action", "climax", "transition"], True),
    ("江南烟雨", ["nostalgic", "peaceful", "emotional", "sad"], (45, 65), (0.1, 0.3),
     ["pipa", "dizi", "erhu", "strings"], ["intro", "reflection", "ending"], False),
    ("战鼓擂", ["intense", "epic", "heroic", "action"], (100, 140), (0.7, 1.0),
     ["drums", "orchestra", "erhu", "guzheng"], ["climax", "action"], True),
    ("禅意", ["peaceful", "calm", "spiritual"], (40, 55), (0.05, 0.2),
     ["guzheng", "dizi", "ambient"], ["intro", "reflection", "ending"], False),
    ("花好月圆", ["warm", "nostalgic", "romantic", "peaceful"], (50, 70), (0.15, 0.35),
     ["pipa", "erhu", "dizi", "strings"], ["reflection", "ending", "intro"], False),
    ("丝路驼铃", ["mysterious", "epic", "nostalgic"], (60, 85), (0.25, 0.55),
     ["guzheng", "dizi", "drums", "orchestra"], ["buildup", "transition", "action"], True),
    ("霸王别姬", ["dramatic", "sad", "emotional", "epic"], (55, 75), (0.3, 0.6),
     ["erhu", "orchestra", "pipa", "drums"], ["climax", "ending", "reflection"], True),
    ("雪中梅花", ["peaceful", "emotional", "sad", "nostalgic"], (40, 60), (0.1, 0.25),
     ["erhu", "guzheng", "pipa", "strings"], ["intro", "reflection", "ending"], False),
    ("江湖夜雨", ["mysterious", "dark", "emotional", "suspense"], (55, 75), (0.2, 0.45),
     ["pipa", "erhu", "electronic", "drums"], ["buildup", "hook", "transition"], False),
    ("敦煌飞天", ["ethereal", "peaceful", "mysterious", "grand"], (50, 70), (0.2, 0.5),
     ["guzheng", "dizi", "choir", "orchestra"], ["buildup", "reflection", "transition"], True),
    ("塞上曲", ["nostalgic", "dramatic", "heroic", "emotional"], (55, 80), (0.25, 0.55),
     ["erhu", "guzheng", "orchestra", "drums"], ["action", "reflection", "ending"], True),
]

for i, (title, emotions, bpm_range, energy_range, instruments, usage_tags, with_climax) in enumerate(oriental_tracks):
    new_tracks.append(track(102 + i, title, emotions, bpm_range, oriental_keys, energy_range,
                            instruments, usage_tags, next_license(), with_climax=with_climax))

# ---- Sci-fi/Futuristic: 10 tracks ----
scifi_keys = ["C minor", "Eb minor", "F minor", "G minor", "A minor", "B minor", "D minor", "F# minor"]
scifi_tracks = [
    ("赛博城市", ["futuristic", "intense", "dark"], (90, 130), (0.5, 0.85),
     ["electronic", "synth", "drums", "ambient"], ["action", "transition", "hook"], True),
    ("星际航行", ["futuristic", "ethereal", "epic"], (70, 100), (0.3, 0.6),
     ["synth", "ambient", "orchestra", "electronic"], ["buildup", "transition", "intro"], True),
    ("数字迷梦", ["futuristic", "mysterious", "dreamy"], (65, 90), (0.2, 0.5),
     ["synth", "electronic", "ambient", "piano"], ["intro", "buildup", "transition"], False),
    ("量子跃迁", ["futuristic", "energetic", "intense"], (100, 140), (0.55, 0.85),
     ["electronic", "synth", "drums"], ["action", "climax", "transition"], True),
    ("机械觉醒", ["futuristic", "dark", "intense"], (85, 120), (0.45, 0.75),
     ["electronic", "drums", "synth", "ambient"], ["buildup", "action", "climax"], True),
    ("太空漫步", ["futuristic", "peaceful", "ethereal"], (50, 70), (0.1, 0.3),
     ["synth", "ambient", "electronic"], ["intro", "reflection", "transition"], False),
    ("数据洪流", ["futuristic", "intense", "energetic"], (110, 150), (0.6, 0.9),
     ["electronic", "synth", "drums"], ["action", "climax", "buildup"], True),
    ("异星文明", ["mysterious", "futuristic", "ethereal", "epic"], (65, 90), (0.25, 0.55),
     ["synth", "orchestra", "ambient", "electronic"], ["buildup", "intro", "transition"], True),
    ("神经网络", ["futuristic", "dark", "mysterious", "intense"], (80, 115), (0.35, 0.65),
     ["electronic", "synth", "drums", "ambient"], ["buildup", "action", "hook"], True),
    ("零点能", ["futuristic", "peaceful", "dreamy", "ethereal"], (45, 65), (0.1, 0.3),
     ["ambient", "synth", "electronic", "piano"], ["intro", "reflection", "ending"], False),
]

for i, (title, emotions, bpm_range, energy_range, instruments, usage_tags, with_climax) in enumerate(scifi_tracks):
    new_tracks.append(track(116 + i, title, emotions, bpm_range, scifi_keys, energy_range,
                            instruments, usage_tags, next_license(), with_climax=with_climax))

# ---- Tension/Chase: 10 tracks ----
tension_keys = ["C minor", "D minor", "E minor", "F minor", "G minor", "A minor", "B minor"]
tension_tracks = [
    ("生死时速", ["tense", "intense", "urgent", "action"], (120, 160), (0.7, 1.0),
     ["electronic", "drums", "strings", "brass"], ["action", "climax"], True),
    ("分秒必争", ["urgent", "tense", "intense"], (110, 150), (0.65, 0.95),
     ["drums", "electronic", "strings"], ["action", "climax", "transition"], True),
    ("暗夜飞车", ["intense", "action", "tense", "urgent"], (115, 155), (0.7, 0.95),
     ["electronic", "drums", "guitar", "strings"], ["action", "climax"], True),
    ("心跳加速", ["tense", "urgent", "intense"], (125, 160), (0.65, 0.9),
     ["electronic", "drums", "bass"], ["action", "transition", "buildup"], True),
    ("风暴来袭", ["intense", "urgent", "dramatic", "epic"], (100, 140), (0.6, 0.9),
     ["orchestra", "drums", "electronic", "strings"], ["action", "climax", "buildup"], True),
    ("穷追不舍", ["urgent", "tense", "action", "intense"], (130, 160), (0.7, 1.0),
     ["drums", "electronic", "brass", "strings"], ["action", "climax"], True),
    ("命悬一线", ["tense", "intense", "suspense", "urgent"], (100, 135), (0.55, 0.85),
     ["strings", "drums", "electronic"], ["buildup", "action", "climax"], True),
    ("危机四伏", ["tense", "suspense", "intense", "urgent"], (105, 140), (0.5, 0.8),
     ["electronic", "drums", "strings", "piano"], ["buildup", "action", "transition"], True),
    ("无路可退", ["intense", "action", "tense", "dramatic"], (110, 145), (0.6, 0.9),
     ["orchestra", "drums", "electronic", "brass"], ["climax", "action"], True),
    ("绝地反击", ["epic", "intense", "heroic", "action"], (115, 155), (0.7, 1.0),
     ["orchestra", "drums", "brass", "electronic"], ["climax", "action", "ending"], True),
]

for i, (title, emotions, bpm_range, energy_range, instruments, usage_tags, with_climax) in enumerate(tension_tracks):
    new_tracks.append(track(126 + i, title, emotions, bpm_range, tension_keys, energy_range,
                            instruments, usage_tags, next_license(), with_climax=with_climax))

# ---- Romance/Love: 6 tracks ----
romance_keys = ["C major", "G major", "F major", "A major", "D major", "E minor"]
romance_tracks = [
    ("初见心动", ["romantic", "warm", "emotional"], (55, 75), (0.15, 0.4),
     ["piano", "strings", "guitar"], ["intro", "reflection", "transition"], False),
    ("月下之约", ["romantic", "nostalgic", "warm", "dreamy"], (50, 70), (0.1, 0.35),
     ["piano", "strings", "flute"], ["reflection", "intro", "ending"], False),
    ("深情告白", ["romantic", "emotional", "warm"], (60, 80), (0.2, 0.45),
     ["piano", "strings", "guitar", "orchestra"], ["reflection", "transition", "ending"], False),
    ("执子之手", ["romantic", "hopeful", "warm", "emotional"], (55, 75), (0.2, 0.4),
     ["piano", "guitar", "strings"], ["reflection", "ending", "transition"], False),
    ("雨中漫步", ["romantic", "warm", "peaceful", "nostalgic"], (50, 70), (0.1, 0.3),
     ["piano", "guitar", "strings"], ["intro", "reflection", "transition"], False),
    ("永恒之爱", ["romantic", "emotional", "grand", "warm"], (55, 80), (0.2, 0.5),
     ["orchestra", "piano", "strings", "choir"], ["ending", "climax", "reflection"], True),
]

for i, (title, emotions, bpm_range, energy_range, instruments, usage_tags, with_climax) in enumerate(romance_tracks):
    new_tracks.append(track(136 + i, title, emotions, bpm_range, romance_keys, energy_range,
                            instruments, usage_tags, next_license(), with_climax=with_climax))

# ---- Reflection/Ending: 5 tracks ----
reflection_keys = ["C major", "G major", "F major", "A minor", "E minor", "D major"]
reflection_tracks = [
    ("片尾余韵", ["reflective", "emotional", "nostalgic", "peaceful"], (45, 65), (0.1, 0.3),
     ["piano", "strings", "guitar"], ["ending", "reflection"], False),
    ("告别时刻", ["sad", "nostalgic", "emotional", "reflective"], (40, 60), (0.1, 0.3),
     ["piano", "strings", "choir"], ["ending", "reflection"], False),
    ("回望来路", ["reflective", "nostalgic", "peaceful", "warm"], (45, 65), (0.1, 0.25),
     ["piano", "guitar", "ambient"], ["ending", "reflection", "transition"], False),
    ("未完待续", ["reflective", "hopeful", "warm", "emotional"], (50, 70), (0.15, 0.35),
     ["piano", "strings", "orchestra"], ["ending", "reflection", "buildup"], False),
    ("永恒之声", ["reflective", "grand", "emotional", "peaceful"], (50, 70), (0.15, 0.4),
     ["orchestra", "choir", "piano", "strings"], ["ending", "reflection", "climax"], True),
]

for i, (title, emotions, bpm_range, energy_range, instruments, usage_tags, with_climax) in enumerate(reflection_tracks):
    new_tracks.append(track(142 + i, title, emotions, bpm_range, reflection_keys, energy_range,
                            instruments, usage_tags, next_license(), with_climax=with_climax))

# === Assemble final library ===
all_tracks = existing_tracks + new_tracks

# Verify count
assert len(all_tracks) == 146, f"Expected 146 tracks, got {len(all_tracks)}"

# Verify cc0/licensed distribution
cc0_count = sum(1 for t in all_tracks if t["license_type"] == "cc0")
licensed_count = sum(1 for t in all_tracks if t["license_type"] == "licensed")
print(f"Total tracks: {len(all_tracks)}")
print(f"cc0: {cc0_count}, licensed: {licensed_count}")

# Verify unique IDs
ids = [t["track_id"] for t in all_tracks]
assert len(set(ids)) == 146, "Duplicate track IDs found!"
assert ids[0] == "bgm_001", "First ID should be bgm_001"
assert ids[-1] == "bgm_146", f"Last ID should be bgm_146, got {ids[-1]}"

# Category counts (informational)
print(f"\nCategories:")
print(f"  Existing (preserved): 5 (bgm_001 - bgm_005)")
print(f"  Suspense/Mystery: 20 (bgm_006 - bgm_025)")
print(f"  Action/Epic: 24 (bgm_026 - bgm_049)")
print(f"  Emotional/Warm: 24 (bgm_050 - bgm_073)")
print(f"  Horror/Terror: 14 (bgm_074 - bgm_087)")
print(f"  Comedy/Light: 14 (bgm_088 - bgm_101)")
print(f"  Oriental/Chinese: 14 (bgm_102 - bgm_115)")
print(f"  Sci-fi/Futuristic: 10 (bgm_116 - bgm_125)")
print(f"  Tension/Chase: 10 (bgm_126 - bgm_135)")
print(f"  Romance/Love: 6 (bgm_136 - bgm_141)")
print(f"  Reflection/Ending: 5 (bgm_142 - bgm_146)")
print(f"  Total new: 141")
print(f"  Grand total: 146")

# Write output
output = {"tracks": all_tracks}
output_path = r"F:\claude\movie-narration-web\backend\data\bgm_library.json"
with open(output_path, "w", encoding="utf-8") as f:
    json.dump(output, f, ensure_ascii=False, indent=2)

print(f"\nWritten to: {output_path}")
print("Done!")
