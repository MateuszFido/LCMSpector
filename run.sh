#!/bin/bash
module load stack/2024-06
module load python/3.11.6

slurm_script="script.slurm"

cat > "$slurm_script" <<EOF
#!/bin/bash
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=16
#SBATCH --time=4:0:0
#SBATCH --mem-per-cpu=12G
#SBATCH --tmp=32GB
#SBATCH --mail-type=FAIL,END
#SBATCH --job-name=lc-inspector.job
#SBATCH --output=jobs/lc-inspector.out
#SBATCH --error=jobs/lc-inspector.err
python3 main.py
EOF

sbatch "$slurm_script"
