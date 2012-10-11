#!/bin/bash
HONDIR=`dirname "$0"`
pushd "$HONDIR"
export LC_ALL=C
python launcher.py sea
popd
