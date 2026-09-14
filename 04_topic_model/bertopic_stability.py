# -*- coding: utf-8 -*-
# ============================================================================
# bertopic_stability.py  |  P0-3 stability analysis
# Purpose : Test whether the frozen baseline numbers (77 topics / 20 safety
#           candidates / 30.2% noise) are stable under UMAP seed, HDBSCAN/UMAP
#           parameter, and embedding-model perturbations.
# Baseline: output/time_analysis/04_bertopic_time/ (mcs=25, nn=15, UMAP
#           seed=42, PatentSBERTa_V2, dataset v5) — READ ONLY, never modified.
# Output  : output/time_analysis/13_stability/
# Usage   : python scripts/bertopic_stability.py
# Asimov Cascade humanoid-safety patent pipeline
# ============================================================================

"""Stability analysis for the BERTopic cascade stage.

Design:
  - Embeddings are computed ONCE per model and cached as .npy in
    13_stability/cache/; all configs reuse them.
  - Each config reruns UMAP + HDBSCAN + c-TF-IDF via BERTopic with the exact
    same sub-model settings as the baseline training script
    (min_dist=0, cosine, n_components=5; HDBSCAN min_samples=3, eom).
  - Topic matching vs baseline uses document-set Jaccard over patent_number
    sets (baseline topics from the frozen document_topic_assignment.csv).

All random seeds are fixed explicitly and printed.
"""

import sys, io, os, json, time
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# --- Dataset: baseline run used v5 (verified: 8,928 docs, patent_number order
# --- identical to document_topic_assignment.csv). Pin it before engine import.
os.environ.setdefault(
    'PATSENSE_DATASET',
    r'<project>/PatSense\Cascade\data\humanoid_safety_patents_v5_clean.xlsx')
sys.path.insert(0, '.')

import numpy as np
import pandas as pd
from pathlib import Path

np.random.seed(42)

BASE = Path(r'<project>/PatSense\Cascade\BERT_Python')
OUT = BASE / 'output' / 'time_analysis' / '13_stability'
CACHE = OUT / 'cache'
RUNS = OUT / 'runs'
for p in (OUT, CACHE, RUNS):
    p.mkdir(parents=True, exist_ok=True)

FROZEN = BASE / 'output' / 'time_analysis' / '04_bertopic_time'
LABELS = BASE / 'output' / 'time_analysis' / '10_cascade' / 'llm_safety_labels.csv'

JACCARD_MATCH_THRESHOLD = 0.5

# --- Config grid (baseline itself is seed=42/mcs=25/nn=15/PatentSBERTa) ---
CONFIGS = [
    # seed grid: UMAP random_state varies, mcs=25, nn=15, PatentSBERTa_V2
    {'name': 'seed0',   'embedding': 'patentsberta', 'umap_seed': 0,   'mcs': 25, 'nn': 15},
    {'name': 'seed1',   'embedding': 'patentsberta', 'umap_seed': 1,   'mcs': 25, 'nn': 15},
    {'name': 'seed7',   'embedding': 'patentsberta', 'umap_seed': 7,   'mcs': 25, 'nn': 15},
    {'name': 'seed123', 'embedding': 'patentsberta', 'umap_seed': 123, 'mcs': 25, 'nn': 15},
    # parameter grid: seed=42, PatentSBERTa_V2
    {'name': 'mcs15_nn15', 'embedding': 'patentsberta', 'umap_seed': 42, 'mcs': 15, 'nn': 15},
    {'name': 'mcs40_nn15', 'embedding': 'patentsberta', 'umap_seed': 42, 'mcs': 40, 'nn': 15},
    {'name': 'mcs25_nn10', 'embedding': 'patentsberta', 'umap_seed': 42, 'mcs': 25, 'nn': 10},
    {'name': 'mcs25_nn30', 'embedding': 'patentsberta', 'umap_seed': 42, 'mcs': 25, 'nn': 30},
    # alternative embedding: all-MiniLM-L6-v2, seed=42/mcs=25/nn=15
    {'name': 'minilm',  'embedding': 'minilm',       'umap_seed': 42, 'mcs': 25, 'nn': 15},
]

EMBEDDING_MODELS = {
    'patentsberta': 'AAUBS/PatentSBERTa_V2',
    'minilm': 'sentence-transformers/all-MiniLM-L6-v2',
}


