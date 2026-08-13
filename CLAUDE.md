# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

НЯН (Nyan) is a news aggregator. It scrapes posts from ~160 Russian-language Telegram channels, clusters near-duplicate posts about the same event, and posts one merged message per event to its own Telegram channels (@nyannews and friends). Every source belongs to a *group* (red = pro-Russian state, blue = independent/foreign, purple = neutral, plus topical groups) so readers can judge the slant of a story at a glance.

## Setup

Models are **not** in the repo and most of the code and tests won't run without them:

```
pip3 install -r requirements.txt
bash download_models.sh          # unpacks fasttext lang id + category classifier into models/
docker-compose up                # MongoDB on :27017 — the only datastore
```

Telegram bot tokens and channel ids go in `configs/client_config.json` (one entry per issue). `OPENAI_API_KEY` (or `OPENROUTER_API_KEY`) enables the LLM features (`nyan/topics.py`, `nyan/openai.py`); both are read from the environment or from a `.env` in the repo root. `nyan/openai.py` picks the provider from an explicit `provider_name`, then `LLM_PROVIDER`, then the model name — namespaced names (`anthropic/claude-sonnet-4.5`) go to OpenRouter, bare ones (`gpt-4o`) to OpenAI.

## Commands

```
bash crawl.sh                    # crawler loop: scrapy -> Mongo
bash send.sh                     # main daemon loop: Mongo -> annotate -> cluster -> rank -> post
bash archive.sh                  # export Mongo to data/nyan_archive.tar.gz
bash rss.sh                      # build RSS into static/ and push to gh-pages

pytest -s                        # tests; run from repo root — fixtures use relative paths
pytest -s tests/test_clusterer.py::test_clusterer_and_ranker_on_snapshot
flake8 nyan/ --count --ignore=C901,E741,W503,PIE786,E203 --show-source --statistics
mypy --strict nyan/              # CI gates on this; nyan/ is fully typed, crawler/ and scripts/ are not
```

CI (`.github/workflows/python.yml`, Python 3.8) runs flake8 + `mypy --strict` over `nyan/` only, then `pytest -s`.

## Architecture

Two independent processes joined only by MongoDB — the crawler never calls the daemon.

**Crawler** (`crawler/`, Scrapy). `crawler/spiders/telegram.py` scrapes the public web preview (`telegram.me/s/<channel>`) rather than the Bot API, so it can read channels it isn't a member of. `crawler/pipelines.py` upserts each post by URL into the `documents` collection. `crawler/fetch_times.json` tracks per-channel progress across restarts and is mutated at runtime.

**Daemon** (`nyan/daemon.py`, entrypoint `python3 -m nyan.send`). Loops forever; each iteration is one full pass:

1. **Read** — documents from the last `documents_offset` seconds (24h), previously posted clusters from the last `clusters_offset` (72h).
2. **Annotate** (`annotator.py`) — clean boilerplate, tokenize, embed with `multilingual-e5-base`, detect language (fasttext), classify category, embed images (CLIP). Results are cached in the `annotated_documents` collection and only recomputed when `Document.version` bumps or the text changed (`Document.is_reannotation_needed`). `postprocess` drops docs that `is_discarded()` — no issue, text under 12 chars, or category `not_news`.
3. **Cluster** (`clusterer.py`) — agglomerative clustering over cosine distance between embeddings, with the distance matrix hand-adjusted first: same-channel pairs penalized, far-apart-in-time pairs penalized on a sigmoid, pairs sharing a near-identical image discounted.
4. **Rank** (`ranker.py`) — per issue, keep clusters with ≥N distinct channels, at least one Russian doc, and under a max age; then filter by views-per-hour percentile and keep the top 10. For the `main` issue, red and blue views are normalized against each other so neither side's larger audience dominates the feed.
5. **Render** (`renderer.py`) — the chosen annotation text goes through `ads.py` (`AdRemover`, built from the `ad_remover` block of `renderer_config.json` and the same `LLM` the renderer already has), which asks the model to delete ad and self-promo fragments (`nyan/prompts/remove_ads.txt`). The answer is diffed against the original: anything that adds text (`max_new_ratio`) or strips too much of it (`min_kept_ratio` / `min_kept_ratio_hard` / `max_removed_length`) is thrown away and the original is rendered instead. The accepted text is cached on the cluster as `clean_annotation_text`.
6. **Send** (`daemon.send_cluster` + `client.py`) — a cluster similar to an already-posted one *edits* that message and appends the new sources to its discussion thread instead of posting again; a genuinely new cluster is posted, optionally as a reply to the most similar recent cluster (`related_threshold`), then each source doc is echoed into the discussion thread.

### Concepts worth knowing before editing

- **Issue** = one output Telegram channel (`main`, `tech`, `economy`, `moscow`, `entertainment`, `summary`). A channel declares its home issue plus a group per issue in `channels.json`; a cluster can land in several issues at once (`Cluster.issues`, always includes `main`).
- **Group** = the trust/slant color. `Cluster.group` is a majority vote over its docs' `main` groups and drives both the emoji in the rendered post and the view normalization in the ranker.
- Everything is config-driven JSON in `configs/`, one file per stage (`annotator_config.json` holds the large boilerplate-stripping substring lists, `clusterer_config.json` the distance penalties, `ranker_config.json` the per-issue thresholds, `daemon_config.json` the loop timings, `renderer_config.json` the ad-stripping thresholds). Behavior changes usually belong there, not in code.
- Dataclasses in `nyan/` inherit `Serializable` (`util.py`) for the JSON/Mongo round-trip. When adding a field to `Document`, bump `CURRENT_VERSION` so cached annotations get invalidated.

### Tests

`test_annotator.py` and `test_clusterer.py` are snapshot tests: they run the real pipeline over `tests/data/input_docs.jsonl` and diff against checked-in expected output. Any deliberate change to annotation, clustering, or ranking will fail them — regenerate with `python3 -m tests.canonize` and review the diff. They load the real models and the real `channels.json`, so they're slow and sensitive to config edits.

## Note

`configs/*.json` are working files that carry live credentials (bot tokens). Don't echo their contents into commits, output, or anything outbound.
