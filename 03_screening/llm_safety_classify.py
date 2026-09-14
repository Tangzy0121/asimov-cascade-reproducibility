# -*- coding: utf-8 -*-
# ============================================================================
# llm_safety_classify.py  |  Tier 1 (active)
# Purpose : Grade each topic 0-5 for safety relevance via a DeepSeek few-shot prompt softly gated by a 12-category keyword prior.
# Input   : output/time_analysis/ CSVs and/or data/humanoid_safety_patents.xlsx (via engine.data)
# Output  : output/time_analysis/10_cascade/llm_safety_labels.csv
# Usage   : python scripts/llm_safety_classify.py
# Asimov Cascade humanoid-safety patent pipeline
# ----------------------------------------------------------------------------
# HOW IT WORKS:
#   1. For each topic, send its keywords / representative docs to a DeepSeek few-shot prompt (12 cats).
#   2. Independently score with a keyword taxonomy (12 categories x keyword lists).
#   3. Soft-fuse the two into a 0-5 safety score + category (hybrid mode needs no API key).
#   4. Write llm_safety_labels.csv (topics scoring >= 2 enter the cascade set).
# ============================================================================

"""scripts/llm_safety_classify.py — LLM-based safety classification for BERTopic topics.

Replaces the simple keyword-matching in detect_cascade_signals.py with
LLM reasoning. Supports two backends:

  Mode A (LLM):     DeepSeek / OpenAI-compatible API  — nuanced, accurate
  Mode B (Hybrid):  Enhanced keyword matching          — zero-cost fallback

LLM mode uses few-shot in-context learning (see llm_safety_seeds.json) and
a soft hybrid gate that fuses LLM predictions with an interpretable keyword
taxonomy. The old hard keyword veto has been replaced by a score-fusion rule
that recovers false negatives while keeping false positives low.

Output: llm_safety_labels.csv (same schema as safety_topic_labels.csv)
        → consumed by detect_cascade_signals.py

Usage:
  # LLM mode (needs API key):
  set DEEPSEEK_API_KEY=sk-xxx
  python scripts/llm_safety_classify.py

  # Hybrid mode (no key needed):
  python scripts/llm_safety_classify.py --mode hybrid

Seed file format (llm_safety_seeds.json):
  A JSON list of objects, each with:
    role, topic_name, topic_keywords, representative_doc,
    safety_score (0-5), safety_category, rationale
"""

import sys, io, os, json, argparse
from pathlib import Path
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pandas as pd
import numpy as np
from pathlib import Path

PROJECT_ROOT = Path(r"<project>/PatSense\Cascade\BERT_Python")
TOPIC_SUMMARY = PROJECT_ROOT / "output" / "time_analysis" / "04_bertopic_time" / "topic_summary.csv"
OUTPUT_DIR = PROJECT_ROOT / "output" / "time_analysis" / "10_cascade"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
OUTPUT_FILE = OUTPUT_DIR / "llm_safety_labels.csv"
SEED_FILE = Path(__file__).resolve().parent / "llm_safety_seeds.json"

# Tunable thresholds for soft hybrid gate
LLM_OVERRIDE_MIN_SCORE = 4
LLM_OVERRIDE_MIN_CONFIDENCE = 0.85
LLM_OVERRIDE_CATEGORIES = {
    "collision_protection",
    "force_control",
    "impedance_compliance",
    "fail_safe_emergency",
    "injury_prevention",
}


# ============================================================================
# Enhanced Safety Keyword Taxonomy (Mode B: Hybrid fallback)
# ============================================================================
# Organized by safety mechanism TYPE, not just raw keywords.
# Each category has a base_score reflecting severity in humanoid robotics context.

