#!/usr/bin/env python3
from __future__ import annotations

import argparse
import math
import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Tuple

from common.io import FRAMES_DIR, TMP_DIR, ensure_runtime_dirs


def _configure_panda3d(width: int, height: int, prefer_gpu: bool) -> None:
    from panda3d.core import loadPrcFileData

    cache_dir = TMP_DIR / "panda_cache"
    cache_dir.mkdir(parents=True, exist_ok=True)
    if prefer_gpu:
        loadPrcFileData("", "load-display pandagl")
        loadPrcFileData("", "aux-display p3tinydisplay")
    else:
        loadPrcFileData("", "load-display p3tinydisplay")
    loadPrcFileData("", "window-type offscreen")
    loadPrcFileData("", f"win-size {width} {height}")
    loadPrcFileData("", "audio-library-name null")
    loadPrcFileData("", "sync-video false")
    loadPrcFileData("", f"model-cache-dir {cache_dir}")


def _delegate_to_desktop_user_if_needed(prefer_gpu: bool) -> None:
    if not prefer_gpu:
        return
    if os.environ.get("PANDA_GPU_DELEGATED") == "1":
        return
    if os.geteuid() != 0:
        return
    if not Path("/mnt/wslg/runtime-dir").exists():
        return

    target_user = os.environ.get("PANDA_GPU_USER", "bob")
    command = [
        "runuser",
        "-u",
        target_user,
        "--",
        "env",
        "PANDA_GPU_DELEGATED=1",
        f"DISPLAY={os.environ.get('DISPLAY', ':0')}",
        f"XDG_RUNTIME_DIR={os.environ.get('XDG_RUNTIME_DIR', '/mnt/wslg/runtime-dir')}",
        f"WAYLAND_DISPLAY={os.environ.get('WAYLAND_DISPLAY', 'wayland-0')}",
        f"PULSE_SERVER={os.environ.get('PULSE_SERVER', 'unix:/mnt/wslg/PulseServer')}",
        "python3",
        *sys.argv,
    ]
    raise SystemExit(subprocess.call(command))


def _clear_output() -> None:
    if FRAMES_DIR.exists():
        for item in FRAMES_DIR.glob("builtin_panda_*.png"):
            item.unlink()
    video_only = TMP_DIR / "builtin_panda_video.mp4"
    if video_only.exists():
        video_only.unlink()


def _open_ffmpeg_stream(fps: int, width: int, height: int, output_path: Path):
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
        "-r",
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
        "23",
        str(output_path),
    ]
    return subprocess.Popen(command, stdin=subprocess.PIPE)


def _place_on_ground(node, ground_z: float) -> None:
    bounds = node.getTightBounds()
    if not bounds:
        return
    min_point, _ = bounds
    node.setZ(node.getZ() + (ground_z - min_point.z))


def _capture_frame_bytes(base) -> bytes:
    from panda3d.core import GraphicsOutput, Texture

    capture_texture = getattr(base, "_codex_capture_texture", None)
    if capture_texture is None:
        capture_texture = Texture()
        capture_texture.setKeepRamImage(True)
        base.win.addRenderTexture(capture_texture, GraphicsOutput.RTM_copy_ram)
        base._codex_capture_texture = capture_texture

    for _ in range(2):
        base.graphicsEngine.renderFrame()
        if capture_texture.hasRamImage():
            payload = capture_texture.getRamImageAs("RGB")
            if payload:
                frame_bytes = bytes(payload)
                row_stride = base.win.getXSize() * 3
                return b"".join(
                    frame_bytes[row_start : row_start + row_stride]
                    for row_start in range(len(frame_bytes) - row_stride, -1, -row_stride)
                )
    raise RuntimeError("failed to capture frame bytes")


