# -*- coding: utf-8 -*-
# ============================================================================
# kimi_asimov_run.py
# Purpose : Run Kimi (Moonshot) on ASIMOV v2-Injury (319) + v1-Injury (304),
#           N seeded runs per scenario for sampling-robustness (majority vote
#           downstream). Reuses validators from asimov_validate.py — Kimi is
#           ONLY an evaluated model here, never a mapping judge (circularity).
# Input   : data/asimov/{v2_injury, v1_injury}.csv
# Output  : output/asimov_validation/kimi_{v2,v1}_results_seed{i}.csv
# Env     : KIMI_API_KEY (or MOONSHOT_API_KEY)
# Usage   : python scripts/kimi_asimov_run.py [--seeds 3] [--limit N]
#           [--model kimi-k2-0905-preview] [--temperature 0.7]
# Note    : run a --limit 2 smoke test first to verify key/model/quota.
# ============================================================================

import sys, os, argparse
from pathlib import Path

# NOTE: no stdout re-wrap here — asimov_validate (imported below) already does
# it at module level; wrapping twice orphans the first wrapper and its GC
# closes the shared buffer ("I/O operation on closed file").
sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pandas as pd
from openai import OpenAI

from asimov_validate import validate_v2_injury, validate_v1_injury

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data" / "asimov"
OUTPUT_DIR = PROJECT_ROOT / "output" / "asimov_validation"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# sk-kimi- keys are Kimi Coding keys: they ONLY work on the coding endpoint
# (api.kimi.com/coding/v1, model kimi-for-coding), not on api.moonshot.cn/.ai.
BASE_URL = "https://api.kimi.com/coding/v1"
DEFAULT_MODEL = "kimi-for-coding"


def get_client():
    key = os.environ.get("KIMI_API_KEY") or os.environ.get("MOONSHOT_API_KEY")
    if not key:
        raise RuntimeError(
            "KIMI_API_KEY (or MOONSHOT_API_KEY) not set. "
            "Get one at platform.moonshot.cn and set the env var."
        )
    return OpenAI(api_key=key, base_url=BASE_URL)


def main():
    parser = argparse.ArgumentParser(description="Kimi on ASIMOV (seeded runs)")
    parser.add_argument("--dataset", choices=["v2_injury", "v1_injury", "all"],
                        default="all")
    parser.add_argument("--seeds", type=int, default=3,
                        help="number of seeded runs per scenario (default 3)")
    parser.add_argument("--limit", type=int, default=None,
                        help="limit examples (smoke test)")
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--temperature", type=float, default=1.0,
                        help="sampling temperature (default 1.0 — "
                             "kimi-for-coding REJECTS any other value; "
                             "DeepSeek reference runs were 0.1, noted in report)")
    parser.add_argument("--workers", type=int, default=9,
                        help="parallel chunk workers (default 9; 429 backoff "
                             "is built into the validators)")
    args = parser.parse_args()

    client = get_client()
    print(f"Kimi client ready (model={args.model}, seeds={args.seeds}, "
          f"T={args.temperature})")

    # chunk-level parallelism (user-approved speedup 2026-07-22):
    # all (seed, chunk) jobs share one pool; per-seed file lock; resume by idx
    from concurrent.futures import ThreadPoolExecutor
    import threading

    def run_v1(seed_i):
        out = OUTPUT_DIR / f"kimi_v1_results_seed{seed_i}.csv"
        if out.exists() and len(pd.read_csv(out)) >= (args.limit or 304):
            print(f"  [skip] v1 seed {seed_i}: complete")
            return
        df = pd.read_csv(DATA_DIR / "v1_injury.csv")
        res = validate_v1_injury(client, df, limit=args.limit,
                                 model=args.model,
                                 temperature=args.temperature, seed=seed_i,
                                 max_tokens=2048)
        res.to_csv(out, index=False, encoding="utf-8")
        print(f"  [done] v1 seed {seed_i}: {res['error'].isna().sum()}/{len(res)} valid")

    def v2_chunk_jobs():
        df = pd.read_csv(DATA_DIR / "v2_injury.csv")
        if args.limit:
            df = df.head(args.limit)
        jobs = []
        for seed_i in range(1, args.seeds + 1):
            out = OUTPUT_DIR / f"kimi_v2_results_seed{seed_i}.csv"
            done_idx = set()
            if out.exists():
                done_idx = set(pd.read_csv(out)["idx"].tolist())
            for start in range(0, len(df), CHUNK):
                chunk = df.iloc[start:start + CHUNK]
                if set(chunk.index) <= done_idx:
                    continue
                jobs.append((seed_i, chunk))
        return jobs

    CHUNK = 40
    locks = {s: threading.Lock() for s in range(1, args.seeds + 1)}

    def run_v2_chunk(seed_i, chunk):
        out = OUTPUT_DIR / f"kimi_v2_results_seed{seed_i}.csv"
        res = validate_v2_injury(client, chunk, model=args.model,
                                 temperature=args.temperature, seed=seed_i,
                                 max_tokens=4096)
        with locks[seed_i]:
            parts = [res]
            if out.exists():
                parts.insert(0, pd.read_csv(out))
            merged = pd.concat(parts).drop_duplicates(subset="idx", keep="last")
            merged.to_csv(out, index=False, encoding="utf-8")
        print(f"  [ckpt] v2 seed {seed_i}: {len(merged)}/319 "
              f"({res['error'].isna().sum()}/{len(res)} valid this chunk)")

    jobs = []
    if args.dataset in ("v2_injury", "all"):
        jobs += [("v2", s, c) for s, c in v2_chunk_jobs()]
    if args.dataset in ("v1_injury", "all"):
        jobs += [("v1", s, None) for s in range(1, args.seeds + 1)]

    print(f"  Jobs: {sum(1 for j in jobs if j[0] == 'v2')} v2 chunks, "
          f"{sum(1 for j in jobs if j[0] == 'v1')} v1 runs "
          f"(workers={min(args.workers, len(jobs) or 1)})")

    def run(job):
        kind, seed_i, chunk = job
        if kind == "v2":
            run_v2_chunk(seed_i, chunk)
        else:
            run_v1(seed_i)

    with ThreadPoolExecutor(max_workers=args.workers) as ex:
        list(ex.map(run, jobs))

    print("\nAll runs done. Next: majority-vote aggregation in "
          "asimov_cascade_evidence.py")


if __name__ == "__main__":
    main()
