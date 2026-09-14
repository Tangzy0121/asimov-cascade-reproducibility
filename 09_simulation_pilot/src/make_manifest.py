"""Final manifest (plan Task 9): SHA-256 of every material artifact — frozen
config, all source, all tests, raw outputs, tables, figures, logs, reports.
"""
import hashlib
import json
import os
import sys

WORK = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))


def sha(p):
    with open(p, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


def main():
    entries = {}
    for root, _dirs, files in os.walk(WORK):
        for fn in sorted(files):
            p = os.path.join(root, fn)
            rel = os.path.relpath(p, WORK).replace("\\", "/")
            if rel.startswith(("logs/fig_preview/",)) or rel in (
                    "final_manifest.json",):
                continue
            if "__pycache__" in rel or ".pytest_cache" in rel:
                continue
            entries[rel] = {"sha256": sha(p), "bytes": os.path.getsize(p)}
    manifest = {
        "experiment": "Topic 22 controlled propagation simulation",
        "frozen_config_sha256": entries["config/preregistered.yaml"]["sha256"],
        "n_files": len(entries),
        "files": entries,
    }
    out = os.path.join(WORK, "final_manifest.json")
    with open(out, "w") as f:
        json.dump(manifest, f, indent=2)
    print(f"manifest: {len(entries)} files hashed -> {out}")


if __name__ == "__main__":
    main()