def get_embeddings(key, documents):
    """Compute once, cache as .npy, reuse afterwards."""
    path = CACHE / f'embeddings_{key}.npy'
    if path.exists():
        print(f'  [cache] loading {path.name}')
        return np.load(path)
    from sentence_transformers import SentenceTransformer
    name = EMBEDDING_MODELS[key]
    print(f'  Computing embeddings with {name} (one-off, cached to {path.name})...')
    model = SentenceTransformer(name)
    t0 = time.time()
    emb = model.encode(documents, show_progress_bar=True, batch_size=64,
                       convert_to_numpy=True)
    print(f'  encoded {emb.shape} in {time.time()-t0:.0f}s')
    np.save(path, emb)
    return emb


def run_config(cfg, documents, embeddings):
    """One UMAP+HDBSCAN+BERTopic clustering run, mirroring the baseline flow."""
    from bertopic import BERTopic
    from umap import UMAP
    from hdbscan import HDBSCAN
    from sklearn.feature_extraction.text import CountVectorizer

    emb_dim = embeddings.shape[1]
    umap_model = UMAP(
        n_neighbors=cfg['nn'], n_components=min(5, emb_dim - 1), min_dist=0,
        metric='cosine', random_state=cfg['umap_seed'])
    hdbscan_model = HDBSCAN(
        min_cluster_size=cfg['mcs'], min_samples=3, metric='euclidean',
        cluster_selection_method='eom', prediction_data=True)
    vectorizer_model = CountVectorizer(ngram_range=(1, 2), stop_words='english')

    topic_model = BERTopic(
        umap_model=umap_model, hdbscan_model=hdbscan_model,
        vectorizer_model=vectorizer_model, verbose=False, top_n_words=50)
    topics, _ = topic_model.fit_transform(documents, embeddings)
    return topic_model, np.asarray(topics)


def jaccard(a, b):
    if not a and not b:
        return 0.0
    u = len(a | b)
    return len(a & b) / u if u else 0.0


