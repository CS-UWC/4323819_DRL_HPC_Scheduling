# =============================================================================
# justfile — DRLScheduler Pipeline Commands
# =============================================================================
# Usage: just <target> [trace]
# The trace arg accepts the short form (physical | deeplearn) or the full
# trace_name (physical_job | deeplearn_job); both normalise to <name>_job.
# Defaults to physical when omitted.
# Example: just run_full_slurm deeplearn
# Example: just run_smoke physical
# Ref: https://just.systems/man/en/
# =============================================================================

# Auto-detect CPU count (varies by OS)
cpu_count := if os() == "linux" {
    `nproc`
} else if os() == "macos" {
    `sysctl -n hw.ncpu`
} else {
    "4"
}

# Where `archive_results` copies analysis outputs + all algorithms' final models
# off scratch into safe (home) storage. Override: ARCHIVE=/path just archive_results deeplearn
ARCHIVE := env_var_or_default("ARCHIVE", env_var("HOME") + "/drl_archive")

# =============================================================================
# HELP
# =============================================================================

@help:
    echo "DRLScheduler Snakemake Pipeline — justfile Targets"
    echo ""
    echo "Most targets take a trace argument: physical (default) | deeplearn"
    echo ""
    echo "PIPELINE TARGETS:"
    echo "  dry_run_smoke [trace]   - Validate smoke DAG without execution"
    echo "  dry_run [trace]         - Validate production DAG without execution"
    echo "  run_smoke [trace]       - Smoke test (fast end-to-end validation)"
    echo "  run_full [trace]        - Full pipeline (train → eval → aggregate → stats → baseline → holdout)"
    echo "  run_baseline [trace]    - Run baseline scheduler only"
    echo ""
    echo "DAG EXPORT TARGETS:"
    echo "  export_dag [trace]          - Export both detail + overview DAGs"
    echo "  export_dag_detail [trace]   - Export job-level DAG (detailed)"
    echo "  export_dag_overview [trace] - Export rule-level DAG (clean)"
    echo ""
    echo "SLURM TARGETS:"
    echo "  dry_run_smoke_slurm [trace] - Validate smoke DAG for cluster"
    echo "  dry_run_slurm [trace]       - Validate production DAG for cluster"
    echo "  run_smoke_slurm [trace]     - Submit smoke test to SLURM"
    echo "  run_full_slurm [trace]      - Submit full pipeline to SLURM"
    echo "  setup_scratch               - Redirect outputs to /scratch/\$USER (run once per clone)"
    echo "  archive_results [trace]     - Copy results + ALL final models off scratch to \$HOME/drl_archive"
    echo "  slurm_report                - Generate efficiency report after run"
    echo "  build_sif                   - Build Apptainer .sif from Nix flake"
    echo ""
    echo "MAINTENANCE:"
    echo "  clean                - Remove all outputs except data and logs"
    echo "  clean_all            - Remove all outputs including logs"
    echo "  nix_develop          - Enter Nix shell"
    echo ""
    echo "EXAMPLES:"
    echo "  just run_smoke                     # Quick smoke test on physical"
    echo "  just run_full deeplearn            # Full run on deeplearn"
    echo "  just run_full_slurm deeplearn      # Full SLURM run on deeplearn"
    echo "  just export_dag physical           # Export DAGs before running"
    echo ""

# =============================================================================
# VALIDATION TARGETS
# =============================================================================

dry_run_smoke trace="physical":
    #!/usr/bin/env bash
    set -euo pipefail
    t="{{trace}}"; t="${t%_job}_job"
    echo "Validating smoke DAG (no execution) on ${t}..."
    snakemake --configfile config.smoke.yaml --config trace_name="${t}" --dry-run --quiet

dry_run trace="physical":
    #!/usr/bin/env bash
    set -euo pipefail
    t="{{trace}}"; t="${t%_job}_job"
    echo "Validating production DAG (no execution) on ${t}..."
    snakemake --configfile config.yaml --config trace_name="${t}" --dry-run --quiet

# =============================================================================
# PIPELINE TARGETS
# =============================================================================

run_smoke trace="physical":
    #!/usr/bin/env bash
    set -euo pipefail
    t="{{trace}}"; t="${t%_job}_job"
    echo "Running smoke test pipeline on ${t}..."
    echo "Config: config.smoke.yaml (2 seeds, 200 timesteps, max-steps=5)"
    snakemake --configfile config.smoke.yaml --config trace_name="${t}" --cores {{cpu_count}}
    echo "✓ Smoke test complete. Outputs in result/${t}/"

run_full trace="physical":
    #!/usr/bin/env bash
    set -euo pipefail
    t="{{trace}}"; t="${t%_job}_job"
    echo "Running full production pipeline on ${t}..."
    echo "Config: config.yaml (10 seeds, 3M timesteps)"
    snakemake --configfile config.yaml --config trace_name="${t}" --cores {{cpu_count}}
    echo "✓ Full pipeline complete. Outputs in result/${t}/"

run_baseline trace="physical":
    #!/usr/bin/env bash
    set -euo pipefail
    t="{{trace}}"; t="${t%_job}_job"
    echo "Running configured baseline schedulers on ${t}..."
    snakemake --configfile config.yaml --config trace_name="${t}" --cores {{cpu_count}} result/"${t}"/baseline/.heuristics_complete
    echo "✓ Baseline complete. Outputs in result/${t}/baseline/"

