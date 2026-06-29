# KathaTrace Demo

This repository contains a lightweight demo app for KathaTrace, an interactive storyboarding experience that shows how semantic trajectory quality changes across different evidence conditions.

## What is included

- A polished single-page demo experience in [index.html](index.html)
- A small storyboard generation pipeline in [demo_pipeline](demo_pipeline)
- Demo story metadata and assets under [assets](assets)

## Demo app overview

The app lets you:

- choose a story from the bundled demo set
- generate a storyboard trace from the story text
- inspect scene-by-scene transitions and evidence recovery bars
- compare how the system behaves under different evidence modes

## Project structure

- [index.html](index.html) — the interactive demo frontend
- [demo_pipeline](demo_pipeline) — Python pipeline for generating storyboard assets
- [assets](assets) — story metadata and local demo assets
- [demo_pipeline/stories/demo_stories.jsonl](demo_pipeline/stories/demo_stories.jsonl) — sample stories used by the demo

## Running the demo locally

Open [index.html](index.html) in a browser to view the demo.

If you want to regenerate the storyboard assets, install the Python dependencies and run the pipeline:

```bash
pip install requests
export GEMINI_API_KEY=...
export FAL_KEY=...
cd demo_pipeline
python3 generate_demo_storyboards.py --stories stories/demo_stories.jsonl --out-dir output
```

## Repository status

This repository is ready to be shared and pushed to GitHub as a demo app snapshot.