def main():
    t_start = time.time()
    print('=' * 70)
    print('P0-3 BERTopic stability analysis')
    print(f'Configs: {len(CONFIGS)} | seeds/mcs/nn all explicit (see below)')
    print('=' * 70)

    # --- Data (same pipeline + dataset as the baseline run) ---
    from engine.data import load_and_prepare
    df, documents, _ = load_and_prepare()
    patent_numbers = df['patent_number'].tolist()
    print(f'Documents: {len(documents)} (dataset: {os.environ["PATSENSE_DATASET"]})')

    # --- Frozen baseline assignments (READ ONLY) ---
    base_assign = pd.read_csv(FROZEN / 'document_topic_assignment.csv')
    assert list(base_assign['patent_number']) == patent_numbers, \
        'Baseline assignment order mismatch — dataset does not match'
    base_topic = base_assign['topic'].to_numpy()
    base_topics = sorted(t for t in set(base_topic) if t != -1)
    base_sets = {t: set(base_assign.loc[base_topic == t, 'patent_number'])
                 for t in base_topics}
    n_base_noise = int((base_topic == -1).sum())
    print(f'Baseline: {len(base_topics)} topics, noise {n_base_noise}'
          f' ({100*n_base_noise/len(base_topic):.1f}%)')

    # --- Safety candidates (safety_score >= 2) ---
    labels = pd.read_csv(LABELS)
    candidates = sorted(labels.loc[labels['safety_score'] >= 2, 'bertopic_id'].tolist())
    print(f'Safety candidates: {len(candidates)} topics: {candidates}')

    # --- Embeddings (one-off per model, cached) ---
    embeddings = {k: get_embeddings(k, documents) for k in EMBEDDING_MODELS}

    # --- Run grid ---
    run_rows = []
    cand_rows = []          # long format: one row per (candidate, config)
    for cfg in CONFIGS:
        t0 = time.time()
        print(f"\n--- {cfg['name']}: embedding={cfg['embedding']}, "
              f"umap_seed={cfg['umap_seed']}, mcs={cfg['mcs']}, nn={cfg['nn']} ---")
        topic_model, topics = run_config(cfg, documents, embeddings[cfg['embedding']])

        run_topic_ids = sorted(t for t in set(topics) if t != -1)
        n_noise = int((topics == -1).sum())
        noise_rate = n_noise / len(topics)
        run_sets = {t: set(np.asarray(patent_numbers)[topics == t])
                    for t in run_topic_ids}

        # Per-baseline-topic best Jaccard match
        best_j = {}
        best_run = {}
        for bt in base_topics:
            bj, br = 0.0, None
            for rt, rs in run_sets.items():
                j = jaccard(base_sets[bt], rs)
                if j > bj:
                    bj, br = j, rt
            best_j[bt], best_run[bt] = bj, br
        bj_vals = np.array([best_j[t] for t in base_topics])
        matched = int((bj_vals >= JACCARD_MATCH_THRESHOLD).sum())

        # Candidate retention
        retained = 0
        for c in candidates:
            j, rt = best_j[c], best_run[c]
            ok = j >= JACCARD_MATCH_THRESHOLD
            retained += ok
            cand_rows.append({
                'baseline_topic': c,
                'baseline_name': labels.loc[labels.bertopic_id == c, 'bertopic_name'].iloc[0],
                'config': cfg['name'],
                'best_jaccard': round(j, 4),
                'matched_run_topic': rt,
                'retained': int(ok),
            })

        run_rows.append({
            'config': cfg['name'],
            'embedding': EMBEDDING_MODELS[cfg['embedding']],
            'umap_seed': cfg['umap_seed'],
            'min_cluster_size': cfg['mcs'],
            'n_neighbors': cfg['nn'],
            'n_topics': len(run_topic_ids),
            'n_noise': n_noise,
            'noise_rate': round(noise_rate, 4),
            'baseline_topics_matched_jge0.5': matched,
            'match_rate': round(matched / len(base_topics), 4),
            'mean_best_jaccard': round(float(bj_vals.mean()), 4),
            'median_best_jaccard': round(float(np.median(bj_vals)), 4),
            'candidates_retained_20': retained,
            'candidate_retention_rate': round(retained / len(candidates), 4),
            'runtime_sec': round(time.time() - t0, 1),
        })
        print(f'  topics={len(run_topic_ids)}, noise={noise_rate:.1%}, '
              f'matched(J>=0.5)={matched}/{len(base_topics)}, '
              f'meanJ={bj_vals.mean():.3f}, candidates={retained}/20, '
              f'{time.time()-t0:.0f}s')

        # Per-run topic summary for human inspection (labels legible)
        topic_model.get_topic_info().to_csv(
            RUNS / f'topic_summary_{cfg["name"]}.csv', index=False,
            encoding='utf-8-sig')
        pd.DataFrame({'patent_number': patent_numbers, 'topic': topics}).to_csv(
            RUNS / f'doc_topics_{cfg["name"]}.csv', index=False, encoding='utf-8-sig')

    # --- Outputs ---
    runs_df = pd.DataFrame(run_rows)
    runs_df.to_csv(OUT / 'bertopic_stability_runs.csv', index=False, encoding='utf-8-sig')

    cand_df = pd.DataFrame(cand_rows)
    cand_df.to_csv(OUT / 'bertopic_stability_candidate_detail.csv',
                   index=False, encoding='utf-8-sig')
    # Fate matrix: 20 candidates x 9 configs, cell = best Jaccard
    matrix = cand_df.pivot(index='baseline_topic', columns='config',
                           values='best_jaccard')
    matrix.to_csv(OUT / 'bertopic_stability_candidate_retention.csv',
                  encoding='utf-8-sig')

    meta = {'configs': CONFIGS, 'jaccard_match_threshold': JACCARD_MATCH_THRESHOLD,
            'dataset': os.environ['PATSENSE_DATASET'],
            'baseline': {'n_topics': len(base_topics), 'n_noise': n_base_noise,
                         'noise_rate': round(n_base_noise/len(base_topic), 4)},
            'total_runtime_sec': round(time.time() - t_start, 1)}
    with open(OUT / 'stability_meta.json', 'w', encoding='utf-8') as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)

    print('\n' + '=' * 70)
    print(runs_df.to_string(index=False))
    print(f'\nTotal runtime: {time.time()-t_start:.0f}s')
    print(f'Outputs in {OUT}')


if __name__ == '__main__':
    main()