SAFETY_TAXONOMY = {
    "collision_protection": {
        "score": 5,
        "keywords": [
            "collision avoidance", "collision detection", "collision prevention",
            "collision-free", "anti-collision", "obstacle avoidance",
            "collision", "collision warning",
        ]
    },
    "force_control": {
        "score": 4,
        "keywords": [
            "force control", "force sensor", "force feedback",
            "torque control", "torque limiting", "torque sensor",
            "force limiting", "force/torque", "force estimation",
            "contact force", "force impedance",
        ]
    },
    "impedance_compliance": {
        "score": 4,
        "keywords": [
            "impedance control", "impedance", "compliance control",
            "compliant", "variable stiffness", "admittance control",
            "series elastic", "spring-damper", "viscoelastic",
        ]
    },
    "fail_safe_emergency": {
        "score": 5,
        "keywords": [
            "fail-safe", "fail safe", "failsafe", "fail-operational",
            "emergency stop", "emergency braking", "emergency shutdown",
            "protective stop", "safety stop", "safe stop",
            "e-stop", "deadman", "dead man",
        ]
    },
    "safety_monitoring": {
        "score": 3,
        "keywords": [
            "safety monitoring", "safety monitor", "safety assessment",
            "safety check", "safety verification", "safety validation",
            "safety inspection", "safety detection", "safety warning",
            "risk monitoring", "hazard monitoring",
        ]
    },
    "risk_assessment": {
        "score": 3,
        "keywords": [
            "risk assessment", "risk analysis", "risk evaluation",
            "risk management", "risk mitigation", "hazard analysis",
            "safety analysis", "fault tree", "fmea",
            "risk field", "risk prediction", "safety risk",
        ]
    },
    "injury_prevention": {
        "score": 5,
        "keywords": [
            "injury prevention", "injury", "harm prevention",
            "human injury", "operator safety", "human safety",
            "personal safety", "worker safety", "user safety",
            "human-robot safety", "safe human-robot",
        ]
    },
    "fault_detection": {
        "score": 4,
        "keywords": [
            "fault detection", "fault diagnosis", "fault tolerant",
            "fault tolerance", "anomaly detection", "error detection",
            "failure detection", "failure mode", "fault isolation",
            "self-diagnosis", "diagnosis", "diagnostic",
        ]
    },
    "safe_control": {
        "score": 4,
        "keywords": [
            "safe control", "safety control", "safety-critical",
            "safety guarantee", "safety constraint", "safety barrier",
            "barrier function", "control barrier", "safety filter",
            "safe reinforcement learning", "safe RL",
            "safety layer", "safety policy",
        ]
    },
    "stability_balance": {
        "score": 2,  # lower: stability is about performance more than safety
        "keywords": [
            "stability", "balance control", "fall prevention",
            "fall detection", "fall recovery", "postural stability",
            "zero moment point", "zmp", "capture point",
            "balance", "push recovery", "stabilization",
        ]
    },
    "thermal_management": {
        "score": 2,
        "keywords": [
            "thermal", "overheating", "heat dissipation",
            "temperature control", "thermal management",
            "cooling", "overheat protection", "thermal protection",
        ]
    },
    "electrical_safety": {
        "score": 3,
        "keywords": [
            "overcurrent", "overvoltage", "short circuit",
            "electrical safety", "insulation", "ground fault",
            "power safety", "battery safety", "overload protection",
        ]
    },
}

# Flatten to keyword → weight mapping for fast lookup
_KEYWORD_WEIGHTS = {}
for cat_name, cat_info in SAFETY_TAXONOMY.items():
    for kw in cat_info["keywords"]:
        _KEYWORD_WEIGHTS[kw.lower()] = cat_info["score"]


