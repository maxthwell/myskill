# Data Visualization

Use this subskill when the caller provides a CSV long table with exactly three semantic columns:

1. Year
2. Category
3. Value

The script now supports only one output type: a matplotlib-rendered 2D visualization video.

## Output

- Combined visualization video:
  Render one MP4 containing:
  - an animated pie-share section
  - a horizontal bar-race section
  - a vertical bar section
  - a stock-style trend section

## Script Contract

Run:

```bash
python3 scripts/visualize_long_table.py --input <csv> --output <video.mp4>
```

Optional flags:

- `--title <text>`
- `--top-n <int>`: capped at `32`
- `--fps <int>`
- `--width <int>`
- `--height <int>`
- `--cpu`: accepted for compatibility and ignored

## Data Rules

- Parse the first three columns as `year`, `category`, `value`.
- Convert `value` to numeric and fail clearly on bad rows.
- Preserve category labels exactly as provided.
- Sort years numerically when possible; otherwise sort lexicographically.
- For repeated `(year, category)` rows, sum their values.
- Support at most `32` categories in one CSV.

## Visual Rules

- Use a white background by default.
- Assign category colors in a fixed 32-color sequence based on category order.
- Render the final video directly in `16:9`.
- Render all chart geometry through matplotlib and encode MP4 with `ffmpeg`.

## Failure Policy

- If the CSV is missing required columns, fail with a direct error.
- If plotting or encoding dependencies are unavailable, fail with a direct install/runtime error.
