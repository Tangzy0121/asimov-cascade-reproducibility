# -*- coding: utf-8 -*-
# ============================================================================
# run_stm_phase3.py  |  Tier 1 (active)
# Purpose : Python bridge that builds stm_input.csv and runs the STM (K=12) Egami analysis in R.
# Input   : output/time_analysis/ CSVs and/or data/humanoid_safety_patents.xlsx (via engine.data)
# Output  : output/time_analysis/04_stm/stm_egami_effects.csv
# Usage   : python scripts/run_stm_phase3.py
# Asimov Cascade humanoid-safety patent pipeline
# ============================================================================

"""scripts/run_stm_phase3.py — Python bridge + visualization for Phase 3 STM.

Orchestrates: generate stm_input.csv → call run_stm_phase3.R → 6 figures (S1-S6)
All figures saved to output/time_analysis/04_stm/.

Usage: python scripts/run_stm_phase3.py
"""
import sys, io, os, subprocess
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.path.insert(0, '.')
sys.path.insert(0, r'<project>/.claude\skills\scientific-visualization\scripts')
from style_presets import apply_publication_style
apply_publication_style('default')

import matplotlib.pyplot as plt
import seaborn as sns
import pandas as pd
import numpy as np
from pathlib import Path

from engine.data import load_and_prepare
from engine.time_concepts import compute_all_concepts
from engine.style import CANDY_PALETTE, CANDY_HEATMAP, set_style, save_figure

set_style(font_scale=1.1)

OUT = Path('output/time_analysis/04_stm')
OUT.mkdir(parents=True, exist_ok=True)
STM_R = Path(r'<project>/Cascade/STM_R/run_stm_phase3.R')
RSCRIPT = 'Rscript'  # assumes Rscript is on PATH; set an absolute path here if needed


# ============================================================
# 1. Generate stm_input.csv
# ============================================================
def generate_stm_input():
    csv_path = OUT / 'stm_input.csv'
    if csv_path.exists():
        print(f'stm_input.csv exists ({csv_path.stat().st_size} bytes). Skip.')
        return csv_path

    print('Generating stm_input.csv...')
    df, documents, timestamps = load_and_prepare()
    df = compute_all_concepts(df)
    df['doc_id'] = range(len(df))
    df['text'] = df['combined_text']
    df['year'] = df['app_year'].astype(int)

    if 'IPC Main Subgroup' in df.columns:
        sec = df['IPC Main Subgroup'].astype(str).str.strip().str[0]
        df['ipc_section'] = sec.where(sec.isin(list('ABCDEFGH')), 'UNK')
    else:
        df['ipc_section'] = 'UNK'

    if 'Publication Authority' in df.columns:
        auth = df['Publication Authority'].astype(str).str.strip()
    else:
        auth = df.get('country_simple', pd.Series(['Other'] * len(df)))
    # incoPat publication-authority labels (Chinese keys), matched verbatim
    # against the raw export
    mapping = {'China': 'China', 'India': 'India', 'United States': 'US',
               '中国': 'China', '美国': 'US', '印度': 'India',
               '日本': 'Japan', '韩国': 'Korea', '德国': 'Germany',
               '英国': 'UK', '法国': 'France', '俄罗斯': 'Russia'}
    df['authority'] = auth.map(mapping).fillna('Other')

    concept_cols = [f'C{i}' for i in range(1, 25)]
    avail_concepts = [c for c in concept_cols if c in df.columns and c != 'CPC']
    missing_concepts = [c for c in concept_cols if c not in df.columns]
    if missing_concepts:
        print(f'  Note: {missing_concepts} unavailable (missing source date columns in incoPat export)')
    out_df = df[['doc_id', 'text', 'year', 'ipc_section', 'authority'] + avail_concepts]
    out_df.to_csv(csv_path, index=False, encoding='utf-8-sig')

    print(f'Wrote {csv_path}: {len(out_df)} rows')
    for cc in avail_concepts:
        na = out_df[cc].isna().sum()
        print(f'  {cc}: {len(out_df)-na}/{len(out_df)} non-null ({100*(len(out_df)-na)/len(out_df):.0f}%)')
    return csv_path


# ============================================================
# 2. Call R
# ============================================================
def call_r():
    effects_csv = OUT / 'stm_egami_effects.csv'
    if effects_csv.exists():
        print(f'STM outputs exist. Skipping R. (Delete {OUT}/*.csv to re-run)')
        return True

    print(f'Running: {RSCRIPT} {STM_R}')
    result = subprocess.run(
        [RSCRIPT, str(STM_R)],
        capture_output=True, text=True, encoding='utf-8',
        cwd=str(STM_R.parent)
    )
    print(result.stdout)
    if result.returncode != 0:
        print('STDERR:', result.stderr[-800:])
        raise RuntimeError(f'R script failed (code {result.returncode})')
    print('R completed.')
    return True


