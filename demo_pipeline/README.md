# KathaTrace demo storyboard generation

Generates storyboards for 10 demo stories using hosted APIs (no local GPU needed):

- **Planner**: Gemini API (`gemini-2.0-flash` by default) plays the role of the trained
  Gemma-3-4B-IT LoRA planner from the main KathaBench-25K pipeline — it breaks each story
  into 4-6 scenes with events, emotions, transition dimensions, and FLUX prompts.
- **Renderer**: fal.ai's hosted FLUX (`fal-ai/flux/dev` by default) renders one image per scene.
- **Video**: ffmpeg stitches each story's scene images into an `.mp4` (fixed duration per scene).

## Setup

```bash
pip install requests
export GEMINI_API_KEY=...   # https://aistudio.google.com/apikey
export FAL_KEY=...          # https://fal.ai/dashboard/keys
```

## Run

```bash
cd demo_pipeline
python3 generate_demo_storyboards.py --stories stories/demo_stories.jsonl --out-dir output
```

Add `--limit 1` to test on a single story first before spending API credits on all 10.

## Output

```
output/
  manifest.json              # all 10 stories: scenes, image paths, video path
  demo-01/
    plan.json                # raw planner output for this story
    scene_01.png .. scene_0N.png
    storyboard.mp4
  demo-02/
    ...
```

Copy `output/` into `../assets/storyboards/` (or point the demo page's fetch path at it)
to wire the generated videos into `index.html`.
