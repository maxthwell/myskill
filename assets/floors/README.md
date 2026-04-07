Each floor lives as a flat asset in this directory.

Supported layout:

- `assets/floors/<id>.json`
- optional image beside it with the same stem, for example `assets/floors/wood-plank.png`

The runtime uses:

- `color` as fallback when no image is present
- `image_path` when a matching local image exists

Scene usage:

- canonical story: `"floor": "wood-plank"`
- compact story: `"floor": "wood-plank"`
