# Architecture

## Pipeline

`BaseVideoScript subclass -> story_package.json -> optional dialogue audio manifest -> renderer -> scene-aligned audio build -> mp4`

## Runtime folders

- `work/`: normalized `story_package.json` artifacts produced from Python story scripts
- `tmp/frames/`: rendered frame PNGs
- `tmp/audio/`: optional generated dialogue audio
- `tmp/scene_audio/`: scene-length intermediate audio beds, normalized scene tracks, and the final lossless combined story audio
- `outputs/`: final MP4 files

## Responsibilities

- `check_story_input.py`: load a Python story script, normalize it, validate it, and print a concise summary
- `normalize_story.py`: turn a Python story script into canonical `story_package.json`
- `validate_story.py`: enforce ids, timing, overlap, and manifest constraints
- `synthesize_tts.py`: best-effort dialogue audio generation with shared cache and per-line normalization
- `render_video.py`: use the pygame renderer, build scene-aligned audio, and `ffmpeg` encode the final MP4
- `storyboard/video_script.py`: defines `BaseVideoScript`, which centralizes CLI parsing, TTS policy, normalization, and direct rendering
- `generate_*.py`: main entrypoint scripts that define a `BaseVideoScript` subclass, instantiate `SCRIPT`, and render the final MP4 directly
- `agent_ready.py`: short readiness check for AI agents and weak models

## Rendering model

- 2D/2.5D staged renderer behind a normalized `story_package.json`
- Local background images or animations plus parallax accents
- Character cards with body, head, aura, and label layers
- Procedural prop cards
- Local foreground images or animations
- Per-frame subtitle overlay
- Named action effects rendered from local effect assets with alpha and brightness controls

## Action effects

Special-action beats stay deterministic. The renderer only implements effect ids that exist in the manifest and are explicitly referenced or inferred during normalization. v1 includes:

- `dragon-palm`
- `thunder-strike`
- `sword-arc`

`dragon-palm` is the schema-level answer for moves such as “降龙十八掌”.
