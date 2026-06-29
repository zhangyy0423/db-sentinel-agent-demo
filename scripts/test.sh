#!/usr/bin/env bash

export HUSKY=0
export REPO_NAME="repo-for-test"
export DESCRIPTION=""
export SSH_URL=$AGILE_ICODE_URL
export CREATOR=$AGILE_PIPELINE_TRIGGER_USER

set -e

echo "node $(node -v)"
echo "npm $(npm -v)"

sh init.sh
sh scripts/build.sh

git checkout .
git clean -fd
