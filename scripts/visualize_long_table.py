#!/usr/bin/env python3
from __future__ import annotations

import argparse
import os
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

os.environ.setdefault("MPLCONFIGDIR", "/tmp/matplotlib")

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib import font_manager
from matplotlib.patches import Rectangle


MAX_CATEGORIES = 32
BACKGROUND = "#ffffff"
TEXT = "#16202a"
MUTED = "#6d7e8e"
GRID = "#dde4ec"
FRAME = "#edf2f6"
YEAR = "#c3cfdb"
PIE_EDGE = "#ffffff"
SEQUENTIAL_32 = [
    "#1f77b4", "#ff7f0e", "#2ca02c", "#d62728", "#9467bd", "#8c564b", "#e377c2", "#7f7f7f",
    "#bcbd22", "#17becf", "#393b79", "#637939", "#8c6d31", "#843c39", "#7b4173", "#3182bd",
    "#31a354", "#756bb1", "#636363", "#e6550d", "#969696", "#dd1c77", "#6baed6", "#74c476",
    "#9e9ac8", "#bdbdbd", "#fd8d3c", "#fdae6b", "#9ecae1", "#a1d99b", "#c7e9c0", "#fdd0a2",
]


@dataclass(frozen=True)
class Segment:
    key: str
    label: str
    frames: int


def configure_fonts() -> None:
    font_paths = [
        Path("/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc"),
        Path("/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc"),
        Path("/usr/share/fonts/truetype/droid/DroidSansFallbackFull.ttf"),
    ]
    families: list[str] = []
    for path in font_paths:
        if not path.exists():
            continue
        font_manager.fontManager.addfont(str(path))
        families.append(font_manager.FontProperties(fname=str(path)).get_name())

    matplotlib.rcParams["font.family"] = families[0] if families else "DejaVu Sans"
    matplotlib.rcParams["font.sans-serif"] = [*families, "DejaVu Sans"]
    matplotlib.rcParams["axes.unicode_minus"] = False


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Render a year-category-value long-table CSV into a matplotlib MP4 visualization video.")
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True, help="Output MP4 path")
    parser.add_argument("--title", default="", help="Optional title prefix for generated charts")
    parser.add_argument("--top-n", type=int, default=8, help="Top categories to keep in bar sections")
    parser.add_argument("--fps", type=int, default=24, help="Frame rate for the MP4 visualization video")
    parser.add_argument("--width", type=int, default=1920)
    parser.add_argument("--height", type=int, default=1080)
    parser.add_argument("--cpu", action="store_true", help="Accepted for compatibility. Ignored in matplotlib mode.")
    return parser.parse_args()


def sort_year_labels(values: Iterable[str]) -> list[str]:
    def key(item: str):
        text = str(item)
        try:
            return (0, float(text), text)
        except ValueError:
            return (1, text, text)

    return sorted({str(item) for item in values}, key=key)


def load_long_table(path: Path) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(f"input CSV not found: {path}")

    frame = pd.read_csv(path)
    if frame.shape[1] < 3:
        raise ValueError("expected at least three columns: year, category, value")

    normalized = frame.iloc[:, :3].copy()
    normalized.columns = ["year", "category", "value"]
    normalized["year"] = normalized["year"].astype(str).str.strip()
    normalized["category"] = normalized["category"].astype(str).str.strip()
    normalized["value"] = pd.to_numeric(normalized["value"], errors="raise")
    normalized = normalized[(normalized["year"] != "") & (normalized["category"] != "")]
    if normalized.empty:
        raise ValueError("input CSV has no usable rows after normalization")

    grouped = normalized.groupby(["year", "category"], as_index=False)["value"].sum()
    if grouped["category"].nunique() > MAX_CATEGORIES:
        raise ValueError(f"expected at most {MAX_CATEGORIES} categories, got {grouped['category'].nunique()}")

    ordered_years = sort_year_labels(grouped["year"])
    grouped["year"] = pd.Categorical(grouped["year"], categories=ordered_years, ordered=True)
    return grouped.sort_values(["year", "category"]).reset_index(drop=True)


def build_pivot(frame: pd.DataFrame) -> pd.DataFrame:
    pivot = frame.pivot(index="year", columns="category", values="value").fillna(0.0)
    return pivot.astype(float)


def category_palette(categories: Iterable[str]) -> dict[str, str]:
    ordered = [str(category) for category in categories]
    return {category: SEQUENTIAL_32[index % len(SEQUENTIAL_32)] for index, category in enumerate(ordered)}


