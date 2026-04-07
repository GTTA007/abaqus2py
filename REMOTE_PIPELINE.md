# Remote Pipeline

This repo now includes a one-command local/server workflow.

## Files

- `server/run_and_export.bat`
  Runs the full server-side pipeline for one selected job:
  `cae -> inp -> odb -> csv`

- `local/run_remote_pipeline.py`
  Runs the remote batch over SSH, pulls CSV files back with SCP, then calls the existing local plotting script.

## Example

```bash
py -3 local/run_remote_pipeline.py \
  --remote user@server \
  --remote-repo-dir D:\abaqus2py \
  --remote-cae D:\abaqus_runs\project.cae \
  --remote-out-dir D:\abaqus_runs\out \
  --job-name Job-1 \
  --step Step-1 \
  --disp-node-set RP-top \
  --reaction-node-sets RP-bottom \
  --disp-u U2 \
  --reaction-rf RF2 \
  --frame -1 \
  --local-data-dir .\data\Job-1 \
  --local-fig-dir .\figures\Job-1 \
  --plane xy
```

## Requirements

- Local machine:
  - OpenSSH `ssh` and `scp` available in `PATH`
  - Python installed
  - plotting dependencies installed for `local/plot_results.py`

- Remote machine:
  - Windows host reachable over SSH
  - this repo present at `--remote-repo-dir`
  - `abaqus` command available in the SSH session

## Notes

- `--job-name` is required because a `.cae` may contain multiple jobs. The remote flow will run all jobs, then export CSV only from the selected job's `.odb`.
- Remote CSV files are expected under:
  `REMOTE_OUT_DIR\csv\JOB_NAME`
