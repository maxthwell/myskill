# Trigger And Workflow

Use this skill when the caller wants a local video generated or edited in this repo: story videos, wuxia/xianxia clips, action showcases, TTS videos, BGM/effects/audio-heavy videos, or fixes to an existing `scripts/generate_*.py` script.

## Preferred flow

1. Verify the skill is ready:

```bash
python3 scripts/agent_ready.py
```

2. Inspect real local assets:

```bash
python3 scripts/list_assets.py --pretty
```

3. Reuse the closest existing generator under `scripts/generate_*.py`.

4. Validate before rendering:

```bash
python3 scripts/check_story_input.py --input scripts/generate_my_story.py
```

5. Render:

```bash
python3 scripts/generate_my_story.py --cpu --output outputs/story.mp4
```

For long TTS-heavy stories:

```bash
python3 scripts/generate_my_story.py --cpu --tts-workers 4 --scene-workers 2 --output outputs/story.mp4
```

## Rules for weak models

- Use only relative paths.
- Start from an existing generator when possible.
- Do not invent asset ids.
- Do not skip validation before a long render.
- If the user asks for a quick result, prefer editing one script and running it directly.
