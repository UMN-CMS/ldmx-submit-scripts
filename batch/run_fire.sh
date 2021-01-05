#!/bin/bash

set -x

###############################################################################
# run_fire.sh
#   Batch running script for executing fire on a worker node and then copying
#   the results to an output directory.
###############################################################################

_work_dir=$1 # directory to run inside of
_env_script=$2 #environment to use
_config_script=$3 #script itself to run
_output_dir=$4 #output directory to copy products to
_config_args=${@:5} #arguments to configuration script

if [ ! -d /cvmfs/cms.cern.ch || ! -d /hdfs/cms/user ];
then
  echo "Worker node is not connected to cvmfs and/or hdfs."
  exit 99
fi

if ! mkdir -p $_work_dir
then
  echo "Can't create working directory."
  exit 110
fi
cd $_work_dir

if [[ ! -z "$(ls -A .)" ]]
then
  # temp directory non-empty
  #   we need to clean it before running so that
  #   the only files are the ones we know about
  rm -r *
fi

if ! source $_env_script
then
  echo "Wasn't able to source the environment script."
  exit 111
fi

_to_remove=""
if [[ "$_config_script" != *"hdfs"* ]]
then
  if ! cp $_config_script .
  then
    echo "Can't copy the config script to the working directory."
    exit 113
  fi
  _config_script=$(basename $_config_script)
  _to_remove="$_config_script __pycache__"
fi

if ! fire $_config_script $_config_args
then
  echo "fire returned an non-zero error status."
  exit 115
fi

# first remove the input files
#   so they don't get copied to the output
if [[ ! -z "$_to_remove" ]]
then
  if ! rm -r $_to_remove
  then
    echo "Can't remove the config file."
    exit 116
  fi
fi

# copy all other generated root files to output
if ! cp *.root $_output_dir
then
  echo "Can't copy the output root files to the output directory (or couldn't find output files)."
  exit 117
fi