def interpolated_values(pivot: pd.DataFrame, progress: float) -> tuple[pd.Series, str]:
    years = [str(item) for item in pivot.index]
    if len(years) == 1:
        return pivot.iloc[0].astype(float), years[0]

    clamped = max(0.0, min(float(progress), float(len(years) - 1)))
    base_index = int(np.floor(clamped))
    next_index = min(base_index + 1, len(years) - 1)
    tween = clamped - base_index
    current = pivot.iloc[base_index].astype(float)
    target = pivot.iloc[next_index].astype(float)
    label = years[next_index] if tween >= 0.5 else years[base_index]
    return current + (target - current) * tween, label


def top_series(values: pd.Series, top_n: int) -> pd.Series:
    return values.sort_values(ascending=False).head(top_n)


def fit_fontsize(text: str, base_size: float, max_chars: int) -> float:
    if len(text) <= max_chars:
        return base_size
    return max(base_size * max_chars / max(1, len(text)), base_size * 0.55)


def open_ffmpeg_stream(output_path: Path, fps: int, width: int, height: int) -> subprocess.Popen:
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        raise RuntimeError("ffmpeg is required to encode the final video")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    command = [
        ffmpeg,
        "-y",
        "-f",
        "rawvideo",
        "-pix_fmt",
        "rgb24",
        "-s",
        f"{width}x{height}",
        "-framerate",
        str(fps),
        "-i",
        "-",
        "-c:v",
        "libx264",
        "-pix_fmt",
        "yuv420p",
        "-preset",
        "medium",
        "-crf",
        "18",
        str(output_path),
    ]
    return subprocess.Popen(command, stdin=subprocess.PIPE)


