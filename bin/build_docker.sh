#!/usr/bin/env bash

cd "$(dirname "$0")/.."
mkdir -p docker_build/code
cp ${WISLIB_DIST} requirements.txt ./docker_build
cp run.py project/ docker_build/code -r
docker build -t wizgram . ${@}
rm docker_build/ -rf