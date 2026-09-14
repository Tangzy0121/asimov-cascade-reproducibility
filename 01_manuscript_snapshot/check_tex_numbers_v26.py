# -*- coding: utf-8 -*-
# ============================================================================
# check_tex_numbers_v26.py  |  Tier 1 (paper-critical, READ-ONLY)
# Purpose : Diff key numbers in the current ICRA 2027 manuscript (main.tex,
#           overleaf_v26 snapshot) against on-disk authoritative outputs
#           (censoring_2024 manifest, family manifest, ASIMOV reports,
#            content-audit results, simulation payload).
#           Catches stale v5-era numbers (the old check_tex_numbers.py target
#           was <project>/PatSense\PaperWork\icra_latex\asimov_cascade.tex,
#           which no longer reflects the current paper).
# Usage   : python scripts/check_tex_numbers_v26.py
# Exit    : 0 = all PASS, 1 = any FAIL
# ============================================================================

import io, json, re, sys
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

from pathlib import Path

BASE = Path(r'<project>/Projects\PatSense\Cascade\BERT_Python')
HELP = Path(r'<project>/Help')
TEX = Path(r'<project>/<project>/\work\overleaf_v26\src\main.tex')

tex = TEX.read_text(encoding='utf-8')
tex = re.sub(r'(?<!\\)%.*', '', tex)          # strip comments
tex = tex.replace('\u2009', ' ').replace('\u202f', ' ')  # normalize thin spaces

results = []

def check(name, ok, detail=''):
    results.append((name, bool(ok), detail))

def has(pattern):
    return re.search(pattern, tex) is not None

def hasnt(pattern):
    return re.search(pattern, tex) is None

# ---------------------------------------------------------------------------
# 1. On-disk sources
# ---------------------------------------------------------------------------
cen = json.loads((BASE / 'output' / 'censoring_2024' / 'manifest.json').read_text(encoding='utf-8'))
fam = json.loads((BASE / 'output' / 'family_primary_reestimation' / 'manifest.json').read_text(encoding='utf-8'))
evi = (BASE / 'output' / 'asimov_validation' / 'evidence_report.md').read_text(encoding='utf-8')
rol = (BASE / 'output' / 'asimov_role_separated' / 'report.md').read_text(encoding='utf-8')
aud = (HELP / 'topic22_25_single_reviewer_audit' / 'audit_results.md').read_text(encoding='utf-8')
sim = (HELP / 'topic22_controlled_propagation_sim' / 'work' / 'page19_result_payload.md').read_text(encoding='utf-8')

# ---------------------------------------------------------------------------
# 2. Cross-source value checks (disk vs disk expectations, then tex presence)
# ---------------------------------------------------------------------------
# --- censoring manifest ---
check('src: censored-2024 families = 4,729', cen['n_families']['cut_2024'] == 4729)
check('src: full families = 6,602', cen['n_families']['full_2026_raw'] == 6602)
check('src: pub HIGH frozen = {7,22,25,29,40}', cen['pub_high_frozen'] == [7, 22, 25, 29, 40])
check('src: censored-2024 HIGH = {7,25,40}', cen['family_censored2024_high'] == [7, 25, 40])
check('src: T22 HIGH-lost', cen['high_lost'] == [22])
check('src: T40 HIGH-gained', cen['high_gained'] == [40])
check('src: tier changes = 6', cen['risk_changes_safety_candidates'] == 6)
check('src: trend changes = 51', cen['trend_changes_all_topics'] == 51)
check('src: lifecycle changes = 26', cen['lifecycle_changes_all_topics'] == 26)
rho, p = cen['spearman_rho_full_vs_c2024'], cen['spearman_p']
check(f'src: rho {rho:.3f} / p {p:.3f}', abs(rho - 0.487) < 0.001 and abs(p - 0.030) < 0.001)
t = cen['threshold_support']
check('src: HIGH R in [0.35,5.60]', abs(t['high_R_min'] - 0.35) < 0.01 and abs(t['high_R_max'] - 5.60) < 0.01)
check('src: threshold 0.08 / max non-HIGH 0.06', t['threshold_high'] == 0.08 and t['max_nonhigh_R'] == 0.06)

# --- family manifest representative_stats ---
rs = fam.get('representative_stats', {})
if 'n_simple_families' in rs:
    check('src: simple families 6,602', rs['n_simple_families'] == 6602)
if 'n_publications' in rs:
    check('src: publications 8,928', rs['n_publications'] == 8928)

# --- ASIMOV evidence report ---
def ev_has(pat):
    return re.search(pat, evi) is not None
