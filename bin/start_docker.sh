#!/usr/bin/env bash

cd "$(dirname "$0")/.."

docker stop wizgram; docker rm wizgram
echo ${pwd}
docker run wizgram ${@}