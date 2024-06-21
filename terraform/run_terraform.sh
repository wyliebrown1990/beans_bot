#!/usr/bin/env bash
# intermediate layer between user and running docker container
SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )

echo "in directory: $(pwd)"
echo "changing to: $SCRIPT_DIR"
cd "$SCRIPT_DIR"

TERRAFORM_ARG=$1
if [[ "$TERRAFORM_ARG" == "init" ]]; then
  TERRAFORM_ARG="init"
elif [[ "$TERRAFORM_ARG" == "apply" ]]; then
  TERRAFORM_ARG="apply -auto-approve"
elif [ "$TERRAFORM_ARG" == "plan" ]; then
  TERRAFORM_ARG="plan"
else
  echo "only 'init', 'plan', or 'apply' may be passed"
  exit 1
fi

docker run  -it \
--mount "type=bind,source=$(pwd)/.aws/,target=/root/.aws" \
--mount "type=bind,source=$(pwd),target=/app" \
--workdir '/app' \
hashicorp/terraform:latest $TERRAFORM_ARG