check('src: ASIMOV k50 DeepSeek -3.818 p=0.0007', ev_has(r'-3\.818.*0\.0007'))
check('src: ASIMOV k50 KimiMV -2.263 p=0.1005', ev_has(r'-2\.263.*0\.1005'))
check('src: ASIMOV k25 DS -3.753 / k100 -3.835', ev_has(r'-3\.753.*0\.0013') and ev_has(r'-3\.835.*0\.0036'))
check('src: ASIMOV k25 Kimi -2.114 / k100 -2.223', ev_has(r'-2\.114.*0\.1600') and ev_has(r'-2\.223.*0\.1815'))
check('src: ASIMOV topic rho -0.231 perm 0.3669', ev_has(r'rho=-0\.231') and ev_has(r'p_perm=0\.3669'))
check('src: ASIMOV n=1276 / strict n=319', ev_has(r'\|\s*1276\s*\|') and ev_has(r'319\s*\|'))

# --- role report ---
def rol_has(pat):
    return re.search(pat, rol) is not None
check('src: role barrier pub -0.317 q .0009', rol_has(r'Barrier \| -0\.317') and rol_has(r'0\.0009492'))
check('src: role barrier fam -0.215 q .0216', rol_has(r'Barrier \| -0\.215') and rol_has(r'0\.02157'))
check('src: role propagation pub 0.104 q .425', rol_has(r'Propagation \| 0\.104') and rol_has(r'0\.4251'))
check('src: role propagation fam -0.030 q .730', rol_has(r'Propagation \| -0\.030') and rol_has(r'0\.7303'))

# --- content audit ---
def aud_has(pat):
    return re.search(pat, aud) is not None
check('src: audit direct 34/49 vs 14/38', aud_has(r'34/49') and aud_has(r'14/38'))
check('src: audit force 38/48 vs 19/37', aud_has(r'38/48') and aud_has(r'19/37'))
check('src: audit chain 32/49 vs 6/36', aud_has(r'32/49') and aud_has(r'6/36'))
check('src: audit off-topic 5/49 vs 19/38', aud_has(r'5/49') and aud_has(r'19/38'))
check('src: audit qs .00774/.0142/5.72e-05/.000229/.586',
      aud_has(r'0\.00774') and aud_has(r'0\.0142') and aud_has(r'5\.72e-05')
      and aud_has(r'0\.000229') and aud_has(r'0\.586'))
check('src: audit repeat 18/18 100%', aud_has(r'\|\s*18\s*\|') and aud_has(r'100\.0%'))

# --- simulation payload + trial CSV ---
def sim_has(pat):
    return re.search(pat, sim) is not None
check('src: sim 3,300 / 518 / 0.26% / PILOT_SUPPORT',
      sim_has(r'3[,]?300') and sim_has(r'518') and sim_has(r'0\.26%') and sim_has(r'PILOT_SUPPORT'))
check('src: sim payload mentions 369/149', sim_has(r'369') and sim_has(r'149'))

import csv as _csv
from collections import defaultdict as _dd
_sim_tot = _dd(lambda: [0, 0, 0])
with open(HELP / 'topic22_controlled_propagation_sim' / 'work' / 'outputs' / 'descriptive_results.csv',
          encoding='utf-8-sig') as _f:
    for _r in _csv.DictReader(_f):
        _c = _r['condition']
        _sim_tot[_c][0] += int(_r['n_propagated'])
        _sim_tot[_c][1] += int(_r['n_breach_unordered'])
        _sim_tot[_c][2] += int(_r['n'])
check('src: sim CSV C0 150 / C1 369(244)/900 / C2 149(151)/600 / C4 0/1,500',
      _sim_tot['C0'] == [0, 0, 150] and _sim_tot['C1'] == [369, 244, 900]
      and _sim_tot['C2'] == [149, 151, 600] and _sim_tot['C4'] == [0, 0, 1500])

