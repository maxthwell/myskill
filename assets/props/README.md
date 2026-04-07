Dynamic prop assets live here.

Each subdirectory becomes one auto-discovered prop id.

Minimal structure:

generated_props/<prop-id>/
  asset.png

Optional:

generated_props/<prop-id>/
  asset.gif
  prop.json

Supported asset filenames:
- asset.png / asset.webp / asset.gif / asset.svg
- sprite.png / sprite.webp / sprite.gif / sprite.svg
- image.png / image.webp / image.gif / image.svg
- preview.png / preview.webp / preview.gif / preview.svg

Example prop.json:

{
  "display_name": "Little Dog",
  "category": "animal",
  "default_layer": "front",
  "anchor": [0.5, 1.0],
  "base_width": 160,
  "base_height": 120,
  "animated": true,
  "seat_height": 0
}

Notes:
- Animated gif/webp props will play inside each scene.
- Static png/webp/svg props are also supported.
- A scene can place the prop by setting `prop_id` to the directory name.
- Animal props move by default.
- Optional motion fields:
  - `motion`: `animal`, `hop`, `float`, `drift`
  - `motion_x`
  - `motion_y`
  - `motion_period_ms`
