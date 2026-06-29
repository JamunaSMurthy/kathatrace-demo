#!/usr/bin/env python3
"""Generate KathaTrace demo storyboards: Gemini planner -> FLUX (fal.ai) renderer -> per-story video.

Usage:
    export GEMINI_API_KEY=...
    export FAL_KEY=...
    python3 generate_demo_storyboards.py \
        --stories stories/demo_stories.jsonl \
        --out-dir output \
        --flux-model fal-ai/flux/dev \
        --gemini-model gemini-2.0-flash \
        --scene-seconds 3.0

Each story produces:
    output/<id>/plan.json          scene breakdown returned by the planner
    output/<id>/scene_NN.png       one rendered image per scene
    output/<id>/storyboard.mp4     scenes stitched into a video with simple crossfades
    output/manifest.json           summary of all stories (used by the demo page)

This intentionally mirrors the schema used by scripts/dataset/run_planner_on_jsonl.py and
scripts/generate_storyboards.py in the main KathaBench-25K pipeline, substituting hosted
Gemini + FLUX APIs for the local Gemma-3 LoRA planner + local SDXL renderer, since this
machine has no GPU and no local checkpoint.
"""
import argparse
import json
import os
import subprocess
import sys
import time
from pathlib import Path

import requests

GEMINI_BASE = "https://generativelanguage.googleapis.com/v1beta/models"
FAL_BASE = "https://fal.run"

PLANNER_SYSTEM_PROMPT = """You are annotating a moral story for an AI system that generates images with FLUX.
Break the story into 4 to 6 sequential scenes that capture the narrative arc, including the key
transition that carries the story's moral.

Return ONLY valid JSON (no markdown fences) matching this schema:
{
  "scenes": [
    {
      "scene_id": 1,
      "event": "<one sentence describing what happens in this scene>",
      "emotion": "<single dominant emotion word>",
      "outcome_visibility": "none|partial|full",
      "transition_dimension": "action|causal|intentional|emotional|consequence",
      "flux_prompt": "<vivid, explicit visual description for an image model: characters named explicitly, setting, pose, lighting, no pronoun-only references>",
      "caption": "<short human-readable caption for this scene>"
    }
  ]
}

The "transition_dimension" field describes the link FROM the previous scene TO this one
(scene 1 may use "action" as a default). Keep flux_prompt under 60 words, consistent in
character appearance across scenes, and avoid text/words appearing in the image."""


def call_gemini(api_key: str, model: str, story_text: str, title: str) -> dict:
    url = f"{GEMINI_BASE}/{model}:generateContent?key={api_key}"
    payload = {
        "contents": [
            {
                "role": "user",
                "parts": [
                    {"text": PLANNER_SYSTEM_PROMPT + f"\n\nStory title: {title}\nStory: {story_text}"}
                ],
            }
        ],
        "generationConfig": {"temperature": 0.4, "responseMimeType": "application/json"},
    }
    resp = requests.post(url, json=payload, timeout=60)
    resp.raise_for_status()
    data = resp.json()
    text = data["candidates"][0]["content"]["parts"][0]["text"]
    return json.loads(text)


def call_flux(api_key: str, model: str, prompt: str, out_path: Path) -> None:
    url = f"{FAL_BASE}/{model}"
    headers = {"Authorization": f"Key {api_key}", "Content-Type": "application/json"}
    payload = {
        "prompt": prompt,
        "image_size": "landscape_4_3",
        "num_inference_steps": 28,
        "num_images": 1,
    }
    resp = requests.post(url, headers=headers, json=payload, timeout=120)
    resp.raise_for_status()
    data = resp.json()
    image_url = data["images"][0]["url"]
    img_resp = requests.get(image_url, timeout=60)
    img_resp.raise_for_status()
    out_path.write_bytes(img_resp.content)


def stitch_video(scene_dir: Path, num_scenes: int, scene_seconds: float, out_path: Path) -> None:
    """Concatenate scene_NN.png into an mp4 with a fixed duration per scene via ffmpeg.

    ffmpeg's concat demuxer ignores the `duration` on the final entry, so the last
    frame must be listed twice (once with duration, once bare) to hold its length.
    """
    concat_list = scene_dir / "concat.txt"
    lines = []
    for i in range(1, num_scenes + 1):
        lines.append(f"file 'scene_{i:02d}.png'")
        lines.append(f"duration {scene_seconds}")
    lines.append(f"file 'scene_{num_scenes:02d}.png'")
    concat_list.write_text("\n".join(lines))

    cmd = (
        f"ffmpeg -y -f concat -safe 0 -i {concat_list.name} "
        f"-vf \"scale=1024:768:force_original_aspect_ratio=decrease,pad=1024:768:(ow-iw)/2:(oh-ih)/2,fps=24\" "
        f"-c:v libx264 -pix_fmt yuv420p {out_path.name}"
    )
    subprocess.run(cmd, shell=True, cwd=scene_dir, check=True)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--stories", default="stories/demo_stories.jsonl")
    ap.add_argument("--out-dir", default="output")
    ap.add_argument("--flux-model", default="fal-ai/flux/dev")
    ap.add_argument("--gemini-model", default="gemini-2.0-flash")
    ap.add_argument("--scene-seconds", type=float, default=3.0)
    ap.add_argument("--limit", type=int, default=None, help="Only process first N stories (for testing)")
    args = ap.parse_args()

    gemini_key = os.environ.get("GEMINI_API_KEY")
    fal_key = os.environ.get("FAL_KEY")
    if not gemini_key or not fal_key:
        sys.exit("Set GEMINI_API_KEY and FAL_KEY environment variables before running.")

    out_root = Path(args.out_dir)
    out_root.mkdir(parents=True, exist_ok=True)
    manifest = []

    stories = [json.loads(l) for l in Path(args.stories).read_text().splitlines() if l.strip()]
    if args.limit:
        stories = stories[: args.limit]

    for story in stories:
        sid = story["id"]
        print(f"[{sid}] planning scenes for '{story['title']}'...")
        story_dir = out_root / sid
        story_dir.mkdir(parents=True, exist_ok=True)

        plan = call_gemini(gemini_key, args.gemini_model, story["story"], story["title"])
        (story_dir / "plan.json").write_text(json.dumps(plan, indent=2))
        scenes = plan["scenes"]

        for scene in scenes:
            n = scene["scene_id"]
            img_path = story_dir / f"scene_{n:02d}.png"
            print(f"[{sid}] rendering scene {n}/{len(scenes)}...")
            call_flux(fal_key, args.flux_model, scene["flux_prompt"], img_path)
            time.sleep(0.5)

        video_path = story_dir / "storyboard.mp4"
        stitch_video(story_dir, len(scenes), args.scene_seconds, video_path)

        manifest.append(
            {
                "id": sid,
                "title": story["title"],
                "source": story["source"],
                "moral_label": story["moral_label"],
                "num_scenes": len(scenes),
                "scenes": scenes,
                "video": f"{sid}/storyboard.mp4",
                "images": [f"{sid}/scene_{s['scene_id']:02d}.png" for s in scenes],
            }
        )
        print(f"[{sid}] done -> {video_path}")

    (out_root / "manifest.json").write_text(json.dumps(manifest, indent=2))
    print(f"\nWrote manifest for {len(manifest)} stories to {out_root / 'manifest.json'}")


if __name__ == "__main__":
    main()
