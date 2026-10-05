#!/bin/bash
#SBATCH --job-name=phmb-natality
#SBATCH --account=[VERIFY account]
#SBATCH --partition=[VERIFY partition]
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=4
#SBATCH --mem=32G
#SBATCH --time=02:00:00
#SBATCH --output=phmb-natality-%j.log
# Login nodes usually have internet; compute nodes often do not.
# Run `python code/01_fetch.py` on a login node first, then submit this job.
module load python   # [VERIFY] module name on Alpine / Anvil
cd "$SLURM_SUBMIT_DIR"
python code/02_parse.py
python code/03_audit.py
python code/04_tasks.py