def render_builtin_panda_video(output_path: Path, duration_s: float, fps: int, width: int, height: int, prefer_gpu: bool) -> Tuple[Path, str]:
    ensure_runtime_dirs()
    _clear_output()
    _configure_panda3d(width, height, prefer_gpu=prefer_gpu)

    from direct.actor.Actor import Actor
    from direct.showbase.ShowBase import ShowBase
    from panda3d.core import AmbientLight, DirectionalLight, OrthographicLens

    base = ShowBase(windowType="offscreen")
    pipe_name = base.pipe.getType().getName()
    ffmpeg_proc = _open_ffmpeg_stream(fps, width, height, output_path)
    try:
        base.disableMouse()
        lens = OrthographicLens()
        lens.setFilmSize(18, 18 * height / width)
        base.cam.node().setLens(lens)

        environment = base.loader.loadModel("models/environment")
        environment.reparentTo(base.render)
        environment.setScale(0.12)
        environment.setPos(-8.0, 22.0, -3.6)
        environment.setH(12.0)
        ground_z = -3.45

        panda = Actor("models/panda-model", {"walk": "models/panda-walk4"})
        panda.reparentTo(base.render)
        panda.setScale(0.0046)
        panda.setPos(0.0, 10.0, ground_z)
        panda.setH(0.0)
        _place_on_ground(panda, ground_z)

        side_pandas = []
        for index, config in enumerate(
            (
                {"x": -5.2, "y": 15.0, "z": ground_z, "scale": 0.0036, "h": 18.0},
                {"x": 4.8, "y": 14.5, "z": ground_z, "scale": 0.0038, "h": -22.0},
                {"x": 0.4, "y": 18.2, "z": ground_z, "scale": 0.0033, "h": 0.0},
            )
        ):
            model = base.loader.loadModel("models/panda-model")
            model.reparentTo(base.render)
            model.setScale(config["scale"])
            model.setPos(config["x"], config["y"], config["z"])
            model.setH(config["h"])
            _place_on_ground(model, ground_z)
            side_pandas.append((index, model, config))

        prop_specs = [
            ("models/teapot", (-6.8, 11.5, -2.4), 0.65, (18.0, 0.0, 0.0)),
            ("models/teapot", (6.6, 12.0, -2.38), 0.52, (-12.0, 0.0, 0.0)),
            ("models/smiley", (-2.4, 16.0, 0.1), 0.78, (0.0, 0.0, 0.0)),
            ("models/frowney", (3.2, 16.6, 0.2), 0.72, (0.0, 0.0, 0.0)),
            ("models/box", (0.0, 12.6, -2.75), 0.85, (0.0, 0.0, 0.0)),
        ]
        props = []
        for model_name, pos, scale, hpr in prop_specs:
            model = base.loader.loadModel(model_name)
            model.reparentTo(base.render)
            model.setScale(scale)
            model.setPos(*pos)
            model.setHpr(*hpr)
            props.append(model)

        ambient = base.render.attachNewNode(AmbientLight("ambient"))
        ambient.node().setColor((0.72, 0.72, 0.78, 1.0))
        base.render.setLight(ambient)
        sun = base.render.attachNewNode(DirectionalLight("sun"))
        sun.node().setColor((0.96, 0.94, 0.86, 1.0))
        sun.setHpr(-30, -38, 0)
        base.render.setLight(sun)

        total_frames = max(1, round(duration_s * fps))
        walk_frames = max(1, panda.getNumFrames("walk"))
        for frame_index in range(total_frames):
            t = frame_index / fps
            loop_ratio = frame_index / max(1, total_frames - 1)
            anim_frame = int((t * fps * 1.7) % walk_frames)
            panda.pose("walk", anim_frame)

            panda_x = -2.8 + loop_ratio * 5.6
            panda.setPos(panda_x, 10.0, ground_z)
            panda.setH(math.sin(t * 1.4) * 8.0)
            _place_on_ground(panda, ground_z)

            for index, side_panda, config in side_pandas:
                sway = math.sin(t * (0.8 + index * 0.23) + index) * 0.08
                nod = math.sin(t * (1.1 + index * 0.17) + index * 0.6) * 6.0
                side_panda.setPos(config["x"] + sway, config["y"], ground_z)
                side_panda.setH(config["h"] + nod)
                _place_on_ground(side_panda, ground_z)

            props[0].setHpr(18.0 + t * 18.0, math.sin(t * 1.2) * 6.0, 0.0)
            props[1].setHpr(-12.0 - t * 15.0, math.cos(t * 1.1) * 5.0, 0.0)
            props[2].setPos(-2.4, 16.0 + math.sin(t * 1.4) * 0.3, 0.18 + math.sin(t * 2.1) * 0.14)
            props[3].setPos(3.2, 16.6 + math.cos(t * 1.3) * 0.35, 0.26 + math.cos(t * 1.8) * 0.12)
            props[4].setHpr(0.0, 0.0, math.sin(t * 0.9) * 4.0)

            cam_x = panda_x + math.sin(t * 0.8) * 1.2
            cam_y = -28.0
            cam_z = 1.4 + math.cos(t * 0.7) * 0.2
            base.camera.setPos(cam_x, cam_y, cam_z)
            base.camera.lookAt(panda_x, 10.0, -0.8)

            frame_bytes = _capture_frame_bytes(base)
            assert ffmpeg_proc.stdin is not None
            ffmpeg_proc.stdin.write(frame_bytes)
    finally:
        if ffmpeg_proc.stdin is not None:
            ffmpeg_proc.stdin.close()
        return_code = ffmpeg_proc.wait()
        base.destroy()
    if return_code != 0:
        raise RuntimeError(f"ffmpeg exited with code {return_code}")

    return output_path, pipe_name


def main() -> int:
    parser = argparse.ArgumentParser(description="Render a short MP4 using Panda3D built-in character assets.")
    parser.add_argument("--output", type=Path, default=Path("outputs/builtin_panda_demo.mp4"))
    parser.add_argument("--duration", type=float, default=6.0)
    parser.add_argument("--fps", type=int, default=24)
    parser.add_argument("--width", type=int, default=960)
    parser.add_argument("--height", type=int, default=540)
    parser.add_argument("--cpu", action="store_true", help="Force TinyDisplay software rendering instead of requesting GPU first.")
    args = parser.parse_args()

    _delegate_to_desktop_user_if_needed(prefer_gpu=not args.cpu)

    output, pipe_name = render_builtin_panda_video(
        output_path=args.output,
        duration_s=args.duration,
        fps=args.fps,
        width=args.width,
        height=args.height,
        prefer_gpu=not args.cpu,
    )
    print(f"pipe={pipe_name}")
    print(output)
    return 0


if __name__ == "__main__":
    sys.exit(main())
