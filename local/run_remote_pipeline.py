#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Run the Abaqus export script locally on a local ODB, then plot locally.

Example:
    python local/run_remote_pipeline.py ^
      --odb D:\Files\Abaqus\static\Model\test-hnt-xie.odb ^
      --step Step-1
"""

from __future__ import print_function
import argparse
import os
import subprocess
import sys


def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument('--odb', required=True, help='local ODB file path')
    p.add_argument('--step', required=True, help='Abaqus step name')
    p.add_argument('--disp-node-set', default='RP-top', help='node set or point used for displacement averaging')
    p.add_argument('--reaction-node-sets', default='RP-bottom', help='comma-separated node sets or points used for reaction summation')
    p.add_argument('--disp-u', default='AUTO', help='displacement component, e.g. U2, or AUTO')
    p.add_argument('--reaction-rf', default='AUTO', help='reaction component, e.g. RF2, or AUTO')
    p.add_argument('--frame', default='-1', help='frame index for stress cloud export')
    p.add_argument('--abaqus-exe', default='abaqus', help='Abaqus command executable')
    p.add_argument('--python-exe', default=sys.executable or 'python', help='Python executable used for plotting')
    p.add_argument('--local-data-dir', default=None, help='local directory for exported CSV files')
    p.add_argument('--local-fig-dir', default=None, help='local directory for output figures')
    p.add_argument('--plane', choices=['xy', 'xz', 'yz'], default='xy', help='projection plane for stress cloud')
    p.add_argument('--dpi', type=int, default=180, help='output figure DPI')
    return p.parse_args()


def run_checked(cmd, label):
    print('[INFO] %s' % label)
    result = subprocess.run(cmd)
    if result.returncode != 0:
        raise SystemExit(result.returncode)


def build_default_dirs(odb_path):
    job_name = os.path.splitext(os.path.basename(odb_path))[0]
    return (
        os.path.join('data', job_name),
        os.path.join('figures', job_name),
    )


def main():
    args = parse_args()

    if not os.path.isfile(args.odb):
        raise SystemExit('ODB file not found: %s' % args.odb)

    default_data_dir, default_fig_dir = build_default_dirs(args.odb)
    local_data_dir = args.local_data_dir or default_data_dir
    local_fig_dir = args.local_fig_dir or default_fig_dir

    os.makedirs(local_data_dir, exist_ok=True)
    os.makedirs(local_fig_dir, exist_ok=True)

    repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    export_script = os.path.join(repo_root, 'server', 'export_abaqus_data.py')
    plot_script = os.path.join(repo_root, 'local', 'plot_results.py')

    run_checked(
        [
            args.abaqus_exe,
            'python',
            export_script,
            '--',
            '--odb',
            args.odb,
            '--step',
            args.step,
            '--disp-node-set',
            args.disp_node_set,
            '--reaction-node-sets',
            args.reaction_node_sets,
            '--disp-u',
            args.disp_u,
            '--reaction-rf',
            args.reaction_rf,
            '--frame',
            args.frame,
            '--out-dir',
            local_data_dir,
        ],
        'exporting CSV files from local ODB',
    )

    run_checked(
        [
            args.python_exe,
            plot_script,
            '--input-dir',
            local_data_dir,
            '--out-dir',
            local_fig_dir,
            '--plane',
            args.plane,
            '--dpi',
            str(args.dpi),
        ],
        'plotting local figures',
    )

    print('[OK] local pipeline finished')
    print('[OK] odb:', os.path.abspath(args.odb))
    print('[OK] csv dir:', os.path.abspath(local_data_dir))
    print('[OK] fig dir:', os.path.abspath(local_fig_dir))


if __name__ == '__main__':
    main()
