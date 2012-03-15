#!/bin/bash
HONDIR=`dirname "$0"`
pushd "$HONDIR"
python launcher.py cis -d
popd