def enhanced_keyword_score(topic_name, topic_keywords, representative_doc=""):
    """Multi-dimensional safety scoring using the taxonomy.

    Instead of a single score, returns a dict with:
      - safety_score: 0-5 overall
      - safety_category: primary category or "not_safety"
      - category_scores: per-category breakdown
      - rationale: which keywords matched
    """
    text = (topic_name + " " + topic_keywords + " " + representative_doc[:2000]).lower()

    category_hits = {}
    matched_keywords = []
    for cat_name, cat_info in SAFETY_TAXONOMY.items():
        hits = []
        for kw in cat_info["keywords"]:
            if kw.lower() in text:
                hits.append(kw)
        if hits:
            category_hits[cat_name] = {
                "base_score": cat_info["score"],
                "match_count": len(hits),
                "keywords": hits,
            }
            matched_keywords.extend(hits)

    if not category_hits:
        return {
            "safety_score": 0,
            "safety_category": "not_safety",
            "category_scores": {},
            "matched_keywords": [],
            "rationale": "No safety keywords matched",
        }

    # Primary category = highest base_score × log(1 + matches)
    best_cat = max(category_hits, key=lambda c:
        category_hits[c]["base_score"] * np.log1p(category_hits[c]["match_count"]))

    # Overall score: weighted average of top categories, capped at 5
    scores = []
    for cat, info in category_hits.items():
        scores.append(info["base_score"] * min(info["match_count"], 3) / 3)
    overall = min(5, round(sum(sorted(scores, reverse=True)[:3]) / min(3, len(scores))))

    rationale = f"Matched: {', '.join(matched_keywords[:8])}"

    return {
        "safety_score": overall,
        "safety_category": best_cat,
        "category_scores": {c: h["base_score"] for c, h in category_hits.items()},
        "matched_keywords": matched_keywords,
        "rationale": rationale,
    }


# ============================================================================
# Few-shot seed loading
# ============================================================================

def load_seeds(seed_path: Path = SEED_FILE) -> list:
    """Load curated few-shot examples for LLM safety classification."""
    if not seed_path.exists():
        return []
    with open(seed_path, "r", encoding="utf-8") as f:
        return json.load(f)


def build_few_shot_messages(seeds: list) -> list:
    """Convert seed examples into alternating user/assistant messages."""
    messages = []
    for seed in seeds:
        user_text = f"""Topic Name: {seed['topic_name']}
Top Keywords: {seed['topic_keywords']}
Representative Patent Abstracts:
{seed['representative_doc']}

Classify this topic's safety relevance for humanoid robotics."""
        assistant_text = json.dumps({
            "safety_score": seed["safety_score"],
            "safety_category": seed["safety_category"],
            "confidence": 0.95,
            "rationale": seed["rationale"],
        }, ensure_ascii=False)
        messages.append({"role": "user", "content": user_text})
        messages.append({"role": "assistant", "content": assistant_text})
    return messages


# ============================================================================
# Soft hybrid gate: fuse LLM and keyword signals
# ============================================================================

