#!/usr/bin/env bash

if [ $# -lt 1 ]; then
    echo "usage: $0 [PYTHON]"
    exit 1
fi

PYTHON="$1"

cp -r /dups /root/dups
cd /root/dups


# SSH server is required for remote testsA
/usr/sbin/sshd

# Run all unittests
${PYTHON} -m unittest discover -v -s tests

