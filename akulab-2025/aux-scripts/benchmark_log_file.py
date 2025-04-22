#!/usr/bin/env python3
"""
Benchmark I/O and membership‑test speed for a plain‑text list
of unique identifiers.

Examples
--------
# default N=17 000, M=10 000
python uid_benchmark.py

# custom sizes
python uid_benchmark.py --n 1_000_000 --m 200_000
"""

from __future__ import annotations
import argparse, random, time, tempfile
from pathlib import Path


def generate_ids(n: int) -> list[str]:
    """Create `n` uniq IDs: id_0 … id_{n‑1}."""
    return [f"id_{i}" for i in range(n)]


def build_query_list(n_ids: int, m: int, rnd: random.Random) -> list[str]:
    """
    Return *m* probe IDs: half are hits (randomly chosen
    from the file), half are guaranteed misses.
    """
    hits  = [f"id_{rnd.randrange(n_ids)}" for _ in range(m // 2)]
    misses = [f"id_{n_ids + i}" for i in range(m - m // 2)]
    return hits + misses


def timed(func, *args):
    """Run *func* and return (elapsed, result)."""
    t0 = time.perf_counter()
    result = func(*args)
    return time.perf_counter() - t0, result


def main():
    ap = argparse.ArgumentParser(formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    ap.add_argument("-n", "--n", type=int, default=17_000,
                    help="number of identifiers to write")
    ap.add_argument("-m", "--m", type=int, default=10_000,
                    help="number of membership checks")
    ap.add_argument("--seed", type=int, default=42, help="RNG seed")
    args = ap.parse_args()

    rnd = random.Random(args.seed)
    ids = generate_ids(args.n)

    workdir = Path(tempfile.mkdtemp(prefix="uid_test_"))
    fpath   = workdir / "uids.log"

    # 1️⃣ write ---------------------------------------------------------------
    write_t, _ = timed(lambda p, data: p.write_text("\n".join(data), encoding="utf-8"),
                       fpath, ids)

    # 2️⃣ read & build set ----------------------------------------------------
    def load_as_set(path: Path) -> set[str]:
        with path.open("r", encoding="utf-8") as f:
            return {line.rstrip("\n") for line in f}

    load_t, uid_set = timed(load_as_set, fpath)

    # 3️⃣ membership queries --------------------------------------------------
    probes = build_query_list(args.n, args.m, rnd)

    def count_hits(lookups: list[str], container: set[str]) -> int:
        return sum(1 for item in lookups if item in container)

    query_t, hits = timed(count_hits, probes, uid_set)

    # ------------------------------------------------------------------------
    print(f"\nFile location: {fpath}")
    print(f"{args.n:>10,} identifiers written ….. {write_t:8.4f} s")
    print(f"Loaded into set ….……………… {load_t:8.4f} s")
    print(f"{args.m:>10,} membership checks … {query_t:8.4f} s   (hits = {hits})")


if __name__ == "__main__":
    main()

