"""Render a complete narration video from a script JSON output.

Usage:
    python scripts/render_video.py <script_json_path> [--platform douyin] [--output output.mp4]

Example:
    python scripts/render_video.py output/shawshank_redemption_suspense_brainburn_douyin.json
    python scripts/render_video.py output/shawshank_redemption_suspense_brainburn_douyin.json --platform bilibili --output my_video.mp4
"""

import argparse
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

# Ensure app is importable
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.engines.template_renderer import (
    TemplateRenderer,
    PhotoCardConfig,
    EmotionCardConfig,
    CANVAS,
)
from app.engines.vdl_compiler import VDLCompiler, FFmpegCommand

# Emotion → visual config mapping
EMOTION_CONFIGS = {
    'suspense': EmotionCardConfig(emotion='SUSPENSE', emoji='🔍', text='', gradient_colors=('#1a1a2e', '#0f3460')),
    'shock_curiosity': EmotionCardConfig(emotion='SHOCK', emoji='😱', text='', gradient_colors=('#2d132c', '#801336')),
    'buildup': EmotionCardConfig(emotion='RISING', emoji='📈', text='', gradient_colors=('#1b262c', '#0f4c75')),
    'tense': EmotionCardConfig(emotion='TENSE', emoji='⚡', text='', gradient_colors=('#1a1a2e', '#533483')),
    'revelation': EmotionCardConfig(emotion='REVEAL', emoji='💡', text='', gradient_colors=('#1b4332', '#40916c')),
    'climax': EmotionCardConfig(emotion='CLIMAX', emoji='🔥', text='', gradient_colors=('#3d0000', '#950101')),
    'reflection': EmotionCardConfig(emotion='REFLECTION', emoji='💭', text='', gradient_colors=('#1a1a2e', '#16213e')),
    'hope': EmotionCardConfig(emotion='HOPE', emoji='✨', text='', gradient_colors=('#0d1b2a', '#1b6ca8')),
    'comedy': EmotionCardConfig(emotion='FUNNY', emoji='😂', text='', gradient_colors=('#ff7b00', '#ffb703')),
    'surprise': EmotionCardConfig(emotion='WOW', emoji='🤯', text='', gradient_colors=('#6a0572', '#c77dff')),
}


def generate_silent_audio(duration_sec: float, output_path: str) -> str:
    """Generate a silent AAC audio file of given duration using FFmpeg."""
    subprocess.run([
        'ffmpeg', '-y', '-f', 'lavfi',
        '-i', f'anullsrc=r=44100:cl=mono',
        '-t', str(duration_sec),
        '-c:a', 'aac', '-b:a', '64k',
        output_path,
    ], capture_output=True, text=True, timeout=30)
    return output_path