# ---------------------------------------------------------------------------
# 3. TEX presence checks (the current paper must say these)
# ---------------------------------------------------------------------------
TEX_CHECKS = [
    # corpus
    ('tex: 9,710 retrieved', r'9[,]?710'),
    ('tex: 8,928 analyzed', r'8[,]?928'),
    ('tex: 77 topics', r'\b77\b'),
    ('tex: 20 candidates', r'\b20\b'),
    ('tex: 2,698 noise (30.2%)', r'2[,]?698.*30\.2'),
    ('tex: 70.1% CN share', r'70\.1'),
    ('tex: years 2006..2026', r'2006.*2026'),
    # censored primary
    ('tex: 6,602 families', r'6[,]?602'),
    ('tex: 4,729 censored families', r'4[,]?729'),
    ('tex: pub HIGH five {7,22,25,29,40}', r'Topics 7, 22, 25, 29, and 40'),
    ('tex: censored HIGH {7,25,40}', r'Topics 7, 25, and 40'),
    ('tex: T22 D 0.80 -> 0.01', r'0\.80.*0\.01'),
    ('tex: rho 0.487, p .030', r'0\.487.*p = \.030'),
    ('tex: tier changed 6 of 20', r'six review-priority tier assignments change'),
    ('tex: HMM dir 51 / lifecycle 26', has(r'trend direction changes for 51') and has(r'lifecycle stage for 26')),
    ('tex: R in [0.35,5.60]', r'0\.35, 5\.60'),
    ('tex: 4.4x threshold / 5.8x gap', r'4\.4\\times.*5\.8\\times'),
    ('tex: cutoff 0.08 / max non-HIGH 0.06', r'0\.08.*0\.06'),
    # STM
    ('tex: STM 120 tests, 38 nominal, 19 BH', r'38 of 120.*19 survived'),
    ('tex: family STM 29 nominal, 18 BH', r'29 nominal and 18'),
    ('tex: T7 p .0488 / q .1542', r'\.0488.*\.1542'),
    ('tex: T22/25 beta -0.0365', r'-0\.0365'),
    ('tex: STM splits 6,249/2,679/4,621/1,981', r'6[,]?249.*2[,]?679.*4[,]?621.*1[,]?981'),
    # ASIMOV
    ('tex: DS -3.818 (p = .0007)', r'-3\.818.*p = \.0007'),
    ('tex: Kimi -2.263 (p = .1005)', r'-2\.263.*p = \.1005'),
    ('tex: k25/k100 DS & Kimi', r'-3\.753.*\.0013.*-3\.835.*\.0036.*-2\.114.*\.160.*-2\.223.*\.181'),
    ('tex: ASIMOV 319 / 1,276 / 308', r'319.*1[,]?276.*308'),
    ('tex: topic rho -.231 p .3669', r'-.231.*\.3669'),
    ('tex: role barrier -.317 q .0009', r'-.317.*\.0009'),
    ('tex: role barrier fam -.215 q .0216', r'-.215.*\.0216'),
    ('tex: role propagation .104 q .425 / -.030 q .730', r'\.104.*\.425.*-.030.*\.730'),
    ('tex: Kimi role min q .16', r'\.16'),
    # screening
    ('tex: 17 of 20 stable', r'17 of the 20'),
    ('tex: DS Jaccard 0.956', r'0\.956'),
    ('tex: 90.6% / kappa 0.715', r'90\.6.*0\.715'),
    ('tex: frozen 69/76 (90.8%) kappa 0.750', r'69/76.*90\.8.*0\.750'),
    ('tex: PPV 14/20 (70%)', r'14/20.*70'),
    # content audit
    ('tex: audit 34/49 vs 14/38', r'34 of 49.*14 of 38'),
    ('tex: audit force 38/48 vs 19/37', r'38 of 48.*19 of 37'),
    ('tex: audit chain 32/49 vs 6/36', r'32 of 49.*6 of 36'),
    ('tex: audit off-topic 5/49 vs 19/38', r'5 of 49.*19 of 38'),
    ('tex: audit qs .00774/.0142/5.72e-5/.000229/.586', r'\.00774.*\.0142.*5\.72\\times10\^{-5\}.*\.000229.*\.586'),
    ('tex: duplicate collapse 79 rows 42 vs 37', r'79 rows: 42 versus 37'),
    ('tex: repeat 18 records 100%', r'18.*100'),
    # simulation
    ('tex: 66 cells / 50 seeds / 3,300 trials', r'66 cells with 50 frozen seeds each \(3[,]?300 formal trials\)'),
    ('tex: C0 150 of 150', r'150 of 150'),
    ('tex: C1 369 of 900 (41.0%)', r'369 of 900.*41\.0'),
    ('tex: 244 unordered', r'244'),
    ('tex: C2 149 of 600 (24.8%)', r'149 of 600.*24\.8'),
    ('tex: 151 unordered', r'151'),
    ('tex: 518 propagated', r'518'),
    ('tex: C4 0 of 1,500 / upper 0.26%', r'0 of 1,500.*0\.26'),
    ('tex: PILOT_SUPPORT', r'PILOT\\_SUPPORT'),
    ('tex: d_safe 0.2 m', r'0\.2'),
    ('tex: 4.0 s -> 8.0 s deviation', r'4\.0 s to 8\.0 s'),
    # ISO protocol
    ('tex: 18 pairs, 12 applicable, 6 decoys', r'18-pair.*12 applicable pairs, 6 decoys'),
    # absence checks (stale numbers must NOT appear)
    ('tex: no stale CONFIRMED framing', hasnt(r'CONFIRMED')),
    ('tex: no stale T16', hasnt(r'T16\b')),
    ('tex: no stale 4.44 headline', hasnt(r'4\.44')),
    ('tex: no stale waves 13/15/49', hasnt(r'13 topics|15 topics|49 topics')),
]

for name, pat in TEX_CHECKS:
    if name.startswith('tex:'):
        ok = pat if isinstance(pat, bool) else has(pat)
        check(name, ok)

# ---------------------------------------------------------------------------
# report
# ---------------------------------------------------------------------------
n_fail = sum(1 for _, ok, _ in results if not ok)
for name, ok, detail in results:
    print(f'[{"PASS" if ok else "FAIL"}] {name}' + (f'  -- {detail}' if (not ok and detail) else ''))
print(f'\n{len(results) - n_fail}/{len(results)} PASS, {n_fail} FAIL')
sys.exit(1 if n_fail else 0)
