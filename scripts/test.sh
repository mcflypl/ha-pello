#!/bin/sh
# Runs the given command (tests by default) in the pinned Home Assistant test image.
set -eu
cd "$(dirname "$0")/.."
docker image inspect ha-pello-test >/dev/null 2>&1 || docker build -f Dockerfile.test -t ha-pello-test .
[ "$#" -gt 0 ] || set -- pytest
exec docker run --rm -u "$(id -u):$(id -g)" -e HOME=/tmp -v "$PWD":/app -w /app ha-pello-test "$@"
