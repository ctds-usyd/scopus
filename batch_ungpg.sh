#/bin/bash

if [ -z "$3" -o -n "$4" ]
then
	echo Usage $0 PASSPHRASE_FILE IN_DIR OUT_DIR >&2
	echo This will decrypt every gpg file in IN_DIR to corresponding directory structure in OUT_DIR >&2
	exit 1
fi

passphrase_file=$1
in_dir=$2
out_dir=$3

cd $in_dir

find . -name '*.gpg' | xargs -n	1 -I{} bash -c 'f="{}"; in_path='$in_dir'/$f; out_path='$out_dir'/${f::-4}; echo decrypting $in_path to $out_path; mkdir -p $(dirname $out_path); gpg -o $out_path --batch --passphrase-file='$passphrase_file' $in_path'