# =============================================================================
# SLURM CLUSTER TARGETS
# =============================================================================

dry_run_smoke_slurm trace="physical":
    #!/usr/bin/env bash
    set -euo pipefail
    t="{{trace}}"; t="${t%_job}_job"
    echo "Validating smoke DAG for cluster (no execution) on ${t}..."
    snakemake --configfile config.smoke.yaml --config trace_name="${t}" --profile profiles/slurm --dry-run --quiet

dry_run_slurm trace="physical":
    #!/usr/bin/env bash
    set -euo pipefail
    t="{{trace}}"; t="${t%_job}_job"
    echo "Validating production DAG for cluster (no execution) on ${t}..."
    snakemake --configfile config.yaml --config trace_name="${t}" --profile profiles/slurm --dry-run --quiet

run_smoke_slurm trace="physical":
    #!/usr/bin/env bash
    set -euo pipefail
    t="{{trace}}"; t="${t%_job}_job"
    echo "Submitting smoke test to SLURM on ${t}..."
    snakemake --configfile config.smoke.yaml --config trace_name="${t}" --profile profiles/slurm
    echo "✓ Smoke jobs submitted. Check squeue for status."

run_full_slurm trace="physical":
    #!/usr/bin/env bash
    set -euo pipefail
    t="{{trace}}"; t="${t%_job}_job"
    echo "Submitting full pipeline to SLURM on ${t}..."
    snakemake --configfile config.yaml --config trace_name="${t}" --profile profiles/slurm
    echo "✓ Full pipeline submitted. Check squeue for status."

# One-time per clone (re-run after clean_all, which removes the dirs): redirect
# the bulky output trees to /scratch so runs write there, not $HOME. Idempotent.
# See wiki/HPC-SLURM-Workflow.md. Final models are copied back with archive_results.
setup_scratch:
    ./src/setup_scratch.sh

# Copy analysis outputs and ALL algorithms' final models off scratch into safe
# home storage. Run ONCE at the end, after select_best decides the winner.
archive_results trace="physical":
    #!/usr/bin/env bash
    set -euo pipefail
    t="{{trace}}"; t="${t%_job}_job"
    ./src/archive_results.sh "${t}" "{{ARCHIVE}}"

@slurm_report:
    echo "Generating SLURM efficiency report..."
    snakemake --configfile config.yaml --profile profiles/slurm --slurm-efficiency-report

@build_sif:
    echo "Building Apptainer .sif from Nix flake..."
    # 1. Build the container script using Nix
    nix build -L .#container -o nix-container-result 2>&1 | tee build.log

    # 2. Execute the script to stream the Docker archive to a tar file
    ./nix-container-result > DRL_env_docker.tar

    # 3. Build the Apptainer .sif directly from the Docker tarball
    apptainer build DRL_env.sif docker-archive://DRL_env_docker.tar

    # 4. Clean up the large temporary files
    rm -f DRL_env_docker.tar nix-container-result
    echo "✓ DRL_env.sif ready"

# =============================================================================
# DAG EXPORT TARGETS
# =============================================================================

export_dag_detail trace="physical":
    #!/usr/bin/env bash
    set -euo pipefail
    t="{{trace}}"; t="${t%_job}_job"
    echo "Exporting job-level DAG for ${t}..."
    mkdir -p plots
    snakemake --configfile config.yaml --config trace_name="${t}" --dag \
        | dot -Tsvg -Grankdir=LR -Gsplines=polyline -Nshape=box -Nstyle=rounded -Efontsize=10 \
        -o plots/"${t}"_dag_detail.svg
    echo "✓ Job DAG exported to plots/${t}_dag_detail.svg"

export_dag_overview trace="physical":
    #!/usr/bin/env bash
    set -euo pipefail
    t="{{trace}}"; t="${t%_job}_job"
    echo "Exporting rule-level DAG for ${t}..."
    mkdir -p plots
    snakemake --configfile config.yaml --config trace_name="${t}" --rulegraph \
        | dot -Tsvg -Grankdir=LR -Gsplines=polyline -Nshape=box -Nstyle=rounded -Efontsize=10 \
        -o plots/"${t}"_dag_overview.svg
    echo "✓ Rule DAG exported to plots/${t}_dag_overview.svg"

export_dag trace="physical":
    #!/usr/bin/env bash
    set -euo pipefail
    just export_dag_detail "{{trace}}"
    just export_dag_overview "{{trace}}"
    echo "✓ Both DAGs exported to plots/"

# =============================================================================
# MAINTENANCE TARGETS
# =============================================================================

@clean:
    echo "Cleaning pipeline outputs (data, code, and logs preserved)..."
    rm -rf result/ trained_model/ .snakemake/
    echo "✓ Clean complete"

@clean_all:
    echo "Cleaning all outputs including logs..."
    rm -rf result/ trained_model/ .snakemake/ logs/run_log.csv logs/baseline_run_log.csv logs/snakemake/
    echo "✓ Full clean complete"

@nix_develop:
    echo "Entering Nix develop environment..."
    nix develop -L

# =============================================================================
# NOTES
# =============================================================================
# Environment:      Nix (nix develop required before running)
# Snakemake:        9.4.3+
# just:             https://just.systems/man/en/
# TODO (future): Add Conda support as alternative to Nix
# =============================================================================