def fuse_scores(llm_result, keyword_result):
    """Combine LLM prediction with keyword taxonomy using interpretable rules.

    Rules (in order):
      1. LLM failure -> fall back to keyword.
      2. Both signals agree on safety (>=2) -> trust LLM category, rounded average.
      3. LLM confident override (score>=LLM_OVERRIDE_MIN_SCORE,
         confidence>=LLM_OVERRIDE_MIN_CONFIDENCE, category in core set)
         while keyword sees no safety -> accept LLM (recovers false negatives).
      4. Keyword positive and LLM low -> use keyword.
      5. Both low -> keep higher score, but reject weak LLM claims when keyword=0.
    """
    llm_score = int(llm_result.get("safety_score", 0))
    llm_cat = llm_result.get("safety_category", "not_safety")
    llm_conf = float(llm_result.get("llm_confidence", 0.5))
    kw_score = int(keyword_result.get("safety_score", 0))
    kw_cat = keyword_result.get("safety_category", "not_safety")

    # Valid safety category must be in taxonomy or not_safety
    valid_cats = set(SAFETY_TAXONOMY.keys()) | {"not_safety"}
    llm_cat = llm_cat if llm_cat in valid_cats else "not_safety"

    # Rule 1: LLM failure already handled by caller; still guard here.
    if llm_result is None:
        return keyword_result.copy(), "keyword_fallback"

    # Rule 2: both agree on safety -> rounded average to avoid LLM over-scoring
    if llm_score >= 2 and kw_score >= 2:
        fused_score = int(round((llm_score + kw_score) / 2))
        fused = {
            "safety_score": min(5, fused_score),
            "safety_category": llm_cat,
            "rationale": f"[agreement] LLM({llm_score}) + keyword({kw_score}): {llm_result['rationale']}",
        }
        return fused, "agreement"

    # Rule 3: LLM confident override when keyword is blind (core categories only)
    if (kw_score == 0 and llm_score >= LLM_OVERRIDE_MIN_SCORE
            and llm_conf >= LLM_OVERRIDE_MIN_CONFIDENCE
            and llm_cat in LLM_OVERRIDE_CATEGORIES):
        fused = {
            "safety_score": llm_score,
            "safety_category": llm_cat,
            "rationale": f"[llm_override conf={llm_conf:.2f}] {llm_result['rationale']}",
        }
        return fused, "llm_override"

    # Rule 4: keyword positive, LLM low -> trust keyword
    if kw_score >= 2 and llm_score < 2:
        fused = {
            "safety_score": kw_score,
            "safety_category": kw_cat,
            "rationale": f"[keyword_fallback] {keyword_result['rationale']}",
        }
        return fused, "keyword_fallback"

    # Rule 5: both low. Reject weak LLM claims when keyword taxonomy is blind.
    if kw_score == 0 and llm_score < LLM_OVERRIDE_MIN_SCORE:
        fused = {
            "safety_score": 0,
            "safety_category": "not_safety",
            "rationale": f"[filtered] LLM({llm_score}, conf={llm_conf:.2f}) without keyword support; treated as not_safety.",
        }
        return fused, "filtered"

    if llm_score >= kw_score:
        fused = {
            "safety_score": llm_score,
            "safety_category": llm_cat,
            "rationale": f"[llm_low] {llm_result['rationale']}",
        }
    else:
        fused = {
            "safety_score": kw_score,
            "safety_category": kw_cat,
            "rationale": f"[keyword_low] {keyword_result['rationale']}",
        }
    return fused, "low_max"


# ============================================================================
# LLM-based classification (Mode A)
# ============================================================================

def llm_classify_topic(topic_name, topic_keywords, representative_doc, client, model, seeds=None):
    """Classify a single topic using DeepSeek/OpenAI API with optional few-shot examples."""

    # Truncate representative docs to avoid token limit
    doc_excerpt = representative_doc[:2500] if representative_doc else ""

    system_prompt = """You are a robotics safety expert classifying patent topics for the
"Asimov Cascade Detection" framework. Your task: determine if a patent topic relates to
HUMANOID ROBOT SAFETY MECHANISMS.

Base your decision PRIMARILY on the representative patent abstracts provided,
NOT just the topic name or keywords. Be conservative.

Safety mechanisms include: collision avoidance/detection, force/torque control,
impedance/compliance control, fail-safe design, emergency stop, fault detection/diagnosis,
risk assessment, injury prevention, safe human-robot interaction, stability/fall prevention.

IMPORTANT DISTINCTIONS — these are NOT safety mechanisms unless the abstracts
EXPLICITLY describe a human-protection or hazard-prevention purpose:
- Mechanical structural parts (frames, links, brackets, abutments, skins, shells,
  housings, rods, pulleys, ropes, fingers, legs) that merely describe hardware shape
- Generic actuators, motors, batteries, sensors, cameras without safety-specific function
- Aesthetic, entertainment, or manufacturing-efficiency features
- Generic control/planning algorithms not motivated by safety

Scoring rules:
- 5 = core safety mechanism explicitly protecting humans in humanoid robots
- 4 = clear safety-related mechanism
- 3 = safety-relevant but peripheral
- 2 = weak/indirect safety connection
- 1 = topic is robotics-related but not primarily safety
- 0 = not safety-related (mechanical/hardware/AI/generic)

Respond in JSON format only:
{
  "safety_score": <0-5>,
  "safety_category": "<one of: collision_protection, force_control, impedance_compliance, fail_safe_emergency, safety_monitoring, risk_assessment, injury_prevention, fault_detection, safe_control, stability_balance, not_safety>",
  "confidence": <0.0-1.0, your certainty that this label is correct>,
  "rationale": "<one sentence citing evidence from the abstracts>"
}"""

    user_prompt = f"""Topic Name: {topic_name}
Top Keywords: {topic_keywords[:400]}
Representative Patent Abstracts (read all before deciding):
{doc_excerpt}

Instructions:
1. Read the representative abstracts carefully.
2. Decide if the topic is primarily about a humanoid robot SAFETY MECHANISM.
3. Score 0-2 if it is mechanical/hardware/structural without explicit safety purpose.
4. Score 4-5 only if the abstracts explicitly describe protecting humans or preventing hazardous contact.
5. Respond in JSON format with safety_score, safety_category, confidence, and rationale."""

    messages = [{"role": "system", "content": system_prompt}]
    if seeds:
        messages.extend(build_few_shot_messages(seeds))
    messages.append({"role": "user", "content": user_prompt})

    try:
        response = client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=0.1,
            max_tokens=350,
            response_format={"type": "json_object"},
        )
        result = json.loads(response.choices[0].message.content)
        return {
            "safety_score": int(result.get("safety_score", 0)),
            "safety_category": result.get("safety_category", "not_safety"),
            "llm_confidence": float(result.get("confidence", 0.5)),
            "category_scores": {},
            "matched_keywords": [],
            "rationale": result.get("rationale", "LLM classified"),
            "llm_model": model,
        }
    except Exception as e:
        print(f"  LLM error for topic '{topic_name[:60]}...': {e}")
        return None