def render_script_to_video(script_path: str, platform: str = 'douyin', output_path: str = 'output.mp4') -> str:
    """Render a script JSON to a complete video.

    Pipeline:
    1. Parse script JSON → extract segments
    2. For each segment, render a visual template frame
    3. Generate silent audio placeholders
    4. Compile VDL → FFmpeg command → execute
    """
    # Load script
    with open(script_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    script = data.get('script', data)
    segments = script.get('script_segments', script.get('segments', []))
    if not segments and 'variants' in script:
        # Script with variants — take the best
        best = script.get('best_variant') or script['variants'][0]
        segments = best.get('segments', [])

    if not segments:
        print('[ERROR] No segments found in script')
        sys.exit(1)

    print(f'Rendering {len(segments)} segments to {platform} video...')

    canvas_size = CANVAS.get(platform, (1080, 1920))
    renderer = TemplateRenderer(canvas_size=canvas_size)

    tmp_dir = Path(tempfile.mkdtemp(prefix='mnw_render_'))
    print(f'  Temp dir: {tmp_dir}')

    # Render each segment
    frame_files = []
    audio_files = []
    total_duration = 0.0

    for i, seg in enumerate(segments):
        text = seg.get('text', f'Segment {i + 1}')
        emotion = seg.get('emotion', 'neutral')
        duration = seg.get('estimated_duration_sec', 12.0)

        print(f'  Segment {i + 1}/{len(segments)}: {seg.get("type", "?")} ({emotion}) — {duration:.1f}s')

        # Render visual template
        emotion_cfg = EMOTION_CONFIGS.get(emotion, EMOTION_CONFIGS['reflection'])
        emotion_cfg.text = text[:150] + '...' if len(text) > 150 else text

        result = renderer.render_emotion_card(emotion_cfg)

        # Convert PNG to short MP4 clip using FFmpeg
        clip_path = str(tmp_dir / f'seg_{i:02d}.mp4')
        subprocess.run([
            'ffmpeg', '-y',
            '-loop', '1',
            '-i', result.image_path,
            '-c:v', 'libx264',
            '-t', str(duration),
            '-pix_fmt', 'yuv420p',
            '-vf', f'scale={canvas_size[0]}:{canvas_size[1]}',
            clip_path,
        ], capture_output=True, text=True, timeout=30)

        frame_files.append(clip_path)

        # Generate silent audio placeholder
        audio_path = str(tmp_dir / f'audio_{i:02d}.aac')
        generate_silent_audio(duration, audio_path)
        audio_files.append(audio_path)

        total_duration += duration

    # Build FFmpeg concat command directly
    # Create input list
    input_args = []
    filter_parts = []
    for i in range(len(segments)):
        input_args.extend(['-i', frame_files[i]])
        input_args.extend(['-i', audio_files[i]])

    # Build concat filter
    video_inputs = ''.join(f'[{i * 2}:v]' for i in range(len(segments)))
    audio_inputs = ''.join(f'[{i * 2 + 1}:a]' for i in range(len(segments)))

    concat_filter = (
        f'{video_inputs}concat=n={len(segments)}:v=1:a=0[out_v];'
        f'{audio_inputs}concat=n={len(segments)}:v=0:a=1[out_a]'
    )

    # Build full command
    cmd = [
        'ffmpeg', '-y',
        *input_args,
        '-filter_complex', concat_filter,
        '-map', '[out_v]',
        '-map', '[out_a]',
        '-c:v', 'libx264',
        '-preset', 'medium',
        '-crf', '18',
        '-c:a', 'aac',
        '-b:a', '192k',
        '-pix_fmt', 'yuv420p',
        '-movflags', '+faststart',
        '-shortest',
        output_path,
    ]

    print(f'\n  Composing final video ({total_duration:.1f}s)...')
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)

    if result.returncode == 0:
        file_size = os.path.getsize(output_path) / 1024 / 1024
        print(f'  [OK] Video rendered: {output_path} ({file_size:.1f} MB, {total_duration:.1f}s)')
    else:
        print(f'  [FAIL] FFmpeg error:\n{result.stderr[-500:]}')

    # Cleanup temp files
    import shutil
    shutil.rmtree(tmp_dir, ignore_errors=True)

    return output_path


def main():
    parser = argparse.ArgumentParser(description='Render narration video from script JSON')
    parser.add_argument('script', help='Path to script JSON file')
    parser.add_argument('--platform', default='douyin',
                        choices=['douyin', 'bilibili', 'kuaishou', 'xiaohongshu'],
                        help='Target platform (default: douyin)')
    parser.add_argument('--output', default=None,
                        help='Output video path (default: <script_name>_<platform>.mp4)')
    args = parser.parse_args()

    if args.output is None:
        script_stem = Path(args.script).stem
        args.output = f'{script_stem}_{args.platform}.mp4'

    # Convert to absolute path in output dir
    output_dir = Path(__file__).parent.parent / 'output'
    output_dir.mkdir(exist_ok=True)
    output_path = str(output_dir / args.output)

    render_script_to_video(args.script, args.platform, output_path)


if __name__ == '__main__':
    main()
