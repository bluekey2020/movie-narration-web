"""Validate the generated BGM library JSON."""
import json
import sys

with open('F:/claude/movie-narration-web/backend/data/bgm_library.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

tracks = data['tracks']
errors = []

print(f'Total tracks: {len(tracks)}')
ids = [t['track_id'] for t in tracks]
expected_ids = [f'bgm_{i:03d}' for i in range(1, 147)]
if ids != expected_ids:
    errors.append(f'ID mismatch')
else:
    print('ID sequence: OK')

# Field validations
required = ['track_id','title','duration_sec','emotions','bpm','key','energy','instruments','sections','natural_cut_points','usage_tags','license_type','file_path']
for t in tracks:
    tid = t.get('track_id', '?')
    for r in required:
        if r not in t:
            errors.append(f'{tid}: MISSING FIELD {r}')
    dur = t.get('duration_sec', 0)
    bpm = t.get('bpm', 0)
    eng = t.get('energy', 0)
    if not (60 <= dur <= 240):
        errors.append(f'{tid}: duration {dur} out of range')
    if not (40 <= bpm <= 160):
        errors.append(f'{tid}: bpm {bpm} out of range')
    if not (0.1 <= eng <= 1.0):
        errors.append(f'{tid}: energy {eng} out of range')
    if not (1 <= len(t.get('emotions', [])) <= 4):
        errors.append(f'{tid}: emotions count {len(t.get("emotions", []))}')
    if len(t.get('instruments', [])) < 1:
        errors.append(f'{tid}: instruments empty')
    if len(t.get('sections', [])) < 2:
        errors.append(f'{tid}: sections count {len(t.get("sections", []))}')
    if len(t.get('usage_tags', [])) < 1:
        errors.append(f'{tid}: usage_tags empty')

if not errors:
    print('All field validations: OK')

# License distribution
cc0 = sum(1 for t in tracks if t['license_type'] == 'cc0')
licensed = sum(1 for t in tracks if t['license_type'] == 'licensed')
print(f'cc0: {cc0}, licensed: {licensed}')
if cc0 != 100:
    errors.append(f'Expected 100 cc0, got {cc0}')
if licensed != 46:
    errors.append(f'Expected 46 licensed, got {licensed}')

# Existing tracks
if tracks[0]['title'] != '悬疑铺垫':
    errors.append('bgm_001 title mismatch')
if tracks[1]['title'] != '紧张追逐':
    errors.append('bgm_002 title mismatch')
if tracks[2]['title'] != '史诗高潮':
    errors.append('bgm_003 title mismatch')
if tracks[3]['title'] != '温暖回忆':
    errors.append('bgm_004 title mismatch')
if tracks[4]['title'] != '暗黑氛围':
    errors.append('bgm_005 title mismatch')
if not any(e.startswith('bgm_00') and 'title' in e for e in errors):
    print('Existing 5 tracks preserved: OK')

# File path format for new tracks
fp_errors = 0
for t in tracks[5:]:
    expected = f'/bgm/{t["track_id"]}.mp3'
    if t['file_path'] != expected:
        fp_errors += 1
if fp_errors > 0:
    errors.append(f'{fp_errors} tracks have wrong file_path')
else:
    print('file_path format: OK')

# Unique titles
titles = [t['title'] for t in tracks]
if len(titles) != len(set(titles)):
    seen = {}
    for t in tracks:
        ti = t['title']
        if ti in seen:
            errors.append(f'Duplicate title: {ti} ({seen[ti]}, {t["track_id"]})')
        seen[ti] = t['track_id']
else:
    print('Unique titles: OK')

# Range checks per category
categories = {
    'Suspense/Mystery (6-25)': (6, 25),
    'Action/Epic (26-49)': (26, 49),
    'Emotional/Warm (50-73)': (50, 73),
    'Horror/Terror (74-87)': (74, 87),
    'Comedy/Light (88-101)': (88, 101),
    'Oriental/Chinese (102-115)': (102, 115),
    'Sci-fi/Futuristic (116-125)': (116, 125),
    'Tension/Chase (126-135)': (126, 135),
    'Romance/Love (136-141)': (136, 141),
    'Reflection/Ending (142-146)': (142, 146),
}

print()
for cat, (start, end) in categories.items():
    cat_tracks = [t for t in tracks if start <= int(t['track_id'].split('_')[1]) <= end]
    print(f'{cat}: {len(cat_tracks)} tracks')
    if len(cat_tracks) != (end - start + 1):
        errors.append(f'{cat}: expected {end-start+1}, got {len(cat_tracks)}')

if errors:
    print(f'\nERRORS ({len(errors)}):')
    for e in errors:
        print(f'  - {e}')
    sys.exit(1)
else:
    print('\nALL VALIDATIONS PASSED')
    sys.exit(0)