# ============================================================
# 3. Load results
# ============================================================
def load_results():
    kw   = pd.read_csv(OUT / 'stm_topic_keywords.csv')
    prev = pd.read_csv(OUT / 'stm_topic_prevalence.csv')
    eff  = pd.read_csv(OUT / 'stm_egami_effects.csv')
    corr = pd.read_csv(OUT / 'stm_topic_corr.csv', index_col=0)
    doc  = pd.read_csv(OUT / 'stm_doc_topics.csv')
    print(f'Loaded: {len(kw)} topics, {len(eff)} effects, {len(doc)} test docs')
    return kw, prev, eff, corr, doc


# ============================================================
# 4. S1: STM Topic Summary
# ============================================================
def fig_s1(kw, prev):
    merged = prev.merge(kw, on='topic').sort_values('prevalence', ascending=True)

    fig, ax = plt.subplots(figsize=(8, 6.5))
    colors = [CANDY_PALETTE[i % 8] for i in range(len(merged))]
    ax.barh(range(len(merged)), merged['prevalence'].values, color=colors, alpha=0.85)

    labels = []
    for _, r in merged.iterrows():
        words = r['prob_words'].split(', ')[:3]
        pct = r['prevalence'] * 100
        labels.append(f'T{r["topic"]}: {", ".join(words)}  ({pct:.1f}%)')
    ax.set_yticks(range(len(merged)))
    ax.set_yticklabels(labels, fontsize=7)
    ax.set_xlabel('Expected Topic Proportion')
    ax.set_title(f'S1: STM Topic Prevalence  (K = {len(merged)})', fontweight='bold', fontsize=11)
    sns.despine()
    save_figure(fig, 'S1_stm_topic_summary', OUT)


# ============================================================
# 5. S2: Egami Coefficient Forest Plot (CORE)
# ============================================================
def fig_s2(eff):
    fig, axes = plt.subplots(1, 2, figsize=(10, 6))
    cv_names = {'C2_std': 'Disclosure Speed (C2)', 'C10_std': 'Priority Urgency (C10)'}
    # Distinct colors per covariate: green/teal for C2, blue for C10
    cv_colors = {
        'C2_std':  {'sig': '#27AE60', 'ns': '#B0D8B0'},   # green / light green
        'C10_std': {'sig': '#2980B9', 'ns': '#A0C8E8'},   # blue  / light blue
    }

    for ax, cv in zip(axes, ['C2_std', 'C10_std']):
        sub = eff[eff['covariate'] == cv].sort_values('coefficient')
        if len(sub) == 0:
            ax.text(0.5, 0.5, 'No data', ha='center', va='center')
            continue
        y_pos = range(len(sub))
        cc = cv_colors[cv]
        for i, (_, r) in enumerate(sub.iterrows()):
            sig = r['p_value'] < 0.05
            color = cc['sig'] if sig else cc['ns']
            ax.errorbar(r['coefficient'], i,
                        xerr=[[r['coefficient'] - r['ci_lower']],
                              [r['ci_upper'] - r['coefficient']]],
                        fmt='o', color=color, capsize=2, markersize=5,
                        alpha=0.9 if sig else 0.5, markeredgewidth=0)

        ax.axvline(0, color='#333333', linestyle='--', linewidth=0.8)
        ax.set_yticks(list(y_pos))
        ax.set_yticklabels([f'T{int(r["topic"])}' for _, r in sub.iterrows()], fontsize=7)
        ax.set_xlabel('Coefficient (Δ prevalence per 1-SD increase)')
        n_sig = (sub['p_value'] < 0.05).sum()
        ax.set_title(f'{cv_names.get(cv, cv)}  ({n_sig}/{len(sub)} sig)',
                     fontweight='bold', fontsize=10)
        sns.despine(ax=ax)

    fig.suptitle('S2: Egami Effect Estimates — Time → Topic Causal Effects (95% CI)',
                 fontweight='bold', fontsize=12, y=1.02)
    plt.tight_layout()
    save_figure(fig, 'S2_egami_coefplot', OUT)


