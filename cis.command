#!/bin/bash
HONDIR=`dirname "$0"`
pushd "$HONDIR"
if [[ `uname` == 'Darwin' ]]; then
	export LC_ALL=C
fi
python launcher.py cis
popd
