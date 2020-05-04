#!/usr/bin/env bash
CURRENT_DIR="$(cd "$(dirname "$0")" && pwd)"
ROOT_DIR=${CURRENT_DIR}/..
VENV_DIR=${ROOT_DIR}/venv

# create virtualenv
if [ ! -d ${VENV_DIR} ]
then
	virtualenv --python=python3.7 ${VENV_DIR}
fi
# install requirements

source ${VENV_DIR}/bin/activate && ${VENV_DIR}/bin/pip install -r ${ROOT_DIR}/requirements.txt


