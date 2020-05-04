#!/usr/bin/env bash
CURRENT_DIR="$(cd "$(dirname "$0")" && pwd)"
ROOT_DIR=${CURRENT_DIR}/..
VENV_DIR=${ROOT_DIR}/venv

# create virtualenv
virtualenv --python=python3.7 ${VENV_DIR}
# install requirements

source ${VENV_DIR}/bin/activate && pip3.6 install -r ${ROOT_DIR}/requirements.txt


