---
name: pygame-agent-video
description: >-
  Maintain and render exactly one local video pipeline: the cangyun mainline
  under scripts/generate_cangyun_escort_story.py, backed by DNN pose detection
  and Panda3D scene rendering. This skill is optimized for weak models: never
  invent a second pipeline, never use deleted legacy generators, always inspect
  local assets first, update pose caches when actions change, and render by
  running the cangyun generator directly.
---

# Single-Chain Video Skill

This skill supports one maintained pipeline only:

- Main story generator: `scripts/generate_cangyun_escort_story.py`
- DNN pose extractor: `scripts/extract_action_poses.py`
- Shared pose renderer/model code: `scripts/generate_actions_pose_reconstruction.py`
- Shared Panda3D renderer: `scripts/common/panda_true3d_renderer.py`
- Runtime helpers: `scripts/check_env.py`, `scripts/agent_ready.py`, `scripts/list_assets.py`

Everything else is legacy and must not be recreated.

## Non-Negotiable Rules

- Only use the cangyun mainline. Do not create or maintain a second story pipeline.
- Render story video frames with Panda3D only. Do not bring back PIL frame rendering or pygame-based rendering paths.
- When a local DNN pose track exists for an action, Panda3D should consume that pose track directly. Do not downgrade it to a canned motion if `assets/actions/.cache/poses/*.pose.json` is available.
- Do not use built-in canned fight motions as the source of body acting. Predefined motion names may exist only as timing metadata, but visible limb posing should come from DNN pose tracks or a neutral static fallback.
- Do not resurrect deleted `generate_*.py`, `storyboard`, `pygame_renderer`, or legacy panda renderer code.
- If the user wants a new story, implement it by editing `scripts/generate_cangyun_escort_story.py`.
- If `assets/actions` changed, run `scripts/extract_action_poses.py` before rendering.
- Only use local assets from this repo. Never reference remote assets or external URLs.
- Prefer `--fast3` for previews and iteration. Use normal mode only for final quality when requested.
- Keep commands relative to the skill root.

## Exact Weak-Model Workflow

Use this order. Do not skip steps unless the user explicitly says to.

1. Check runtime:

```bash
python3 scripts/check_env.py
python3 scripts/agent_ready.py
```

2. Inspect local assets:

```bash
python3 scripts/list_assets.py --pretty
```

3. If the user changed action GIF/WebP resources, refresh pose caches:

```bash
python3 scripts/extract_action_poses.py
```

4. Edit only the cangyun generator:

```bash
scripts/generate_cangyun_escort_story.py
```

Typical edits:

- rewrite `TITLE`
- rewrite `SCENES`
- adjust actors, lines, expressions, BGM, SFX, effects
- when a scene needs richer acting, add `expression_cues` so one actor can change face multiple times inside the same scene
- when acting still feels stiff, adjust the shared automatic expression cadence in `scripts/generate_cangyun_escort_story.py` instead of hardcoding one face per scene
- keep using `generate_actions_pose_reconstruction.py` as the shared DNN stickman backend
- keep using `scripts/common/panda_true3d_renderer.py` as the only scene renderer
- when Panda3D actors perform an action that has a local DNN pose cache, pass the pose track path into Panda3D scene data and let Panda3D render the stickman/body from that DNN track instead of faking it with only a named motion
- if a scene/action has no local DNN pose cache, do not invent a fake martial move. Keep the actor in a neutral static pose, or choose a different local action asset that does have a pose cache

5. Render:

Preview:

```bash
python3 scripts/generate_cangyun_escort_story.py --fast3 --force --output outputs/preview.mp4
```

Higher quality:

```bash
python3 scripts/generate_cangyun_escort_story.py --force --output outputs/final.mp4
```

## What To Touch

- `scripts/generate_cangyun_escort_story.py`
- `scripts/generate_actions_pose_reconstruction.py`
- `scripts/extract_action_poses.py`
- `scripts/check_env.py`
- `scripts/agent_ready.py`
- `scripts/list_assets.py`
- `SKILL.md`

## What Not To Touch

- Do not add a new renderer stack.
- Do not add a new `generate_*story*.py` script unless the user explicitly asks to fork the mainline.
- Do not reintroduce `storyboard` workflows.
- Do not use `scripts/run_pipeline.py` or `scripts/render_video.py`.
- Do not route story generation through `common/panda_renderer.py` or `common/pygame_renderer.py`.
- Do not reintroduce a PIL per-frame compositor for the story generator once Panda3D is available.

## Asset Selection Rules

- Characters: use `assets/characters`
- Actions: use `assets/actions` and `assets/actions/.cache/poses`
- Backgrounds: use `assets/backgrounds`
- Effects: use `assets/effects`
- SFX: use `assets/audio`
- BGM: use `assets/bgm`

Always prefer actual filenames or ids returned by `scripts/list_assets.py`.

## Soft Constraints

These are strong quality hints, not hard blockers. Follow them by default unless the user asks for a different style.

- Prefer continuous storytelling over scene-by-scene reset. Adjacent scenes that are strongly connected should feel like one dramatic passage.
- Do not switch BGM at every scene boundary by default. If several consecutive scenes belong to the same emotional or narrative beat, keep the same BGM and continue its playback instead of restarting from the beginning.
- Use BGM changes mainly for major phase changes:
  opening, investigation, chase, battle, aftermath, finale.