def remux_faststart(path: Path) -> Path:
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        return path
    faststart = path.with_name(f"{path.stem}_faststart{path.suffix}")
    subprocess.run(
        [ffmpeg, "-y", "-i", str(path), "-c", "copy", "-movflags", "+faststart", str(faststart)],
        check=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    return faststart


def figure_to_rgb_bytes(fig: plt.Figure) -> bytes:
    fig.canvas.draw()
    rgba = np.asarray(fig.canvas.buffer_rgba())
    return np.ascontiguousarray(rgba[:, :, :3]).tobytes()


def make_figure(width: int, height: int) -> plt.Figure:
    dpi = 120
    return plt.figure(figsize=(width / dpi, height / dpi), dpi=dpi, facecolor=BACKGROUND)


def draw_header(fig: plt.Figure, title: str, year_label: str) -> None:
    fig.text(0.055, 0.95, title, fontsize=32, fontweight="bold", color=TEXT, ha="left", va="top")
    fig.text(0.95, 0.945, year_label, fontsize=34, color=YEAR, ha="right", va="top", fontweight="bold")


def style_plot_axes(ax) -> None:
    ax.set_facecolor(BACKGROUND)
    for spine in ax.spines.values():
        spine.set_color(GRID)
        spine.set_linewidth(1.2)
    ax.tick_params(colors=TEXT, labelsize=14)
    ax.grid(color=GRID, linewidth=1.0, alpha=0.8)


def bar_limits(series: pd.Series) -> float:
    current_max = max(1.0, float(series.max()))
    return current_max * 1.16


def spread_positions(items: list[tuple[str, float, str]], lower: float, upper: float, gap: float) -> list[tuple[str, float, str]]:
    if not items:
        return []
    ordered = sorted(items, key=lambda item: item[1])
    placed: list[list[object]] = []
    cursor = lower
    for label, y_pos, color in ordered:
        current = max(cursor, y_pos)
        placed.append([label, min(current, upper), color])
        cursor = current + gap
    for index in range(len(placed) - 2, -1, -1):
        placed[index][1] = min(float(placed[index][1]), float(placed[index + 1][1]) - gap)
    return [(str(label), float(y_pos), str(color)) for label, y_pos, color in placed]


def draw_pie_frame(fig: plt.Figure, pivot: pd.DataFrame, palette: dict[str, str], main_title: str, progress: float) -> None:
    values, year_label = interpolated_values(pivot, progress)
    series = values.sort_values(ascending=False)
    total = max(float(series.sum()), 1.0)

    fig.clear()
    draw_header(fig, main_title, year_label)

    pie_ax = fig.add_axes([0.055, 0.10, 0.53, 0.76])
    legend_ax = fig.add_axes([0.62, 0.12, 0.33, 0.72])
    pie_ax.set_aspect("equal")
    pie_ax.set_xticks([])
    pie_ax.set_yticks([])
    pie_ax.set_facecolor(BACKGROUND)
    pie_ax.pie(
        series.values,
        startangle=90,
        colors=[palette[str(item)] for item in series.index],
        radius=1.0,
        wedgeprops={"width": 0.82, "linewidth": 2.0, "edgecolor": PIE_EDGE},
    )
    legend_ax.set_facecolor(BACKGROUND)
    legend_ax.axis("off")
    legend_ax.add_patch(Rectangle((0, 0), 1, 1, transform=legend_ax.transAxes, facecolor="#fbfcfe", edgecolor=FRAME, linewidth=1.5))
    legend_ax.text(0.05, 0.96, "类别 / 占比 / 数值", fontsize=17, color=TEXT, fontweight="bold", va="top")
    rows = len(series)
    columns = 1 if rows <= 16 else 2
    rows_per_column = int(np.ceil(rows / columns))
    y_step = 0.84 / max(rows_per_column, 1)
    for index, (category, value) in enumerate(series.items()):
        column = index // rows_per_column
        row = index % rows_per_column
        x_origin = 0.06 + column * 0.47
        y_pos = 0.88 - row * y_step
        legend_ax.add_patch(Rectangle((x_origin, y_pos - 0.024), 0.032, 0.032, transform=legend_ax.transAxes, facecolor=palette[str(category)], edgecolor="none"))
        percent = value / total
        line = f"{category}"
        legend_ax.text(x_origin + 0.05, y_pos + 0.008, line, fontsize=fit_fontsize(line, 14, 10), color=TEXT, va="center", transform=legend_ax.transAxes)
        legend_ax.text(x_origin + 0.05, y_pos - 0.019, f"{percent:.1%} | {value:,.0f}", fontsize=11.5, color=MUTED, va="center", transform=legend_ax.transAxes)


def draw_bar_frame(fig: plt.Figure, pivot: pd.DataFrame, palette: dict[str, str], main_title: str, progress: float, top_n: int) -> None:
    values, year_label = interpolated_values(pivot, progress)
    series = top_series(values, top_n)
    ymax = len(series)
    limit = bar_limits(series)

    fig.clear()
    draw_header(fig, main_title, year_label)

    ax = fig.add_axes([0.11, 0.14, 0.82, 0.72])
    style_plot_axes(ax)
    ax.grid(axis="x")
    ax.grid(axis="y", visible=False)
    y_positions = np.arange(ymax, dtype=float)
    bar_height = min(0.86, max(0.58, 5.8 / max(ymax, 1)))
    bars = ax.barh(
        y_positions,
        series.values,
        color=[palette[str(item)] for item in series.index],
        edgecolor="#ffffff",
        linewidth=1.3,
        height=bar_height,
    )
    ax.set_yticks(y_positions, list(series.index))
    ax.invert_yaxis()
    ax.set_xlim(0, limit)
    ax.margins(y=0.12)
    ax.set_xlabel("数值", fontsize=15, color=MUTED, labelpad=14)
    for rect, value in zip(bars, series.values):
        ax.text(
            rect.get_width() + limit * 0.012,
            rect.get_y() + rect.get_height() * 0.5,
            f"{value:,.0f}",
            va="center",
            ha="left",
            fontsize=15,
            color=TEXT,
            fontweight="bold",
        )


def draw_column_frame(fig: plt.Figure, pivot: pd.DataFrame, palette: dict[str, str], main_title: str, progress: float, top_n: int) -> None:
    values, year_label = interpolated_values(pivot, progress)
    series = top_series(values, top_n)
    x_positions = np.arange(len(series), dtype=float)
    y_limit = max(1.0, float(series.max()) * 1.22)

    fig.clear()
    draw_header(fig, main_title, year_label)

    ax = fig.add_axes([0.07, 0.28, 0.88, 0.54])
    label_ax = fig.add_axes([0.07, 0.10, 0.88, 0.13], sharex=ax)
    style_plot_axes(ax)
    ax.grid(axis="y")
    ax.grid(axis="x", visible=False)
    ax.spines["bottom"].set_visible(False)
    ax.tick_params(axis="x", bottom=False, labelbottom=False)
    bars = ax.bar(
        x_positions,
        series.values,
        color=[palette[str(item)] for item in series.index],
        edgecolor="#ffffff",
        linewidth=1.5,
        width=0.68,
    )
    ax.set_xlim(-0.6, len(series) - 0.4)
    ax.set_ylim(0, y_limit)
    ax.set_ylabel("数值", fontsize=15, color=MUTED, labelpad=12)
    for rect, value in zip(bars, series.values):
        ax.text(
            rect.get_x() + rect.get_width() * 0.5,
            rect.get_height() + y_limit * 0.018,
            f"{value:,.0f}",
            ha="center",
            va="bottom",
            fontsize=14,
            color=TEXT,
            fontweight="bold",
        )

    label_ax.set_facecolor(BACKGROUND)
    label_ax.set_ylim(0, 1)
    label_ax.set_yticks([])
    label_ax.set_xticks([])
    for spine in label_ax.spines.values():
        spine.set_visible(False)
    for index, category in enumerate(series.index):
        label_ax.text(
            x_positions[index],
            0.56,
            str(category),
            ha="center",
            va="center",
            fontsize=fit_fontsize(str(category), 13, 7),
            color=TEXT,
            rotation=0,
        )


def draw_stock_frame(fig: plt.Figure, pivot: pd.DataFrame, palette: dict[str, str], main_title: str, progress: float) -> None:
    years = [str(item) for item in pivot.index]
    max_index = len(years) - 1
    progress = max(0.0, min(float(progress), float(max_index)))
    whole = int(np.floor(progress))
    tween = progress - whole
    year_label = years[min(max_index, int(round(progress)))]

    fig.clear()
    draw_header(fig, main_title, year_label)

    ax = fig.add_axes([0.08, 0.14, 0.84, 0.70])
    style_plot_axes(ax)
    ax.grid(axis="both")
    x_ticks = np.arange(len(years), dtype=float)
    end_labels: list[tuple[str, float, str]] = []
    for category in pivot.columns:
        values = pivot[category].to_numpy(dtype=float)
        x_points = list(range(whole + 1))
        y_points = list(values[: whole + 1])
        if whole < max_index:
            x_points.append(progress)
            y_points.append(values[whole] + (values[whole + 1] - values[whole]) * tween)
        ax.plot(x_points, y_points, linewidth=3.0, color=palette[str(category)], solid_capstyle="round")
        ax.scatter([x_points[-1]], [y_points[-1]], s=38, color=palette[str(category)], zorder=4)
        end_labels.append((str(category), float(y_points[-1]), palette[str(category)]))

    y_min = float(pivot.min().min())
    y_max = float(pivot.max().max())
    y_pad = max(1.0, (y_max - y_min) * 0.14)
    ax.set_xlim(-0.15, max_index + 0.85)
    ax.set_ylim(y_min - y_pad, y_max + y_pad)
    ax.set_xticks(x_ticks, years)
    ax.set_ylabel("数值", fontsize=15, color=MUTED, labelpad=12)

    gap = max(1.0, (y_max - y_min) * 0.06)
    adjusted = spread_positions(end_labels, y_min - y_pad * 0.2, y_max + y_pad * 0.2, gap)
    label_x = min(progress + 0.14, max_index + 0.36)
    for label, y_pos, color in adjusted:
        ax.plot([progress, label_x - 0.03], [y_pos, y_pos], color=color, linewidth=1.2, alpha=0.5)
        ax.text(label_x, y_pos, label, color=color, fontsize=13, fontweight="bold", ha="left", va="center")


def render_video(frame: pd.DataFrame, output_path: Path, fps: int, title: str, top_n: int, width: int, height: int) -> Path:
    fps = max(12, int(fps))
    pivot = build_pivot(frame)
    years = [str(item) for item in pivot.index]
    palette = category_palette(pivot.columns)
    main_title = title or "数据可视化"

    year_steps = max(1, len(years) - 1)
    segments = [
        Segment("pie", "Category Share", round(year_steps * 1.00 * fps)),
        Segment("bar", "Bar Race", round(year_steps * 0.95 * fps)),
        Segment("column", "Column Bars", round(year_steps * 0.95 * fps)),
        Segment("stock", "Stock Trend", round(max(4.2, year_steps * 0.75) * fps)),
    ]
    total_frames = sum(max(1, segment.frames) for segment in segments)

    fig = make_figure(width, height)
    stream = open_ffmpeg_stream(output_path, fps, width, height)
    assert stream.stdin is not None
    try:
        frame_cursor = 0
        for segment in segments:
            segment_frames = max(1, segment.frames)
            for local_index in range(segment_frames):
                progress = 0.0 if len(years) == 1 else (local_index / max(1, segment_frames - 1)) * year_steps
                if segment.key == "pie":
                    draw_pie_frame(fig, pivot, palette, main_title, progress)
                elif segment.key == "bar":
                    draw_bar_frame(fig, pivot, palette, main_title, progress, top_n)
                elif segment.key == "column":
                    draw_column_frame(fig, pivot, palette, main_title, progress, top_n)
                else:
                    draw_stock_frame(fig, pivot, palette, main_title, progress)
                stream.stdin.write(figure_to_rgb_bytes(fig))
                frame_cursor += 1
    finally:
        plt.close(fig)
        if stream.stdin is not None:
            stream.stdin.close()
        return_code = stream.wait()
    if return_code != 0:
        raise RuntimeError(f"ffmpeg exited with code {return_code}")
    return remux_faststart(output_path)


def main() -> int:
    configure_fonts()
    args = parse_args()
    frame = load_long_table(args.input)
    output = render_video(
        frame=frame,
        output_path=args.output,
        fps=args.fps,
        title=args.title,
        top_n=min(MAX_CATEGORIES, max(1, args.top_n)),
        width=args.width,
        height=args.height,
    )
    print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
