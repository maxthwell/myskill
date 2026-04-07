# Scene Schema

## Accepted public input mode

The public mainline accepts:

- A Python story script that exposes `SCRIPT`, `VIDEO_SCRIPT`, `build_story()`, or `STORY`

All downstream runtime stages consume the canonical artifact at `work/story_package.json`.

## Internal canonical story package

Top-level keys:

- `meta`
- `video`
- `cast`
- `assets`
- `scenes`

## `video`

- `width`
- `height`
- `fps`
- `subtitle_mode`
- `tts_enabled`
- `tts_workers`
- `scene_workers`
- `encoder_preset`
- `crf`

Defaults:

- `width=960`
- `height=540`
- `fps=12`
- `subtitle_mode=bottom`
- `tts_enabled=false`
- `tts_workers` defaults to an internal auto value based on CPU count
- `scene_workers` defaults to an internal auto value based on CPU count and scene count
- `encoder_preset=medium`
- `crf=23`

## `cast[]`

- `id`
- `display_name`
- `asset_id`
- `voice`
- `color_variant` optional

## `assets`

- `backgrounds`
- `floors`
- `props`
- `motions`
- `effects`
- `foregrounds`
- `audio`
- `bgm`

## `scenes[]`

- `id`
- `background`
- `floor`
- `duration_ms`
- `summary`
- `camera`
- `effects[]`
- `props[]`
- `actors[]`
- `npc_groups[]`
- `beats[]`
- `expressions[]`
- `dialogues[]`
- `audio`
- `box`

## `camera`

- `type`
- `x`
- `z`
- `zoom`
- `to_x`
- `to_z`
- `to_zoom`
- `ease`

`type` supports `static` and `pan`. `pan` interpolates from `x/z/zoom` to `to_x/to_z/to_zoom` across the scene duration.

## `props[]`

- `prop_id`
- `x`
- `z`
- `scale`
- `layer`
- `mount`
- `image_url`

`image_url` is only supported on props. Backgrounds and foregrounds are local assets discovered from `assets/backgrounds` and `assets/foreground`.
`mount` supports `free`, `back-wall`, `left-wall`, `right-wall`, `outside-back`, `outside-left`, and `outside-right`.

## `box`

- `width`
- `height`
- `depth`
- `wall_image_url`
- `back_wall_image_url`
- `left_wall_image_url`
- `right_wall_image_url`
- `floor_image_url`
- `ceiling_image_url`
- `outside_image_url`
- `outside_back_image_url`
- `outside_left_image_url`
- `outside_right_image_url`
- `wall_color`
- `back_wall_color`
- `left_wall_color`
- `right_wall_color`
- `floor_color`
- `ceiling_color`

`box` defines the room shell. Actors and props render inside this cuboid room.

## `actors[]`

- `actor_id`
- `spawn`
- `scale`
- `layer`
- `facing`

`spawn`, `from`, and `to` use:

- `x`
- `z`

## `npc_groups[]`

- `id`
- `count`
- `asset_id` or `asset_ids[]`
- `behavior`
- `target_actor_id` optional
- `layer`
- `speed`
- `arrival_distance`
- `evade_distance`
- `relax_distance`
- `wander_radius`
- `wander_aoi`
- `seek_weight`
- `scale`, or `scale_min` and `scale_max`
- `anchor`
- `area`
- `watch`

Supported v1 NPC behaviors:

- `wander`
- `seek`
- `pursue`
- `evade`
- `guard`

`anchor` uses:

- `x`
- `frontness`

`area` uses:

- `x_min`
- `x_max`
- `front_min`
- `front_max`

NPC groups are anonymous background participants. They do not need entries in `cast[]`, do not speak, and are driven by the local staged renderer.

## `beats[]`

- `start_ms`
- `end_ms`
- `actor_id`
- `motion`
- `from`
- `to`
- `facing`
- `emotion`
- `expression` optional
- `effect`
- `target_id` optional

Supported v1 motions:

Use `python3 scripts/list_assets.py --category motions` as the source of truth.
Common ids include:

- `idle`
- `talk`
- `enter`
- `exit`
- `point`
- `nod`
- `flying-kick`
- `somersault`
- `double-palm-push`
- `spin-kick`
- `diagonal-kick`
- `hook-punch`
- `swing-punch`
- `straight-punch`
- `combo-punch`
- `dragon-palm`
- `thunder-strike`
- `sword-arc`

## `dialogues[]`

- `start_ms`
- `end_ms`
- `speaker_id`
- `text`
- `subtitle`
- `voice`
- `bubble`

## `expressions[]`

- `actor_id`
- `start_ms`
- `end_ms`
- `expression`

Supported v1 expressions:

- `neutral`
- `talk`
- `explain`
- `smirk`
- `fierce`
- `awkward`
- `deadpan`
- `hurt`

## Constraints

- `0 <= start_ms < end_ms <= duration_ms`
- actor ids must exist in `cast`
- `actors[]` is still capped at 4 principal performers; use `npc_groups[]` for extra crowd participants
- manifest ids must exist in `assets/manifests/*.json`
- dialogue windows must not overlap
- beat windows for the same actor must not overlap
- expression windows for the same actor must not overlap
- scenes may contain many dialogue turns, but only one active line at a time
- scenes may contain multiple effect declarations, but v1 renders at most one named action effect at a time per actor
- render priority is `scene.expressions > beat.expression > automatic expression inference from emotion/motion/dialogue`
