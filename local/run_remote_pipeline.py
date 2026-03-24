#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Run the server-side Abaqus flow remotely, pull exported CSV files, then plot locally.

Example:
    python local/run_remote_pipeline.py ^
      --remote user@server ^
      --remote-repo-dir D:\abaqus2py ^
      --remote-cae D:\abaqus_runs\project.cae ^
      --remote-out-dir D:\abaqus_runs\out ^
      --job-name Job-1 ^
      --step Step-1 ^
      --disp-node-set RP-TOP ^
      --reaction-node-sets RP-BASE,HNT ^
      --local-data-dir .\data\Job-1 ^
      --local-fig-dir .\figures\Job-1
"""

from __future__ import print_function
import argparse
import os
import subprocess
import sys


def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument('--remote', required=True, help='SSH target, e.g. user@server')
    p.add_argument('--remote-repo-dir', required=True, help='repo path on remote machine')
    p.add_argument('--remote-cae', required=True, help='CAE file path on remote machine')
    p.add_argument('--remote-out-dir', required=True, help='remote output directory for inp/odb/csv')
    p.add_argument('--job-name', required=True, help='job name whose ODB will be exported to CSV')
    p.add_argument('--step', required=True, help='Abaqus step name')
    p.add_argument('--disp-node-set', required=True, help='node set or point used for displacement averaging')
    p.add_argument('--reaction-node-sets', required=True, help='comma-separated node sets or points used for reaction summation')
    p.add_argument('--disp-u', default='AUTO', help='displacement component, e.g. U2, or AUTO')
    p.add_argument('--reaction-rf', default='AUTO', help='reaction component, e.g. RF2, or AUTO')
    p.add_argument('--frame', default='-1', help='frame index for stress cloud export')
    p.add_argument('--ssh-exe', default='ssh', help='SSH executable')
    p.add_argument('--scp-exe', default='scp', help='SCP executable')
    p.add_argument('--local-data-dir', default=os.path.join('data', 'remote_job'), help='local directory for pulled CSV files')
    p.add_argument('--local-fig-dir', default=os.path.join('figures', 'remote_job'), help='local directory for output figures')
    p.add_argument('--plane', choices=['xy', 'xz', 'yz'], default='xy', help='projection plane for stress cloud')
    p.add_argument('--dpi', type=int, default=180, help='output figure DPI')
    return p.parse_args()


def quote_cmd_arg(value):
    value = str(value)
    return '"' + value.replace('"', '""') + '"'


def quote_ps_single(value):
    value = str(value)
    return "'" + value.replace("'", "''") + "'"


def run_checked(cmd, label):
    print('[INFO] %s' % label)
    result = subprocess.run(cmd)
    if result.returncode != 0:
        raise SystemExit(result.returncode)


def build_remote_command(args):
    script_path = os.path.join(args.remote_repo_dir, 'server', 'run_and_export.bat')
    values = [
        script_path,
        args.remote_cae,
        args.remote_out_dir,
        args.job_name,
        args.step,
        args.disp_node_set,
        args.reaction_node_sets,
        args.disp_u,
        args.reaction_rf,
        args.frame,
    ]
    bat_call = 'call ' + ' '.join(quote_cmd_arg(v) for v in values)
    return 'powershell -NoProfile -Command %s' % quote_ps_single('& { %s }' % bat_call)


def build_remote_csv_path(args):
    remote_csv_dir = os.path.join(args.remote_out_dir, 'csv', args.job_name)
    return remote_csv_dir.replace('\\', '/') + '/*.csv'


def main():
    args = parse_args()

    os.makedirs(args.local_data_dir, exist_ok=True)
    os.makedirs(args.local_fig_dir, exist_ok=True)

    remote_cmd = build_remote_command(args)
    run_checked([args.ssh_exe, args.remote, remote_cmd], 'running remote Abaqus flow')

    remote_csv_glob = '%s:%s' % (args.remote, build_remote_csv_path(args))
    run_checked(
        [args.scp_exe, remote_csv_glob, args.local_data_dir],
        'pulling exported CSV files to %s' % args.local_data_dir,
    )

    plot_script = os.path.join(os.path.dirname(__file__), 'plot_results.py')
    run_checked(
        [
            sys.executable,
            plot_script,
            '--input-dir',
            args.local_data_dir,
            '--out-dir',
            args.local_fig_dir,
            '--plane',
            args.plane,
            '--dpi',
            str(args.dpi),
        ],
        'plotting local figures',
    )

    print('[OK] local pipeline finished')
    print('[OK] csv dir:', os.path.abspath(args.local_data_dir))
    print('[OK] fig dir:', os.path.abspath(args.local_fig_dir))


if __name__ == '__main__':
    main()
