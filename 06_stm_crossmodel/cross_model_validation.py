# -*- coding: utf-8 -*-
# ============================================================================
# cross_model_validation.py  |  Tier 1 (active)
# Purpose : Document-level BERTopic x STM validation: project each patent through STM, aggregate per topic, test Egami C2/C10 decay.
# Input   : output/time_analysis/ CSVs and/or data/humanoid_safety_patents.xlsx (via engine.data)
# Output  : output/time_analysis/08_cross_model/cross_model_validation.csv
# Usage   : python scripts/cross_model_validation.py
# Asimov Cascade humanoid-safety patent pipeline
# ----------------------------------------------------------------------------
# HOW IT WORKS:
#   1. Project each patent through the fitted STM (fitNewDocuments) to a theta topic vector.
#   2. Aggregate theta per BERTopic topic -> that topic's STM composition.
#   3. Read the Egami C2/C10 covariate effect; a significant negative effect = STM confirms decay.
#   4. Label each topic CONFIRMED / BERTopic-ONLY / STM-ONLY / LOW-CONSENSUS.
#   5. Write cross_model_validation.csv (T16 is the single CONFIRMED signal).
# ============================================================================

"""scripts/cross_model_validation.py — BERTopic+STM Dual-Pathway Validation.

v5 NEW (2026-07-11): Replaces the old 1:1 topic mapping (cosine=0.505) with
document-level projection. Instead of forcing a 65→12 topic alignment, each
patent is independently projected through STM, then aggregated per BERTopic topic.

Collaboration model: BERTopic = primary path (safety semantics + HMM trends),
STM = verification path (covariate-aware causal inference via C2/C10 effects).

Novelty: No paper has fused BERTopic+STM into a single risk validation framework.

Usage: <python>/envs/<env>/python.exe scripts/cross_model_validation.py
"""

import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.path.insert(0, '.')
sys.path.insert(0, r'<project>/.claude\skills\scientific-visualization\scripts')
from style_presets import apply_publication_style
apply_publication_style('default')

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import seaborn as sns
import pandas as pd
import numpy as np
from pathlib import Path
import warnings
warnings.filterwarnings('ignore')

from engine.style import CANDY_PALETTE, set_style, save_figure
set_style(font_scale=1.1)
CANDY = CANDY_PALETTE

# ---- Paths ----
PROJECT = Path(r'<project>/Cascade\BERT_Python')
OUT_BASE = PROJECT / 'output' / 'time_analysis'
STM_DIR = OUT_BASE / '04_stm'
BERTOPIC_DIR = OUT_BASE / '04_bertopic_time'
CASCADE_DIR = OUT_BASE / '11_temporal_enrichment' / '06_cascade_v3'
CROSS_DIR = OUT_BASE / '08_cross_model'
CROSS_DIR.mkdir(parents=True, exist_ok=True)

DOC_TOPIC = BERTOPIC_DIR / 'document_topic_assignment.csv'
CASCADE_V4 = CASCADE_DIR / 'cascade_signals_v4.csv'
CASCADE_V5 = CASCADE_DIR / 'cascade_signals_v5.csv'
STM_SPLIT = STM_DIR / 'stm_split_info.csv'
STM_THETA_TRAIN = STM_DIR / 'stm_theta_train.csv'
STM_THETA_TEST = STM_DIR / 'stm_theta_test.csv'
STM_EGAMI = STM_DIR / 'stm_egami_effects.csv'
STM_KEYWORDS = STM_DIR / 'stm_topic_keywords.csv'
STM_DOC_TOPICS = STM_DIR / 'stm_doc_topics.csv'


def build_full_theta():
    """Concatenate train+test theta into full 8,928×12 matrix, aligned by doc_id."""
    split = pd.read_csv(STM_SPLIT)
    train = pd.read_csv(STM_THETA_TRAIN)
    test = pd.read_csv(STM_THETA_TEST)

    # Build full theta: 8,928 rows × 12 topics (exclude doc_id column)
    n_total = len(split)
    topic_cols = [c for c in train.columns if c.startswith('topic_')]
    n_topics = len(topic_cols)
    full_theta = np.zeros((n_total, n_topics))

    train_idx = 0
    test_idx = 0
    for i in range(n_total):
        if split.iloc[i]['split'] == 'train':
            full_theta[i] = train.iloc[train_idx][topic_cols].values
            train_idx += 1
        else:
            full_theta[i] = test.iloc[test_idx][topic_cols].values
            test_idx += 1

    print(f'  Full theta: {full_theta.shape} ({n_topics} STM topics, train={train_idx}, test={test_idx})')
    return full_theta


