# -*- coding: utf-8 -*-
"""
Batch export all jobs in a .cae file to .inp files.

Usage (Windows):
    abaqus cae noGUI=write_all_inp.py -- --cae D:\abaqus_runs\project.cae --out-dir D:\abaqus_runs\inp

Notes:
    - Must run inside Abaqus/CAE environment.
    - Exports all jobs found in the CAE database.
"""

from __future__ import print_function
import os
import sys

from abaqus import openMdb, mdb


def parse_args(argv):
    args = {"cae": None, "out_dir": None}
    i = 0
    while i < len(argv):
        key = argv[i]
        norm_key = key.lstrip("-/").lower()
        if norm_key in ("cae", "out-dir", "out_dir"):
            if i + 1 >= len(argv):
                raise ValueError("Missing value for %s" % key)
            val = argv[i + 1]
            if norm_key == "cae":
                args["cae"] = val
            else:
                args["out_dir"] = val
            i += 2
        else:
            raise ValueError("Unknown argument: %s" % key)
    if not args["cae"]:
        raise ValueError("--cae is required")
    if not args["out_dir"]:
        raise ValueError("--out-dir is required")
    return args


def main():
    cae_env = os.environ.get("ABAQUS2PY_CAE_PATH")
    out_env = os.environ.get("ABAQUS2PY_OUT_DIR")
    if cae_env and out_env:
        args = {"cae": cae_env, "out_dir": out_env}
    else:
        argv = sys.argv[1:]
        if "--" in argv:
            argv = argv[argv.index("--") + 1 :]
        args = parse_args(argv)

    cae_path = os.path.abspath(args["cae"])
    out_dir = os.path.abspath(args["out_dir"])

    if not os.path.isfile(cae_path):
        raise IOError("CAE file not found: %s" % cae_path)
    if not os.path.isdir(out_dir):
        os.makedirs(out_dir)

    print("[INFO] open cae:", cae_path)
    openMdb(pathName=cae_path)

    if len(mdb.jobs.keys()) == 0:
        print("[WARN] no jobs found in cae")
        return

    old_cwd = os.getcwd()
    os.chdir(out_dir)
    try:
        for job_name in sorted(mdb.jobs.keys()):
            print("[INFO] write input:", job_name)
            mdb.jobs[job_name].writeInput()
    finally:
        os.chdir(old_cwd)

    print("[OK] all inp exported to:", out_dir)


if __name__ == "__main__":
    main()
