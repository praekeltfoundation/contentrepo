#!/bin/bash

tag="${1#refs/tags/}"

if [ "${tag}" = "${1}" ]; then
    echo "Not a tag ref: '${1}'" >&2
    exit 1
fi

echo "::set-output name=TAG::${tag}"