def build_egami_lookup():
    """Build lookup: (STM_topic, covariate) → (coefficient, p_value)."""
    egami = pd.read_csv(STM_EGAMI)
    lookup = {}
    for _, row in egami.iterrows():
        key = (int(row['topic']), row['covariate'])
        lookup[key] = {
            'coefficient': row['coefficient'],
            'p_value': row['p_value'],
            'ci_lower': row['ci_lower'],
            'ci_upper': row['ci_upper'],
        }
    print(f'  Egami lookup: {len(lookup)} (topic, covariate) pairs')
    return lookup


def get_stm_mirror(bertopic_id, doc_topic, full_theta, egami_lookup):
    """For a given BERTopic topic, compute its STM mirror.

    Args:
        bertopic_id: BERTopic topic ID
        doc_topic: DataFrame with columns [topic, patent_number] (8,928 rows, 0-indexed)
        full_theta: np.array (8928, 12) STM theta per patent
        egami_lookup: dict (STM_topic, covariate) → {coefficient, p_value}

    Returns:
        dict with dominant STM topic, mean theta, C2/C10 effects, convergence label
    """
    # Find all patents belonging to this BERTopic topic
    mask = doc_topic['topic'] == bertopic_id
    n_patents = mask.sum()

    if n_patents == 0:
        return None

    # Get STM theta for these patents
    theta_subset = full_theta[mask.values]  # (n_patents, 12)
    mean_theta = theta_subset.mean(axis=0)  # (12,)
    dominant_stm = int(np.argmax(mean_theta)) + 1  # STM topics are 1-indexed

    # Query C2 and C10 effects for the dominant STM topic
    c2_key = (dominant_stm, 'C2_std')
    c10_key = (dominant_stm, 'C10_std')

    c2 = egami_lookup.get(c2_key, {'coefficient': 0, 'p_value': 1.0})
    c10 = egami_lookup.get(c10_key, {'coefficient': 0, 'p_value': 1.0})

    # Decay confirmed if C2 or C10 has significant negative coefficient
    stm_decay = (
        (c2['coefficient'] < 0 and c2['p_value'] < 0.05) or
        (c10['coefficient'] < 0 and c10['p_value'] < 0.05)
    )

    return {
        'n_patents': int(n_patents),
        'dominant_stm_topic': dominant_stm,
        'stm_theta_mean': float(mean_theta[dominant_stm - 1]),
        'stm_theta_top3': ', '.join(
            f'T{i+1}={mean_theta[i]:.3f}' for i in np.argsort(-mean_theta)[:3]
        ),
        'c2_effect': float(c2['coefficient']),
        'c2_pvalue': float(c2['p_value']),
        'c10_effect': float(c10['coefficient']),
        'c10_pvalue': float(c10['p_value']),
        'stm_decay_confirmed': stm_decay,
    }


def assign_convergence_label(bertopic_risk, stm_decay, cascade_score):
    """Assign dual-pathway convergence label.

    CONFIRMED:     Both paths agree on HIGH risk
    BERTopic-ONLY: BERTopic says HIGH but STM doesn't confirm
    STM-ONLY:      STM detects decay but BERTopic says LOW/MEDIUM
    LOW-CONSENSUS: Both paths agree on LOW/MEDIUM
    """
    bertopic_high = bertopic_risk in ('HIGH', 'MEDIUM')

    if bertopic_high and stm_decay:
        return 'CONFIRMED'
    elif bertopic_high and not stm_decay:
        return 'BERTopic-ONLY'
    elif not bertopic_high and stm_decay:
        return 'STM-ONLY'
    else:
        return 'LOW-CONSENSUS'


