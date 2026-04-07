# -*- coding: utf-8 -*-
"""
Server-side exporter for Abaqus 2021.
Run with:
    abaqus python export_abaqus_data.py -- \
        --odb job.odb \
        --step Step-1 \
        --disp-node-set RP-TOP \
        --reaction-node-sets RP-BOTTOM \
        --disp-u U2 \
        --reaction-rf RF2 \
        --frame -1 \
        --out-dir ./export
"""

from __future__ import print_function
import os
import sys
import csv
import re

from odbAccess import openOdb
from abaqusConstants import INTEGRATION_POINT


def parse_args(argv):
    args = {
        'odb': None,
        'step': None,
        'node_set': None,
        'disp_node_set': 'RP-top',
        'reaction_node_sets': 'RP-bottom',
        'disp_u': 'AUTO',
        'reaction_rf': 'AUTO',
        'frame': '-1',
        'out_dir': 'export',
    }

    i = 0
    while i < len(argv):
        key = argv[i]
        if key in (
            '--odb',
            '--step',
            '--node-set',
            '--disp-node-set',
            '--reaction-node-sets',
            '--disp-u',
            '--reaction-rf',
            '--frame',
            '--out-dir',
        ):
            if i + 1 >= len(argv):
                raise ValueError('Missing value for %s' % key)
            value = argv[i + 1]
            if key == '--odb':
                args['odb'] = value
            elif key == '--step':
                args['step'] = value
            elif key == '--node-set':
                args['node_set'] = value
            elif key == '--disp-node-set':
                args['disp_node_set'] = value
            elif key == '--reaction-node-sets':
                args['reaction_node_sets'] = value
            elif key == '--disp-u':
                args['disp_u'] = value.strip() or None
            elif key == '--reaction-rf':
                args['reaction_rf'] = value.strip() or None
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

    if args['node_set']:
        if not args['disp_node_set']:
            args['disp_node_set'] = args['node_set']
        if not args['reaction_node_sets']:
            args['reaction_node_sets'] = args['node_set']

    return args


def _node_set_from_root_assembly(odb, node_set_name):
    key = node_set_name.upper()
    if key not in odb.rootAssembly.nodeSets:
        raise KeyError('Node set not found in rootAssembly: %s' % node_set_name)
    return odb.rootAssembly.nodeSets[key]


def _split_names(csv_text):
    return [x.strip() for x in csv_text.split(',') if x.strip()]


def _reaction_unit_info(output_name):
    upper_name = output_name.upper()
    if upper_name.startswith('RF'):
        return 1.0 / 1000.0, 'kN'
    if upper_name.startswith('RM'):
        return 1.0 / 1000000.0, 'kNm'
    return 1.0, None


def _history_series(history_region, output_name):
    if output_name not in history_region.historyOutputs:
        return None
    data = history_region.historyOutputs[output_name].data
    if not data:
        return None
    return list(data)


def _series_value_at_time(series, step_time):
    if not series:
        return None

    best_val = series[0][1]
    best_dt = abs(series[0][0] - step_time)
    for t, v in series:
        dt = abs(t - step_time)
        if dt < best_dt:
            best_dt = dt
            best_val = v
    return best_val


def _normalize_name(name):
    return name.strip().upper().replace('-', '_')


def _job_prefix_from_odb_path(odb_path):
    job_name = os.path.splitext(os.path.basename(odb_path))[0].upper()
    parts = [x for x in re.split(r'[-_]', job_name) if x]
    if parts:
        return parts[0]
    return job_name


def _resolve_export_rule(odb_path, disp_u, reaction_rf):
    prefix = _job_prefix_from_odb_path(odb_path)
    rules = {
        'KC': {
            'disp_u': 'U3',
            'reaction_rf': 'RF3',
            'disp_scale': -1.0,
            'reaction_scale': 1.0,
        },
        'KW': {
            'disp_u': 'UR1',
            'reaction_rf': 'RM1',
            'disp_scale': -1.0,
            'reaction_scale': -1.0,
        },
        'NZ': {
            'disp_u': 'UR2',
            'reaction_rf': 'RM2',
            'disp_scale': 1.0,
            'reaction_scale': -1.0,
        },
        'ZY': {
            'disp_u': 'U2',
            'reaction_rf': 'RF2',
            'disp_scale': -1.0,
            'reaction_scale': 1.0,
        },
    }

    resolved = {
        'disp_u': 'U2',
        'reaction_rf': 'RF2',
        'disp_scale': 1.0,
        'reaction_scale': 1.0,
        'prefix': prefix,
        'source': 'default',
    }

    if prefix in rules:
        resolved.update(rules[prefix])
        resolved['source'] = 'odb_prefix'

    if disp_u and disp_u.upper() != 'AUTO':
        resolved['disp_u'] = disp_u
        resolved['disp_scale'] = 1.0
        resolved['source'] = 'cli_override'

    if reaction_rf and reaction_rf.upper() != 'AUTO':
        resolved['reaction_rf'] = reaction_rf
        resolved['reaction_scale'] = 1.0
        resolved['source'] = 'cli_override'

    return resolved


