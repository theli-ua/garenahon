#!/bin/bash
HONDIR=`dirname "$0"`
pushd "$HONDIR"
if [[ -e /etc/debian_version ]]; then 
        export LANG=C.UTF-8
fi
if [[ `uname` == 'Darwin' ]]; then
        export LC_ALL=C
fi
python launcher.py cis -d
popd