# ============================================================
# 6. S3: Topic Correlation Network
# ============================================================
def fig_s3(corr_matrix, prev):
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 5.5))

    # Left: heatmap
    mask = np.triu(np.ones_like(corr_matrix, dtype=bool), k=1)
    sns.heatmap(corr_matrix, mask=mask, cmap=CANDY_HEATMAP, ax=ax1,
                vmin=-1, vmax=1, center=0,
                cbar_kws={'shrink': 0.6, 'label': 'Spearman ρ'},
                square=True, linewidths=0.3)
    ax1.set_title('Topic Correlation Matrix', fontweight='bold', fontsize=10)

    # Right: network
    try:
        import networkx as nx
        G = nx.Graph()
        for i in range(len(corr_matrix)):
            node_size = prev.iloc[i]['prevalence'] if i < len(prev) else 0.05
            G.add_node(i, size=node_size)

        for i in range(len(corr_matrix)):
            for j in range(i + 1, len(corr_matrix)):
                r = corr_matrix.iloc[i, j]
                if abs(r) > 0.3:
                    G.add_edge(i, j, weight=abs(r))

        pos = nx.spring_layout(G, seed=42, k=1.5)
        sizes = [G.nodes[n].get('size', 0.05) * 2500 for n in G.nodes()]
        node_colors = [CANDY_PALETTE[n % 8] for n in G.nodes()]
        nx.draw_networkx_nodes(G, pos, ax=ax2, node_size=sizes,
                               node_color=node_colors, alpha=0.85, edgecolors='white')
        nx.draw_networkx_edges(G, pos, ax=ax2, alpha=0.35, width=1.5,
                               edge_color='#666666')
        nx.draw_networkx_labels(G, pos, ax=ax2, font_size=7, font_weight='bold',
                                labels={n: f'T{n+1}' for n in G.nodes()})
        n_edges = G.number_of_edges()
        ax2.set_title(f'Co-occurrence Network\n(|ρ| > 0.3, {n_edges} edges)',
                      fontweight='bold', fontsize=10)
    except ImportError:
        ax2.text(0.5, 0.5, 'networkx not installed', ha='center', va='center',
                 transform=ax2.transAxes)
        ax2.set_title('Network (requires networkx)', fontweight='bold', fontsize=10)
    ax2.axis('off')

    fig.suptitle('S3: STM Topic Correlations', fontweight='bold', fontsize=12, y=1.01)
    try:
        plt.tight_layout()
    except RuntimeError:
        plt.subplots_adjust(wspace=0.3)
    save_figure(fig, 'S3_topic_correlation_network', OUT)


# ============================================================
# 7. S4: STM vs BERTopic Cross-tabulation
# ============================================================
def fig_s4(stm_doc):
    bt_path = Path('output/time_analysis/04_bertopic_time/document_topic_assignment.csv')
    if not bt_path.exists():
        print('S4 skipped: BERTopic CSV not found')
        return

    bt = pd.read_csv(bt_path)
    # Align by row index: both files generated from same load_and_prepare() ordering
    # STM doc_topics has test-set subset; BERTopic has all 1274 docs
    # Intersect: keep only rows where stm_doc.doc_id matches bt's row index
    merged = stm_doc.copy()
    merged['topic_bt'] = bt.loc[merged['doc_id'].values, 'topic'].values
    merged = merged.dropna(subset=['topic_bt'])
    if len(merged) == 0:
        print('S4 skipped: no overlapping rows')
        return

    ct = pd.crosstab(merged['dominant_topic'], merged['topic_bt'].astype(int))
    ct_norm = ct.div(ct.sum(axis=1), axis=0)

    fig, ax = plt.subplots(figsize=(14, 6))
    sns.heatmap(ct_norm, annot=ct.where(ct > 0, np.nan), fmt='.0f',
                cmap=CANDY_HEATMAP, ax=ax,
                cbar_kws={'shrink': 0.5, 'label': 'Row Proportion'},
                linewidths=0.3, annot_kws={'fontsize': 6})
    ax.set_xlabel('BERTopic Topic')
    ax.set_ylabel('STM Topic')
    ax.set_title(f'S4: STM x BERTopic Topic Alignment  (n = {len(merged)} docs)',
                 fontweight='bold', fontsize=11)
    try:
        plt.tight_layout()
    except RuntimeError:
        plt.subplots_adjust(bottom=0.15)
    save_figure(fig, 'S4_stm_vs_bertopic', OUT)


# ============================================================
# 8. S5: Content Covariate Word Differences (placeholder)
# ============================================================
def fig_s5():
    fig, ax = plt.subplots(figsize=(8, 4))
    ax.text(0.5, 0.5,
            'S5: Content Covariate Word Differences\n'
            'CN vs US word usage per topic (sageLabels)\n'
            '(Requires rpy2 or manual R export of sageLabels)',
            ha='center', va='center', fontsize=11, color='#666666',
            transform=ax.transAxes)
    ax.set_title('S5: CN vs US Lexical Differences (Content Covariate ~ authority)',
                 fontweight='bold', fontsize=11)
    ax.axis('off')
    save_figure(fig, 'S5_content_words', OUT)


# ============================================================
# 9. S6: Model Diagnostics (placeholder)
# ============================================================
def fig_s6():
    fig, ax = plt.subplots(figsize=(6, 5))
    ax.text(0.5, 0.5,
            'S6: Semantic Coherence vs Exclusivity\n'
            '(Requires R export of topicQuality diagnostics)\n'
            'Placeholder — run R export to populate',
            ha='center', va='center', fontsize=11, color='#666666',
            transform=ax.transAxes)
    ax.set_title('S6: Model Diagnostics', fontweight='bold', fontsize=11)
    ax.axis('off')
    save_figure(fig, 'S6_diagnostics', OUT)


# ============================================================
# Main
# ============================================================
if __name__ == '__main__':
    print('=== Phase 3 Python Bridge ===\n')
    generate_stm_input()
    call_r()
    kw, prev, eff, corr_matrix, doc = load_results()

    print('\n--- Generating S1-S6 ---')
    fig_s1(kw, prev)
    fig_s2(eff)
    fig_s3(corr_matrix, prev)
    fig_s4(doc)
    fig_s5()
    fig_s6()

    print(f'\nPhase 3 complete. Output: {OUT}')
