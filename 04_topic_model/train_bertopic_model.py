# -*- coding: utf-8 -*-
# ============================================================================
# train_bertopic_model.py  |  Tier 1 (active)
# Purpose : Train the BERTopic model (65 topics) over title+abstract+first-claim.
# Input   : output/time_analysis/ CSVs and/or data/humanoid_safety_patents.xlsx (via engine.data)
# Output  : output/time_analysis/04_bertopic_time/topic_summary.csv
# Usage   : python scripts/train_bertopic_model.py
# Asimov Cascade humanoid-safety patent pipeline
# ============================================================================

"""scripts/train_bertopic_model.py — Train (or load cached) BERTopic model.

v5 UPGRADE (2026-07-11): PatentSBERTa_V2 (768d) replaces all-MiniLM-L6-v2 (384d).
Falls back to all-MiniLM-L6-v2 if PatentSBERTa download fails.

Usage: python scripts/train_bertopic_model.py [--legacy-embedding]
"""

import sys, io, os, json
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.path.insert(0, '.')
sys.path.insert(0, r'<project>/.claude\skills\scientific-visualization\scripts')

import pandas as pd
import numpy as np
from pathlib import Path

from engine.data import load_and_prepare

OUT = Path(r'<project>/Cascade\BERT_Python\output\time_analysis\04_bertopic_time')
OUT.mkdir(parents=True, exist_ok=True)
MODEL_CACHE = OUT / 'bertopic_model.pkl'
TOPICS_CACHE = OUT / 'topic_assignments.json'


def train_or_load():
    """Train BERTopic if not cached, otherwise load from disk."""
    if MODEL_CACHE.exists() and TOPICS_CACHE.exists():
        print('Loading cached BERTopic model...')
        from bertopic import BERTopic
        topic_model = BERTopic.load(str(MODEL_CACHE))
        with open(TOPICS_CACHE, 'r') as f:
            saved = json.load(f)
        topics = saved['topics']
        print(f'  Loaded: {len(set(topics)) - 1} topics + noise')
        return topic_model, topics

    print('Training BERTopic (2-3 minutes)...')

    from bertopic import BERTopic
    from umap import UMAP
    from hdbscan import HDBSCAN
    from sklearn.feature_extraction.text import CountVectorizer
    from sentence_transformers import SentenceTransformer

    print('  Loading data...')
    df, documents, timestamps = load_and_prepare()

    print('  Loading embedding model...')
    use_legacy = '--legacy-embedding' in sys.argv
    # v5: tunable via CLI (defaults keep v1 behavior unchanged)
    def _cli_int(flag, default):
        return int(sys.argv[sys.argv.index(flag) + 1]) if flag in sys.argv else default
    min_cluster_size = _cli_int('--min-cluster-size', 5)
    n_neighbors = _cli_int('--n-neighbors', 5)
    print(f'  Params: min_cluster_size={min_cluster_size}, n_neighbors={n_neighbors}')
    EMBEDDING_MODEL_NAME = 'sentence-transformers/all-MiniLM-L6-v2' if use_legacy else 'AAUBS/PatentSBERTa_V2'
    try:
        embedding_model = SentenceTransformer(EMBEDDING_MODEL_NAME)
        print(f'  Using: {EMBEDDING_MODEL_NAME} ({embedding_model.get_sentence_embedding_dimension()}d)')
    except Exception as e:
        if not use_legacy:
            print(f'  [WARN] PatentSBERTa download failed ({e})')
            print(f'  [WARN] Falling back to all-MiniLM-L6-v2')
            embedding_model = SentenceTransformer('sentence-transformers/all-MiniLM-L6-v2')
        else:
            raise

    print('  Computing embeddings...')
    embeddings = embedding_model.encode(documents, show_progress_bar=True)
    emb_dim = embeddings.shape[1]

    umap_model = UMAP(
        n_neighbors=n_neighbors, n_components=min(5, emb_dim - 1), min_dist=0,
        metric='cosine', random_state=42
    )
    hdbscan_model = HDBSCAN(
        min_cluster_size=min_cluster_size, min_samples=3, metric='euclidean',
        cluster_selection_method='eom', prediction_data=True
    )
    vectorizer_model = CountVectorizer(
        ngram_range=(1, 2), stop_words='english'
    )

    topic_model = BERTopic(
        embedding_model=embedding_model,
        umap_model=umap_model,
        hdbscan_model=hdbscan_model,
        vectorizer_model=vectorizer_model,
        calculate_probabilities=True,
        verbose=True,
        top_n_words=50,
    )

    print('  Fitting BERTopic...')
    topics, probs = topic_model.fit_transform(documents, embeddings)

    print('  Saving model...')
    topic_model.save(str(MODEL_CACHE), save_embedding_model=False)
    with open(TOPICS_CACHE, 'w') as f:
        json.dump({'topics': [int(t) for t in topics]}, f)

    print(f'  Trained: {len(set(topics)) - 1} topics + noise')
    return topic_model, topics


if __name__ == '__main__':
    topic_model, topics = train_or_load()

    # Export metadata
    topic_info = topic_model.get_topic_info()
    topic_info.to_csv(OUT / 'topic_summary.csv', index=False, encoding='utf-8-sig')
    print(f'Saved topic_summary.csv ({len(topic_info)} rows)')

    # Build document-topic assignment
    df, documents, timestamps = load_and_prepare()
    document_info = topic_model.get_document_info(documents)
    df['topic'] = document_info['Topic'].values
    df['topic_label'] = ['Noise' if t == -1 else f'T{t}' for t in df['topic']]

    doc_topic_df = pd.DataFrame({
        'patent_number': df['patent_number'].values,
        'topic': df['topic'].values,
        'topic_label': df['topic_label'].values,
        'app_year': df['app_year'].values if 'app_year' in df.columns else np.nan,
        'country_code': df['country_code'].values if 'country_code' in df.columns else 'Unknown',
    })
    doc_topic_df.to_csv(OUT / 'document_topic_assignment.csv', index=False, encoding='utf-8-sig')
    print(f'Saved document_topic_assignment.csv ({len(doc_topic_df)} rows)')

    print('\nTraining complete.')
