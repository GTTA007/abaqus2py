# -*- coding: utf-8 -*-
"""
Server-side exporter for Abaqus 2021.
Run with:
    abaqus python export_abaqus_data.py -- \
        --odb job.odb \
        --step Step-1 \
        --node-set NSET_LOAD \
        --disp-u U2 \
        --reaction-rf RF2 \
        --frame -1 \
        --out-dir ./export
"""

from __future__ import print_function
import os
import sys
import csv

from odbAccess import openOdb
from abaqusConstants import INTEGRATION_POINT


def parse_args(argv):
    args = {
        'odb': None,
        'step': None,
        'node_set': None,
        'disp_u': 'U2',
        'reaction_rf': 'RF2',
        'frame': '-1',
        'out_dir': 'export',
    }

    i = 0
    while i < len(argv):
        key = argv[i]
        if key in ('--odb', '--step', '--node-set', '--disp-u', '--reaction-rf', '--frame', '--out-dir'):
            if i + 1 >= len(argv):
                raise ValueError('Missing value for %s' % key)
            value = argv[i + 1]
            if key == '--odb':
                args['odb'] = value
            elif key == '--step':
                args['step'] = value
            elif key == '--node-set':
                args['node_set'] = value
            elif key == '--disp-u':
                args['disp_u'] = value
            elif key == '--reaction-rf':
                args['reaction_rf'] = value
            elif key == '--frame':
                args['frame'] = value
            elif key == '--out-dir':
                args['out_dir'] = value
            i += 2
        else:
            raise ValueError('Unknown argument: %s' % key)

    if not args['odb']:
        raise ValueError('--odb is required')
    if not args['step']:
        raise ValueError('--step is required')
    if not args['node_set']:
        raise ValueError('--node-set is required')

    return args


def _node_set_from_root_assembly(odb, node_set_name):
    key = node_set_name.upper()
    if key not in odb.rootAssembly.nodeSets:
        raise KeyError('Node set not found in rootAssembly: %s' % node_set_name)
    return odb.rootAssembly.nodeSets[key]


def _history_value(history_region, output_name):
    # output_name example: U2, RF2
    if output_name not in history_region.historyOutputs:
        return None
    data = history_region.historyOutputs[output_name].data
    if not data:
        return None
    return data[-1][1]


def export_load_displacement(odb, step_name, node_set_name, disp_u, reaction_rf, out_csv):
    step = odb.steps[step_name]
    node_set = _node_set_from_root_assembly(odb, node_set_name)

    # Gather node labels in the set for quick filtering
    allowed_nodes = set()
    for ns in node_set.nodes:
        for n in ns:
            allowed_nodes.add(n.label)

    with open(out_csv, 'w') as f:
        writer = csv.writer(f)
        writer.writerow(['frame_id', 'step_time', 'sum_%s' % reaction_rf, 'avg_%s' % disp_u])

        for frame_id, frame in enumerate(step.frames):
            total_rf = 0.0
            disp_values = []

            for region_name, region in step.historyRegions.items():
                # Typical key: 'Node PART-1-1.123'
                if not region_name.startswith('Node '):
                    continue
                try:
                    node_label = int(region_name.split('.')[-1])
                except Exception:
                    continue
                if node_label not in allowed_nodes:
                    continue

                rf_val = _history_value(region, reaction_rf)
                u_val = _history_value(region, disp_u)
                if rf_val is not None:
                    total_rf += rf_val
                if u_val is not None:
                    disp_values.append(u_val)

            avg_u = sum(disp_values) / float(len(disp_values)) if disp_values else 0.0
            writer.writerow([frame_id, frame.frameValue, total_rf, avg_u])

    print('[OK] load-displacement data -> %s' % out_csv)


def _build_element_centroids(instance):
    node_coord = {}
    for n in instance.nodes:
        node_coord[n.label] = n.coordinates

    centroids = {}
    for elem in instance.elements:
        conn = elem.connectivity
        n = len(conn)
        cx = cy = cz = 0.0
        for nid in conn:
            c = node_coord[nid]
            cx += c[0]
            cy += c[1]
            cz += c[2]
        centroids[elem.label] = (cx / n, cy / n, cz / n)
    return centroids


def export_stress_cloud(odb, step_name, frame_idx, out_csv):
    step = odb.steps[step_name]
    frames = step.frames
    if frame_idx < 0:
        frame_idx = len(frames) + frame_idx
    if frame_idx < 0 or frame_idx >= len(frames):
        raise IndexError('frame index out of range: %s' % frame_idx)

    frame = frames[frame_idx]
    if 'S' not in frame.fieldOutputs:
        raise KeyError('No stress field output "S" in selected frame')

    s_field = frame.fieldOutputs['S']
    s_ip = s_field.getSubset(position=INTEGRATION_POINT)

    # Cache centroids per instance
    centroid_cache = {}

    with open(out_csv, 'w') as f:
        writer = csv.writer(f)
        writer.writerow(['instance', 'element_label', 'x', 'y', 'z', 'mises'])

        for v in s_ip.values:
            inst_name = v.instance.name
            elem_label = v.elementLabel
            if inst_name not in centroid_cache:
                centroid_cache[inst_name] = _build_element_centroids(odb.rootAssembly.instances[inst_name])

            c = centroid_cache[inst_name].get(elem_label)
            if c is None:
                continue
            writer.writerow([inst_name, elem_label, c[0], c[1], c[2], v.mises])

    print('[OK] stress cloud data -> %s (frame=%d)' % (out_csv, frame_idx))


def main():
    argv = sys.argv[1:]
    if '--' in argv:
        argv = argv[argv.index('--') + 1:]

    args = parse_args(argv)

    odb_path = args['odb']
    step_name = args['step']
    node_set_name = args['node_set']
    disp_u = args['disp_u']
    reaction_rf = args['reaction_rf']
    frame_idx = int(args['frame'])
    out_dir = args['out_dir']

    if not os.path.isdir(out_dir):
        os.makedirs(out_dir)

    odb = openOdb(path=odb_path, readOnly=True)
    try:
        ld_csv = os.path.join(out_dir, 'load_displacement.csv')
        stress_csv = os.path.join(out_dir, 'stress_cloud.csv')

        export_load_displacement(odb, step_name, node_set_name, disp_u, reaction_rf, ld_csv)
        export_stress_cloud(odb, step_name, frame_idx, stress_csv)
    finally:
        odb.close()


if __name__ == '__main__':
    main()