def plot_convergence(results_df):
    """Plot convergence summary: bar chart of labels + scatter of scores vs STM effects."""
    fig, axes = plt.subplots(1, 2, figsize=(14, 5))

    # Left: convergence label distribution
    ax = axes[0]
    label_counts = results_df['convergence_label'].value_counts()
    label_order = ['CONFIRMED', 'BERTopic-ONLY', 'STM-ONLY', 'LOW-CONSENSUS']
    colors = ['#DC143C', '#FF8C00', '#4169E1', '#CCCCCC']
    present_labels = [l for l in label_order if l in label_counts.index]
    present_colors = [colors[i] for i, l in enumerate(label_order) if l in label_counts.index]

    ax.bar(present_labels, [label_counts[l] for l in present_labels],
           color=present_colors, alpha=0.8, edgecolor='white')
    ax.set_ylabel('Number of Topics')
    ax.set_title('Dual-Pathway Convergence\nBERTopic × STM Cross-Validation')
    for i, l in enumerate(present_labels):
        ax.text(i, label_counts[l] + 0.3, str(label_counts[l]), ha='center', fontweight='bold')
    sns.despine(ax=ax)

    # Right: cascade_score vs STM decay (C10 effect)
    ax = axes[1]
    safety_topics = results_df[results_df['safety_score'] >= 2].copy()
    if not safety_topics.empty:
        for label, color in zip(label_order, colors):
            subset = safety_topics[safety_topics['convergence_label'] == label]
            if not subset.empty:
                ax.scatter(subset['cascade_score'], -subset['c10_effect'],
                          c=color, label=f'{label} ({len(subset)})',
                          s=80, alpha=0.8, edgecolors='white', zorder=3)
                for _, r in subset.iterrows():
                    ax.annotate(f'T{int(r["bertopic_id"])}',
                              (r['cascade_score'], -r['c10_effect']),
                              fontsize=6, fontweight='bold', ha='center', va='bottom',
                              xytext=(0, 5), textcoords='offset points')

        ax.axhline(0, color='gray', linestyle='--', alpha=0.3)
        ax.set_xlabel('Cascade Score (BERTopic Path A)')
        ax.set_ylabel('STM C10 Negative Effect\n(higher = more decay)')
        ax.set_title('Cross-Model Validation\nBERTopic Cascade Score × STM C10 Decay')
        ax.legend(fontsize=7)
        sns.despine(ax=ax)

    fig.suptitle('CV1: BERTopic+STM Dual-Pathway Validation', fontweight='bold', fontsize=14, y=1.02)
    fig.tight_layout()
    save_figure(fig, 'CV1_convergence', CROSS_DIR, close=True)