def classify_all_topics(mode="hybrid", api_key=None, model="deepseek-chat", seeds=None,
                        legacy_hard_gate=False):
    """Classify all BERTopic topics for safety relevance.

    Args:
        mode: "llm" or "hybrid"
        api_key: DeepSeek API key (required for LLM mode)
        model: model name for LLM mode
        seeds: optional list of few-shot examples; loaded from file if None
        legacy_hard_gate: if True, force score=0 whenever keyword taxonomy sees no
            safety signal (reproduces the original hard-gate behaviour for validation).
    """
    print(f"=== LLM Safety Classification (mode={mode}, hard_gate={legacy_hard_gate}) ===\n")

    # Load few-shot seeds for LLM mode
    if seeds is None and mode == "llm":
        seeds = load_seeds()
        print(f"Loaded {len(seeds)} few-shot seeds\n")

    # Load BERTopic topic summary
    df = pd.read_csv(TOPIC_SUMMARY)
    # Filter noise topic
    df_clean = df[df["Topic"] != -1].copy()
    n_topics = len(df_clean)
    print(f"Loaded {n_topics} topics (excluding noise)\n")

    # Set up LLM client if needed
    client = None
    if mode == "llm":
        if not api_key:
            api_key = os.environ.get("DEEPSEEK_API_KEY")
        if not api_key:
            print("No API key found. Falling back to hybrid mode.")
            mode = "hybrid"
        else:
            from openai import OpenAI
            client = OpenAI(
                api_key=api_key,
                base_url="https://api.deepseek.com",
            )
            print(f"LLM mode: {model}\n")

    results = []
    for idx, row in df_clean.iterrows():
        topic_id = row["Topic"]
        topic_name = str(row["Name"])
        topic_kw = str(row["Representation"])
        # Combine first 3 representative docs for richer context
        rep_docs = str(row.get("Representative_Docs", ""))
        docs = [d.strip("[]'\"") for d in rep_docs.split("', '") if d.strip("[]'\"")]
        combined_doc = "\n\n---\n\n".join(docs[:3]) if docs else ""

        # Always compute keyword score (used as sanity check in LLM mode)
        keyword_result = enhanced_keyword_score(topic_name, topic_kw, combined_doc)

        if mode == "llm" and client:
            llm_result = llm_classify_topic(topic_name, topic_kw, combined_doc, client, model, seeds=seeds)
            if llm_result is None:
                # Fallback to keyword on error
                result = keyword_result.copy()
                result["llm_failed"] = True
                result["llm_score"] = 0
                result["llm_category"] = "not_safety"
                result["llm_confidence"] = 0.0
                result["fusion_rule"] = "keyword_fallback"
            elif legacy_hard_gate and keyword_result["safety_score"] == 0:
                # Original hard gate: keyword blind -> force not_safety
                result = {
                    "safety_score": 0,
                    "safety_category": "not_safety",
                    "rationale": f"[legacy hard gate] {llm_result['rationale']} (keyword score=0)",
                    "llm_score": llm_result["safety_score"],
                    "llm_category": llm_result["safety_category"],
                    "llm_confidence": llm_result["llm_confidence"],
                    "keyword_score": keyword_result["safety_score"],
                    "keyword_category": keyword_result["safety_category"],
                    "keyword_matched": ", ".join(keyword_result.get("matched_keywords", [])),
                    "fusion_rule": "legacy_hard_gate",
                    "llm_model": model,
                }
            else:
                fused, rule = fuse_scores(llm_result, keyword_result)
                result = {
                    "safety_score": fused["safety_score"],
                    "safety_category": fused["safety_category"],
                    "rationale": fused["rationale"],
                    "llm_score": llm_result["safety_score"],
                    "llm_category": llm_result["safety_category"],
                    "llm_confidence": llm_result["llm_confidence"],
                    "keyword_score": keyword_result["safety_score"],
                    "keyword_category": keyword_result["safety_category"],
                    "keyword_matched": ", ".join(keyword_result.get("matched_keywords", [])),
                    "fusion_rule": rule,
                    "llm_model": model,
                }
        else:
            result = keyword_result.copy()
            result["llm_score"] = 0
            result["llm_category"] = "not_safety"
            result["llm_confidence"] = 0.0
            result["keyword_score"] = keyword_result["safety_score"]
            result["keyword_category"] = keyword_result["safety_category"]
            result["keyword_matched"] = ", ".join(keyword_result.get("matched_keywords", []))
            result["fusion_rule"] = "keyword_only"

        result["bertopic_id"] = topic_id
        result["bertopic_name"] = topic_name
        result["bertopic_count"] = int(row["Count"])
        results.append(result)

        print(f"  [{topic_id:3d}] score={result['safety_score']} "
              f"cat={result['safety_category']:25s} "
              f"name={topic_name[:60]}")

    # Build output DataFrame
    out_df = pd.DataFrame(results)
    base_cols = ["bertopic_id", "bertopic_name", "bertopic_count",
                 "safety_score", "safety_category", "rationale"]
    extra_cols = ["llm_score", "llm_category", "llm_confidence",
                  "keyword_score", "keyword_category", "keyword_matched", "fusion_rule"]
    # Preserve any other columns (e.g., llm_model) without breaking schema
    ordered_cols = base_cols + [c for c in extra_cols if c in out_df.columns]
    ordered_cols += [c for c in out_df.columns if c not in ordered_cols]
    out_df = out_df[ordered_cols]
    out_df.to_csv(OUTPUT_FILE, index=False, encoding='utf-8-sig')

    # Summary stats
    safety_topics = out_df[out_df["safety_score"] >= 2]
    cascade_candidates = out_df[out_df["safety_score"] >= 3]

    print(f"\n=== Summary ===")
    print(f"Total topics: {n_topics}")
    print(f"Safety-related (score>=2): {len(safety_topics)} ({100*len(safety_topics)/n_topics:.0f}%)")
    print(f"Cascade candidates (score>=3): {len(cascade_candidates)} ({100*len(cascade_candidates)/n_topics:.0f}%)")
    print(f"\nCategory distribution:")
    for cat in sorted(out_df["safety_category"].value_counts().index):
        count = out_df["safety_category"].value_counts()[cat]
        print(f"  {cat}: {count}")
    print(f"\nSaved: {OUTPUT_FILE}")

    return out_df


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=["llm", "hybrid"], default="hybrid",
                       help="Classification mode (default: hybrid)")
    parser.add_argument("--api-key", help="DeepSeek API key (or set DEEPSEEK_API_KEY env)")
    parser.add_argument("--model", default="deepseek-chat", help="LLM model name")
    args = parser.parse_args()

    classify_all_topics(mode=args.mode, api_key=args.api_key, model=args.model)
