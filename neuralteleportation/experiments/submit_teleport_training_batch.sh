#!/bin/bash

__usage="
Usage: submit_teleport_training_batch.sh --project_root_dir PROJECT_ROOT_DIR
                                         --dataset_dir DATASET_DIR
                                         {--experiment_config_dir EXPERIMENT_CONFIG_DIR |
                                         --experiment_config_file EXPERIMENT_CONFIG_FILE
                                         --virtualenv VIRTUALENV}
                                         [--email EMAIL]

required arguments:
  --project_root_dir PROJECT_ROOT_DIR, -p PROJECT_ROOT_DIR
                        Root directory of the project's code
                        (typically where you cloned the repository)
  --dataset_dir DATASET_DIR, -d DATASET_DIR
                        Directory where pre-downloaded datasets are stored

optional arguments:
  --email EMAIL, -m EMAIL
                        Email address at which SLURM will send notifications
                        regarding the states of the submitted jobs

required mutually exclusive arguments:
  --experiment_config_dir EXPERIMENT_CONFIG_DIR, -c EXPERIMENT_CONFIG_DIR
                        Directory of the YAML configuration files to run as individual,
                        parallel jobs
                        This directory must not be deleted until all jobs have left
                        pending status!!! (the config files are only loaded once the
                        jobs are active)

  --experiment_config_file EXPERIMENT_CONFIG_FILE, -f EXPERIMENT_CONFIG_FILE
                        YAML matrix configuration file to run as individual,
                        parallel jobs
  --virtualenv VIRTUALENV, -v VIRTUALENV
                        Path to a virtualenv set up for the project
                        Required only when '--experiment_config_file' is used
"

usage()
{
  echo "$__usage"
  exit 2
}

PARSED_ARGUMENTS=$(getopt -n submit_teleport_training_batch -o p:d:c:f:v:m: --long project_root_dir:,dataset_dir:,experiment_config_dir:,experiment_config_file:,virtualenv:,email: -- "$@")
VALID_ARGUMENTS=$?
if [ "$VALID_ARGUMENTS" != "0" ]; then
  usage
fi

eval set -- "$PARSED_ARGUMENTS"
while :
do
  case "$1" in
    -p | --project_root_dir) project_root_dir="$2"; shift 2 ;;
    -d | --dataset_dir) dataset_dir="$2"; shift 2 ;;
    -c | --experiment_config_dir) experiment_config_dir="$2"; shift 2 ;;
    -f | --experiment_config_file) experiment_config_file="$2"; shift 2 ;;
    -v | --virtualenv) virtualenv="$2"; shift 2 ;;
    -m | --email) email="$2"; shift 2 ;;
    # -- means the end of the arguments; drop this, and break out of the while loop
    --) shift; break ;;
    # If invalid options were passed, then getopt should have reported an error,
    # which we checked as VALID_ARGUMENTS when getopt was called...
    *) echo "Unexpected option: $1 - this should not happen."
       usage ;;
  esac
done

# Additional manual checks on arguments
required_args=("$project_root_dir" "$dataset_dir")
for required_arg in "${required_args[@]}"; do
  if [ -z "$required_arg" ]; then
    echo "Missing one or more required argument(s)"; usage
  fi
done
if [ -z "$experiment_config_dir" ] && [ -z "$experiment_config_file" ]; then
  echo "Missing one of the required mutually exclusive arguments"; usage
fi
if [ -n "$experiment_config_dir" ] && ( [ -n "$experiment_config_file" ] || [ -n "$virtualenv" ] ); then
  echo "Provided conflicting arguments"; usage
fi
if [ -n "$experiment_config_file" ] && [ -z "$virtualenv" ]; then
  echo "Missing required 'virtualenv' argument when selecting 'experiment_config_file' option"; usage
fi

# Ensure the project's root directory exists
if [ ! -d "$project_root_dir" ]; then
  echo "Provided project root directory does not exist: $project_root_dir."; exit 1
fi

if [ -n "$experiment_config_file" ]; then
  source "$virtualenv"/bin/activate
  export PYTHONPATH=$PYTHONPATH:"$project_root_dir"
  # Create temp directory where to save individual run config files
  experiment_config_dir=$(TMPDIR="$HOME"/scratch mktemp -d -t run-config-XXXXXXXXXX)
  # Split file of matrix configurations into files for each individual configuration in the matrix
  python "$project_root_dir"/neuralteleportation/experiments/config/unravel_matrix_config.py "$experiment_config_file" \
    --output_dir "$experiment_config_dir"
fi

if [ -n "$email" ]; then
  arg_mail="--mail-user=$email --mail-type=ALL"
fi

# Submit individual jobs for all the configuration files in``experiment_config_dir``
for experiment_config_file in "$experiment_config_dir"/*.yml; do
  sbatch $arg_mail \
    "$project_root_dir"/neuralteleportation/experiments/submit_teleport_training.sh \
      -p "$project_root_dir" -d "$dataset_dir" -c "$experiment_config_file"
done