def main():
    print('=' * 60)
    print('BERTopic+STM Dual-Pathway Cross-Validation (v5)')
    print('=' * 60)

    # Load data
    print('\nLoading data...')
    doc_topic = pd.read_csv(DOC_TOPIC, encoding='utf-8-sig')

    # Cascade scores (prefer v5, fall back to v4)
    if CASCADE_V5.exists():
        cascade = pd.read_csv(CASCADE_V5, encoding='utf-8-sig')
        print('  Using cascade_signals_v5.csv')
    else:
        cascade = pd.read_csv(CASCADE_V4, encoding='utf-8-sig')
        print('  Using cascade_signals_v4.csv (v5 not found)')

    # Build STM resources
    full_theta = build_full_theta()
    egami_lookup = build_egami_lookup()

    # Get STM keywords for interpretation
    stm_keywords = pd.read_csv(STM_KEYWORDS)

    # Phase 1: For every BERTopic topic, compute STM mirror
    print('\nPhase 1: Computing STM mirrors for all BERTopic topics...')
    bertopic_ids = sorted(doc_topic['topic'].unique())
    bertopic_ids = [t for t in bertopic_ids if t >= 0]  # exclude noise

    results = []
    for btid in bertopic_ids:
        mirror = get_stm_mirror(btid, doc_topic, full_theta, egami_lookup)
        if mirror is None:
            continue

        # Get BERTopic cascade info
        c_row = cascade[cascade['bertopic_id'] == btid]
        if len(c_row) == 0:
            continue

        bertopic_risk = c_row.iloc[0].get('risk_level', 'LOW')
        cascade_score = c_row.iloc[0].get('cascade_score', 0)
        safety_score = c_row.iloc[0].get('safety_score', 0)
        bertopic_name = c_row.iloc[0].get('bertopic_name', f'Topic_{btid}')

        convergence = assign_convergence_label(
            bertopic_risk, mirror['stm_decay_confirmed'], cascade_score
        )

        # Get STM keywords for the dominant topic
        stm_kw_row = stm_keywords[stm_keywords['topic'] == mirror['dominant_stm_topic']]
        stm_prob_words = stm_kw_row['prob_words'].values[0] if len(stm_kw_row) > 0 else ''

        results.append({
            'bertopic_id': btid,
            'bertopic_name': bertopic_name,
            'safety_score': safety_score,
            'cascade_score': cascade_score,
            'risk_level': bertopic_risk,
            'n_patents': mirror['n_patents'],
            'dominant_stm_topic': mirror['dominant_stm_topic'],
            'stm_theta_mean': mirror['stm_theta_mean'],
            'stm_theta_top3': mirror['stm_theta_top3'],
            'stm_prob_words': stm_prob_words,
            'c2_effect': mirror['c2_effect'],
            'c2_pvalue': mirror['c2_pvalue'],
            'c10_effect': mirror['c10_effect'],
            'c10_pvalue': mirror['c10_pvalue'],
            'stm_decay_confirmed': mirror['stm_decay_confirmed'],
            'convergence_label': convergence,
        })

    df = pd.DataFrame(results)

    # Phase 2: Check for duplicate STM topic assignments
    print('\nPhase 2: Checking for STM topic duplication...')
    stm_topic_counts = df.groupby('dominant_stm_topic').size()
    duplicates = stm_topic_counts[stm_topic_counts > 1]
    if not duplicates.empty:
        print(f'  ⚠ {len(duplicates)} STM topics assigned to multiple BERTopic topics:')
        for stm_tid, count in duplicates.items():
            btopics = df[df['dominant_stm_topic'] == stm_tid]['bertopic_id'].tolist()
            print(f'    STM T{stm_tid}: {count} BERTopic topics → {btopics}')
    else:
        print('  ✓ No duplicate STM topic assignments (each BERTopic → unique STM)')

    # Phase 3: Convergence summary
    print('\nPhase 3: Convergence Summary:')
    for label in ['CONFIRMED', 'BERTopic-ONLY', 'STM-ONLY', 'LOW-CONSENSUS']:
        subset = df[df['convergence_label'] == label]
        if not subset.empty:
            topics_str = ', '.join(f'T{int(t)}' for t in subset['bertopic_id'])
            print(f'  {label:16s}: {len(subset):2d} topics → {topics_str}')

    # Highlight CONFIRMED topics (both paths agree)
    confirmed = df[df['convergence_label'] == 'CONFIRMED']
    if not confirmed.empty:
        print(f'\n  ★ CONFIRMED cascade signals (dual-model agreement):')
        for _, r in confirmed.iterrows():
            print(f'    T{int(r["bertopic_id"]):2d} {r["bertopic_name"][:45]} '
                  f'| STM→T{r["dominant_stm_topic"]} θ={r["stm_theta_mean"]:.3f} '
                  f'| C10={r["c10_effect"]:.3f} (p={r["c10_pvalue"]:.3f})')

    stm_only = df[df['convergence_label'] == 'STM-ONLY']
    if not stm_only.empty:
        print(f'\n  ⚡ STM-ONLY (STM detected decay that BERTopic missed):')
        for _, r in stm_only.iterrows():
            print(f'    T{int(r["bertopic_id"]):2d} {r["bertopic_name"][:45]} '
                  f'| cascade={r["cascade_score"]:.4f} (BERTopic: {r["risk_level"]}) '
                  f'| STM C10={r["c10_effect"]:.3f} p={r["c10_pvalue"]:.3f}')

    # Save
    out_cols = [
        'bertopic_id', 'bertopic_name', 'safety_score', 'cascade_score', 'risk_level',
        'n_patents', 'dominant_stm_topic', 'stm_theta_mean', 'stm_theta_top3',
        'stm_prob_words', 'c2_effect', 'c2_pvalue', 'c10_effect', 'c10_pvalue',
        'stm_decay_confirmed', 'convergence_label',
    ]
    df[out_cols].to_csv(CROSS_DIR / 'cross_model_validation.csv', index=False, encoding='utf-8-sig')
    print(f'\nSaved: cross_model_validation.csv ({len(df)} topics)')

    # Plot
    plot_convergence(df)

    print(f'\n  Output: {CROSS_DIR}')
    print(f'{"=" * 60}')


if __name__ == '__main__':
    main()
