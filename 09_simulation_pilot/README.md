# Topic 22 Controlled Propagation Simulation — work/

This directory is the single workspace for the preregistered controlled simulation (see `PREREGISTERED_PARAMETERS.md`, `config/preregistered.yaml`, and `AUDIT_REPORT.md`).

- `config/`: frozen preregistration configuration and its SHA-256
- `src/`: simulation and analysis source code (hashed into the manifest after freezing)
- `tests/`: pytest tests (TDD; failure and pass evidence in `logs/tests.log`)
- `outputs/`: raw trial table, event summaries, representative trajectories, statistical results, classification results
- `figures/`: five vector PDF figures (PDFs were used instead of the originally planned PNGs; the deviation is logged)
- `logs/`: every command actually executed, with exit codes and exceptions
- Top level: AUDIT_REPORT.md, claim_impact_matrix.csv, page19_result_payload.md, final_manifest.json

Recomputation: `src/analyze.py` and `src/make_figures.py` consume only the frozen CSVs under `outputs/`; the simulation itself does not need to be rerun.