- Let dialogue carry the story. In dialogue scenes, allow each character to speak multiple times when needed instead of forcing one line per character.
- Keep expressions active. Characters should change expression with emotion, pressure, surprise, anger, relief, or speaking state rather than staying on one face for a whole scene.
- A single scene should usually contain multiple expression changes for important characters. Do not assume one scene equals one expression.
- Do not let expression switches happen at perfectly fixed intervals. Use a base cadence plus small per-character timing error so changes feel organic instead of synchronized.
- The default expression rhythm should be frequent. As a baseline, important characters should usually change face about every 2-3 seconds, with jitter, unless the user asks for a calmer style.
- Prefer explicit in-scene expression timing when the acting matters. Use `expression_cues` in the scene data, for example:
  `expression_cues=(ExpressionCue("qiao", 0.0, "neutral"), ExpressionCue("qiao", 1.2, "angry"), ExpressionCue("qiao", 2.4, "sad"))`
- Treat each speaking line as an implicit expression change at its start, then use `expression_cues` to add finer beats inside or between lines.
- If an expression name is missing for a character, map it to the closest available local skin instead of silently leaving the face unchanged for the whole scene.
- Once the mainline resolves an expression to a real local face skin name, pass that exact expression name through to Panda3D. Do not collapse it again into generic buckets like `neutral`, `smirk`, `hurt`, or `fierce`.
- Speaking should prefer the same expression's local `face_talk_*` variants when they exist. Do not replace a character's chosen expression with an unrelated generic talking face.
- Non-speaking characters should not freeze like cardboard. In preview and final renders, keep low-amplitude idle pose motion and reaction expressions for bystanders.
- Scene transitions should preserve momentum. Do not make a new scene feel like a brand-new unrelated short clip unless the script truly jumps in time or place.
- SFX and visual effects should match the exact dramatic event:
  thunder with thunder, impact with hits, fire with burning or explosions.
- Scene loudness should feel globally consistent. Do not let one scene become obviously louder or quieter than its neighbors unless the user explicitly wants that contrast.
- By default, normalize mixed scene audio toward one shared loudness target after BGM, TTS, and SFX are combined. Do not rely only on raw per-track volume guesses.
- Effects are usually better as timed accents than full-scene loops. Prefer event-aligned bursts unless the user explicitly wants persistent weather or atmosphere.
- When several neighboring scenes form one action sequence, keep staging, tone, and audio language consistent across the whole run.
- Prefer fewer, better-motivated BGM tracks over frequent switching.
- By default, do not show scene-introduction cards or per-scene title blocks. Only keep them if the user explicitly asks for visible scene titles.
- By default, subtitles should show dialogue text only, not `speaker:` labels, unless the user explicitly asks for speaker names.
- Head-face compositing should cover the head ellipse as fully as possible. If face textures leave a visible unused rim, enlarge the face placement before changing head size.
- The character face should fill the panda head as completely as possible. Prefer same-center, same-rotation compositing against the panda head card before increasing head size.
- Head outlines should avoid harsh pure black by default. Prefer lighter gray outlines for the head contour unless a harsher comic style is requested.
- Default camera framing should stay a little closer to the actors than the widest safe room framing. If the user says characters feel too far away, tighten the Panda3D camera before changing actor scale.
- Shoulder-neck silhouettes should be narrow and smooth. Prefer a refined torso polygon over a hard boxy shoulder block when the user asks for slimmer anatomy.
- Arm layering should respect clothing depth. Default order for clothed characters is:
  upper arm first, then torso/clothes, then lower arm and wrist/hand on top.
- Arm roots should not connect to the torso at a single exposed point. Sink upper-arm roots slightly into the torso silhouette so the arm visually emerges from the body instead of pin-attaching.
- When the user gives repeated art-direction corrections, encode them into the shared renderer or this `SKILL.md` rather than fixing one scene only.

## Fast Decision Rules For Weak Models

- User asks for a new story video:
  edit `scripts/generate_cangyun_escort_story.py`

- User says actions changed:
  run `python3 scripts/extract_action_poses.py`

- User says expressions/pose/head/body rendering is wrong:
  patch `scripts/generate_actions_pose_reconstruction.py`

- User says story rendering must use Panda3D or asks to remove PIL/pygame rendering:
  patch `scripts/generate_cangyun_escort_story.py` and `scripts/common/panda_true3d_renderer.py`, then delete dead fallback rendering code instead of keeping parallel engines

- User says Panda3D should support DNN stickman actions:
  patch `scripts/generate_cangyun_escort_story.py` so beats carry `pose_track_path`, then patch `scripts/common/panda_true3d_renderer.py` so actor posing consumes the DNN pose track instead of only named canned motions

- User says built-in actions should be removed:
  patch `scripts/generate_cangyun_escort_story.py` so beats are emitted only when a local DNN pose track exists, and patch `scripts/common/panda_true3d_renderer.py` so the non-pose fallback is neutral static posing rather than canned combat animation

- User says acting still feels stiff or synchronized:
  patch the expression cadence or reaction logic in `scripts/generate_cangyun_escort_story.py`

- User says subtitles, scene cards, or speaker labels are distracting:
  patch the UI drawing in `scripts/generate_cangyun_escort_story.py`

- User says shoulders, neck, clothing overlap, or arm-body connection looks wrong:
  patch the shared body geometry in `scripts/generate_actions_pose_reconstruction.py`

- User says scene volumes feel inconsistent:
  patch the scene audio normalization in `scripts/generate_cangyun_escort_story.py`

- User says assets are missing or command fails:
  run `python3 scripts/check_env.py` and `python3 scripts/agent_ready.py`

- User wants output now:
  render with `--fast3` first

## Minimal Command Set

```bash
python3 scripts/check_env.py
python3 scripts/agent_ready.py
python3 scripts/list_assets.py --pretty
python3 scripts/extract_action_poses.py
python3 scripts/generate_cangyun_escort_story.py --fast3 --force --output outputs/preview.mp4
python3 scripts/generate_cangyun_escort_story.py --force --output outputs/final.mp4
```
