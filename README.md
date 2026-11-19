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

The source handoff retains its original reference within each reconstructed scenario. The prototype currently handles these fixed small acyclic histories. General record input, persistent sharing, caregiver confirmation workflows, and real-world caregiver outcomes are future work.

## Inspect a persisted snapshot

The browser demo still creates an in-memory graph for each request. The separate `snapshots/converged.rl` artifact is a single-file Relate store containing the fictional scenario after the two correction paths converge on `r4`. It can be inspected after the process that created it has exited.

```sh
.venv/bin/python export_store.py inspect snapshots/converged.rl
```

The command opens the existing store in read-only mode. It prints the shared reference, both correction paths, the current record, and the stored versions. The expected paths are `r1 → r2 → r4` and `r1 → r3 → r4`. The shared reference remains `pet-a` / `r1`, while `r4` is still marked `unconfirmed` and needs caregiver confirmation.

To generate another copy from the same fixture statements, choose a new `.rl` path in an existing directory:

```sh
.venv/bin/python export_store.py create snapshots/recreated.rl
.venv/bin/python export_store.py inspect snapshots/recreated.rl
```

Creation closes and flushes Relate before publishing the file. Existing paths are refused. `inspect` requires an existing `.rl` file and does not seed a new graph.

The included snapshot is 36,864 bytes with SHA-256 `fdec9b689bf2c41a82e414c6a89ef9ba13587e9ce885b2a27402c14c08b12c36`. Regenerated stores can have different byte hashes while returning the same paths, versions and statuses.

## Technology and authorship

Relate 1.0.2 is embedded in Python. The local server uses Python's standard library. The UI uses HTML, CSS and JavaScript.

Development began on 17 November 2026 as a new standalone prototype inspired by earlier pet-care handoff work. Its source and fictional records were newly authored during the contest period. Codex assisted with planning, code, fixtures, internal review, and documentation. Playwright and Chrome were used for private browser checks and recording, and FFmpeg encoded the review video.

[Relate Python guide](https://relatedb.ai/docs/guides/embed/python/) · [Relate package](https://pypi.org/project/relate-db/1.0.2/)

[Watch the 89-second fictional-data demo](https://youtu.be/CFTlCs-SS-0)
