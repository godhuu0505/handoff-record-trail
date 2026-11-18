# Handoff Record Trail

A shared message says breakfast was completed for Mochi. A correction later points to another pet with the same name. Handoff Record Trail shows what the message originally referenced and where later corrections lead, so the next caregiver can see when confirmation is still needed.

This standalone prototype replays six fixed fictional scenarios in a local browser. Each request creates an in-memory Relate graph and runs the same parameterized Cypher query. The screen displays the original reference, current records, and every returned correction path. Python deduplicates terminal versions and applies the display rules.

## Run locally

Tested with Python 3.13.1 on macOS arm64.

1. Create a virtual environment.
2. Install the pinned dependency.
3. Start the local server and open the address it prints.

```sh
python3 -m venv .venv
.venv/bin/python -m pip install --only-binary=:all: -r requirements.txt
.venv/bin/python server.py
```

The server binds to 127.0.0.1. All displayed records are generated fictional examples.

## Follow the history

Use Previous and Next to inspect the shared message before correction, a correction to another pet, conflicting corrections, convergence on an unconfirmed record, a missing pet reference, and an unavailable shared reference. A single current version can still need confirmation when it belongs to another pet or its completion status is unconfirmed.

## Verify

```sh
.venv/bin/python -I trace.py
.venv/bin/python -m unittest -v test_server.py
```

The CLI asserts six fixture expectations and prints their actual traces. The five HTTP tests check all six stages against results.json, revisit stages in reverse order, reject invalid stage inputs, and exercise unavailable routes and engine failure.

The source handoff retains its original reference within each reconstructed scenario. The prototype currently handles these fixed small acyclic histories. General record input, persistent storage, caregiver confirmation workflows, and real-world caregiver outcomes are future work.

## Technology and authorship

Relate 1.0.2 is embedded in Python. The local server uses Python's standard library. The UI uses HTML, CSS and JavaScript.

Development began on 17 November 2026 as a new standalone prototype inspired by earlier pet-care handoff work. Its source and fictional records were newly authored during the contest period. Codex assisted with planning, code, fixtures, internal review, and documentation. Playwright and Chrome were used for private browser checks and recording, and FFmpeg encoded the review video.

[Relate Python guide](https://relatedb.ai/docs/guides/embed/python/) · [Relate package](https://pypi.org/project/relate-db/1.0.2/)

[Watch the 89-second fictional-data demo](https://youtu.be/CFTlCs-SS-0)
