#!/bin/bash
HONDIR=`dirname "$0"`
pushd "$HONDIR"
export LC_ALL=C.UTF-8
python launcher.py lat -d
popd
