#!/bin/bash

xmltidy() {
python -c '
import sys, xml.dom.minidom
print(xml.dom.minidom.parseString(sys.stdin.read()).toprettyxml(indent="  ", encoding="utf8"))
'
}

grep_args=$(while [ -n "$1" ]; do echo "-e s2.0-0*${1}.xml" ; shift; done)
echo Finding $grep_args >&2
paths=$(zgrep $grep_args index.txt.gz)
for path in $paths
do
	tar xOzvf $(echo $path | cut -d/ -f1-2).tgz $path | xmltidy
done