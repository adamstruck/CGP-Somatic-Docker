#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
This script is intended to run within the docker container.

Test data available to download from:
https://s3-eu-west-1.amazonaws.com/wtsi-pancancer/testdata/HCC1143_ds.tar
"""
from __future__ import print_function

import argparse
import glob
import os
import re
import shlex
import subprocess
import sys


def collect_args():
    descr = 'SeqWare-based Variant Calling Workflow from Sanger'
    parser = argparse.ArgumentParser(
        description=descr
    )
    parser.add_argument("--tumor",
                        type=str,
                        required=True,
                        nargs="+",
                        help="tumor BAM input")
    parser.add_argument("--normal",
                        type=str,
                        required=True,
                        help="matched normal BAM input")
    parser.add_argument("--output-dir",
                        type=str,
                        default="/output/",
                        help="directory in which to store the outputs of the workflow.")
    parser.add_argument("--refFrom",
                        type=str,
                        required=True,
                        help="reference file archive for CGP-Somatic-Core workflow. \
                        Available to download from: https://s3-eu-west-1.amazonaws.com/wtsi-pancancer/reference/GRCh37d5_CGP_refBundle.tar.gz ")
    parser.add_argument("--bbFrom",
                        type=str,
                        required=True,
                        help="battenberg reference file archive for CGP-Somatic-Core workflow. \
                        Available to download from: https://s3-eu-west-1.amazonaws.com/wtsi-pancancer/reference/GRCh37d5_battenberg.tar.gz")
    parser.add_argument("--keep-all-seqware-output-files",
                        dest='keep_all_seqware_output_files',
                        default=False,
                        action="store_true",
                        help=argparse.SUPPRESS)
    return parser


def write_ini(args, out_dir):
    output_dir = os.path.abspath(args.output_dir).split("/")[-1]
    output_prefix = re.sub(output_dir, "", os.path.abspath(args.output_dir))

    if os.path.isfile(args.refFrom):
        refFrom = os.path.abspath(args.refFrom)
    elif re.match("^http", args.refFrom):
        refFrom = args.refFrom
    else:
        raise Exception("refFrom must be a local file or a valid URL")

    if os.path.isfile(args.bbFrom):
        bbFrom = os.path.abspath(args.bbFrom)
    elif re.match("^http", args.bbFrom):
        bbFrom = args.bbFrom
    else:
        raise Exception("bbFrom must be a local file or a valid URL")

    # based on workflow/config/CgpSomaticCore.ini
    # set up like this to make it easy to parameterize addtional settings
    # in the future
    ini_parts = ["refFrom={0}".format(refFrom),
                 "bbFrom={0}".format(bbFrom),
                 # input files
                 "tumourAliquotIds={0}".format(""),
                 "tumourAnalysisIds={0}".format(""),
                 "tumourBams={0}".format(":".join(args.tumor)),
                 "controlAnalysisId={0}".format(""),
                 "controlBam={0}".format(args.normal),
                 # output dir setup
                 "output_dir={0}".format(output_dir),
                 "output_prefix={0}".format(output_prefix),
                 # clean up
                 "cleanup={0}".format("false"),
                 "cleanupBams={0}".format("false"),
                 # basic setup
                 "coresAddressable={0}".format("24"),
                 "memHostMbAvailable={0}".format("108000"),
                 "study-refname-override={0}".format(""),
                 "analysis-center-override={0}".format(""),
                 "assembly={0}".format("GRCh37"),
                 "species={0}".format("human"),
                 "seqType={0}".format("WGS"),
                 "gender={0}".format("L"),
                 "refExclude={0}".format("MT,GL%,hs37d5,NC_007605"),
                 # GENERIC
                 "memWorkflowOverhead={0}".format("3000"),
                 "memMarkTime={0}".format("4000"),
                 "memGenotype={0}".format("4000"),
                 "memContam={0}".format("4000"),
                 "memQcMetrics={0}".format("4000"),
                 "memGetTbi={0}".format("4000"),
                 "memGenerateBasFile={0}".format("4000"),
                 "memPackageResults={0}".format("4000"),
                 # QC
                 "contamDownSampOneIn={0}".format("25"),
                 # BATTENBERG
                 "memUnpack={0}".format("4000"),
                 "memBbMerge={0}".format("4000"),
                 # ASCAT
                 "memAlleleCount={0}".format("4000"),
                 "memAscat={0}".format("8000"),
                 "memAscatFinalise={0}".format("4000"),
                 # PINDEL
                 "memPindelInput={0}".format("7000"),
                 "memPindelPerThread={0}".format("8000"),
                 "memPindelVcf={0}".format("8000"),
                 "memPindelMerge={0}".format("6000"),
                 "memPindelFlag={0}".format("8000"),
                 # BRASS
                 "memBrassInput={0}".format("6000"),
                 # new
                 "memBrassCoverPerThread={0}".format("2000"),
                 # new
                 "memBrassCoverMerge={0}".format("500"),
                 "memBrassGroup={0}".format("4500"),
                 # new group, isize and normcn can run in parallel
                 "memBrassIsize={0}".format("2000"),
                 "memBrassNormCn={0}".format("4000"),
                 "memBrassFilter={0}".format("4500"),
                 "memBrassSplit={0}".format("4000"),
                 "memBrassAssemblePerThread={0}".format("4000"),
                 "memBrassGrass={0}".format("4000"),
                 "memBrassTabix={0}".format("4000"),
                 # CAVEMAN
                 "memCaveCnPrep={0}".format("4000"),
                 "memCavemanSetup={0}".format("4000"),
                 "memCavemanSplit={0}".format("4000"),
                 "memCavemanSplitConcat={0}".format("4000"),
                 "memCavemanMstepPerThread={0}".format("3000"),
                 "memCavemanMerge={0}".format("4000"),
                 "memCavemanEstepPerThread={0}".format("3000"),
                 "memCavemanMergeResults={0}".format("4000"),
                 "memCavemanAddIds={0}".format("4000"),
                 "memCavemanFlag={0}".format("5000"),
                 "memCavemanTbiClean={0}".format("4000")]

    ini = "\n".join(ini_parts)
    ini_file = os.path.join(out_dir, "workflow.ini")
    with open(ini_file, 'wb') as f:
        f.write(ini)


def execute(cmd):
    print("RUNNING...\n", cmd, "\n")
    process = subprocess.Popen(shlex.split(cmd),
                               shell=False,
                               stdout=subprocess.PIPE,
                               stderr=subprocess.PIPE)

    while True:
        nextline = process.stdout.readline()
        if nextline == '' and process.poll() is not None:
            break
        sys.stdout.write(nextline)
        sys.stdout.flush()

    stderr = process.communicate()[1]
    if stderr is not None:
        print(stderr)
    return process.returncode


def main():
    parser = collect_args()
    args = parser.parse_args()

    workflow_version = "0.0.0"
    seqware_basedir = "/home/seqware/CGP-Somatic-Docker"

    # WRITE WORKFLOW INI
    write_ini(args, seqware_basedir)

    seqware_workflow_bundle = os.path.join(
        seqware_basedir,
        "target/Workflow_Bundle_CgpSomaticCore_{0}_SeqWare_1.1.1".format(
            workflow_version
        ))

    # RUN WORKFLOW
    cmd_parts = ["seqware bundle launch",
                 "--dir {0}".format(seqware_workflow_bundle),
                 "--engine whitestar-parallel",
                 "--ini {0}".format(
                     os.path.join(seqware_basedir, "workflow.ini")
                 ),
                 "--no-metadata"]
    cmd = " ".join(cmd_parts)
    execute(cmd)

    if (args.keep_all_seqware_output_files):
        # find seqware tmp output path; it contains generated scripts w/
        # stdout stderr for each step
        run_info_output_path = glob.glob("/datastore/oozie-*")[0]

        # make the output directory if it does not exist
        if not os.path.isdir(args.output_dir):
            # Need to use sudo since this is process is running as seqware
            execute("sudo mkdir -p {0}".format(args.output_dir))
            # Ensure we can write to the output_dir
            execute("sudo chown -R seqware {0}".format(args.output_dir))

        # move all files to the output directory
        execute("mv {0}/* {1}".format(
            run_info_output_path, args.output_dir
        ))


if __name__ == "__main__":
    main()