def _find_history_regions_by_name(step, target_name, output_name):
    target_norm = _normalize_name(target_name)
    matches = []
    for region_name, region in step.historyRegions.items():
        if output_name not in region.historyOutputs:
            continue
        region_norm = _normalize_name(region_name)
        if region_norm == target_norm or target_norm in region_norm:
            matches.append(region)
    return matches


def _regions_for_set_or_point(odb, step, set_name, output_name):
    direct_matches = _find_history_regions_by_name(step, set_name, output_name)
    if direct_matches:
        return {'mode': 'regions', 'regions': direct_matches}

    try:
        node_set = _node_set_from_root_assembly(odb, set_name)
    except KeyError:
        return {'mode': 'regions', 'regions': []}

    allowed_nodes = set()
    for ns in node_set.nodes:
        for node in ns:
            allowed_nodes.add(node.label)

    node_regions = []
    for region_name, region in step.historyRegions.items():
        if output_name not in region.historyOutputs:
            continue
        if not region_name.startswith('Node '):
            continue
        try:
            node_label = int(region_name.split('.')[-1])
        except Exception:
            continue
        if node_label in allowed_nodes:
            node_regions.append(region)

    return {'mode': 'regions', 'regions': node_regions}


def export_load_displacement(
    odb,
    step_name,
    disp_node_set_name,
    reaction_set_names,
    disp_u,
    reaction_rf,
    disp_scale,
    reaction_extra_scale,
    out_csv,
):
    step = odb.steps[step_name]
    reaction_scale, reaction_unit = _reaction_unit_info(reaction_rf)
    reaction_scale = reaction_scale * reaction_extra_scale

    disp_regions_info = _regions_for_set_or_point(odb, step, disp_node_set_name, disp_u)
    disp_regions = disp_regions_info['regions']
    if not disp_regions:
        raise KeyError('No history regions found for displacement set/point: %s (%s)' % (disp_node_set_name, disp_u))

    reaction_region_map = {}
    for set_name in reaction_set_names:
        info = _regions_for_set_or_point(odb, step, set_name, reaction_rf)
        if not info['regions']:
            raise KeyError('No history regions found for reaction set/point: %s (%s)' % (set_name, reaction_rf))
        reaction_region_map[set_name] = info['regions']

    with open(out_csv, 'w') as f:
        writer = csv.writer(f)
        header = ['frame_id', 'step_time']
        for set_name in reaction_set_names:
            reaction_label = reaction_rf
            if reaction_unit:
                reaction_label = '%s_%s' % (reaction_rf, reaction_unit)
            header.append('sum_%s__%s' % (reaction_label, set_name))
        header.append('avg_%s__%s' % (disp_u, disp_node_set_name))
        writer.writerow(header)

        for frame_id, frame in enumerate(step.frames):
            disp_values = []
            row = [frame_id, frame.frameValue]

            for set_name in reaction_set_names:
                total_rf = 0.0
                has_rf = False
                for region in reaction_region_map[set_name]:
                    rf_series = _history_series(region, reaction_rf)
                    rf_val = _series_value_at_time(rf_series, frame.frameValue)
                    if rf_val is not None:
                        total_rf += rf_val
                        has_rf = True
                row.append((total_rf * reaction_scale) if has_rf else 0.0)

            for region in disp_regions:
                u_series = _history_series(region, disp_u)
                u_val = _series_value_at_time(u_series, frame.frameValue)
                if u_val is not None:
                    disp_values.append(u_val * disp_scale)
            avg_u = sum(disp_values) / float(len(disp_values)) if disp_values else 0.0
            row.append(avg_u)
            writer.writerow(row)

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
    disp_node_set_name = args['disp_node_set']
    reaction_set_names = _split_names(args['reaction_node_sets'])
    frame_idx = int(args['frame'])
    out_dir = args['out_dir']
    export_rule = _resolve_export_rule(odb_path, args['disp_u'], args['reaction_rf'])
    disp_u = export_rule['disp_u']
    reaction_rf = export_rule['reaction_rf']

    if not os.path.isdir(out_dir):
        os.makedirs(out_dir)

    print(
        '[INFO] export rule: prefix=%s source=%s disp_set=%s disp=%s x %.1f reaction_sets=%s reaction=%s x %.1f'
        % (
            export_rule['prefix'],
            export_rule['source'],
            disp_node_set_name,
            disp_u,
            export_rule['disp_scale'],
            ','.join(reaction_set_names),
            reaction_rf,
            export_rule['reaction_scale'],
        )
    )

    odb = openOdb(path=odb_path, readOnly=True)
    try:
        ld_csv = os.path.join(out_dir, 'load_displacement.csv')
        stress_csv = os.path.join(out_dir, 'stress_cloud.csv')

        export_load_displacement(
            odb,
            step_name,
            disp_node_set_name,
            reaction_set_names,
            disp_u,
            reaction_rf,
            export_rule['disp_scale'],
            export_rule['reaction_scale'],
            ld_csv,
        )
        export_stress_cloud(odb, step_name, frame_idx, stress_csv)
    finally:
        odb.close()


if __name__ == '__main__':
    main()
