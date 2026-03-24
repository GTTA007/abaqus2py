#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Local post-processing script.

Usage:
    python plot_results.py \
        --input-dir ./data \
        --out-dir ./figures \
        --plane xy
"""

import os
import argparse

import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.tri as mtri


def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument('--input-dir', default='data', help='directory containing CSV files')
    p.add_argument('--out-dir', default='figures', help='directory for output figures')
    p.add_argument('--plane', choices=['xy', 'xz', 'yz'], default='xy', help='projection plane for stress cloud')
    p.add_argument('--dpi', type=int, default=180)
    return p.parse_args()


def plot_load_displacement(df, out_png, dpi):
    # Prefer displacement on x-axis and load on y-axis
    x_col = [c for c in df.columns if c.startswith('avg_U')]
    y_col = [c for c in df.columns if c.startswith('sum_')]
    if not x_col or not y_col:
        raise ValueError('load_displacement.csv missing avg_U*/sum_* columns')

    x = df[x_col[0]].values
    y = df[y_col[0]].values

    plt.figure(figsize=(7, 5))
    plt.plot(x, y, '-o', lw=1.4, ms=3)
    plt.xlabel(x_col[0])
    plt.ylabel(y_col[0])
    plt.title('Load-Displacement Curve')
    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.savefig(out_png, dpi=dpi)
    plt.close()


def _plane_cols(plane):
    if plane == 'xy':
        return 'x', 'y'
    if plane == 'xz':
        return 'x', 'z'
    return 'y', 'z'


def plot_stress_cloud(df, out_png, plane, dpi):
    c1, c2 = _plane_cols(plane)

    x = df[c1].values
    y = df[c2].values
    z = df['mises'].values

    triang = mtri.Triangulation(x, y)

    plt.figure(figsize=(8, 6))
    cntr = plt.tricontourf(triang, z, levels=24, cmap='turbo')
    plt.colorbar(cntr, label='Mises Stress')
    plt.xlabel(c1)
    plt.ylabel(c2)
    plt.title('Stress Cloud (%s plane)' % plane.upper())
    plt.gca().set_aspect('equal', adjustable='box')
    plt.tight_layout()
    plt.savefig(out_png, dpi=dpi)
    plt.close()


def main():
    args = parse_args()
    os.makedirs(args.out_dir, exist_ok=True)

    ld_csv = os.path.join(args.input_dir, 'load_displacement.csv')
    s_csv = os.path.join(args.input_dir, 'stress_cloud.csv')

    ld_df = pd.read_csv(ld_csv)
    s_df = pd.read_csv(s_csv)

    ld_png = os.path.join(args.out_dir, 'load_displacement.png')
    s_png = os.path.join(args.out_dir, 'stress_cloud_%s.png' % args.plane)

    plot_load_displacement(ld_df, ld_png, args.dpi)
    plot_stress_cloud(s_df, s_png, args.plane, args.dpi)

    print('[OK] saved:', ld_png)
    print('[OK] saved:', s_png)


if __name__ == '__main__':
    main()
