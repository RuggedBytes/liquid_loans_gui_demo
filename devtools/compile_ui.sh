#!/bin/bash

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"

mkdir -p $DIR/../creditor/pyui
rm $DIR/../creditor/pyui/* 2>/dev/null
for filename in $DIR/../creditor/ui/*.ui
do
	file="${filename##*/}"
	pyuic5 $filename -o $DIR/../creditor/pyui/${file%.*}.py
done

mkdir -p $DIR/../debtor/pyui
rm $DIR/../debtor/pyui/* 2>/dev/null
for filename in $DIR/../debtor/ui/*.ui
do
	file="${filename##*/}"
	pyuic5 $filename -o $DIR/../debtor/pyui/${file%.*}.py
done

mkdir -p $DIR/../facilitator/pyui
rm $DIR/../facilitator/pyui/* 2>/dev/null
for filename in $DIR/../facilitator/ui/*.ui
do
	file="${filename##*/}"
	pyuic5 $filename -o $DIR/../facilitator/pyui/${file%.*}.py
done

mkdir -p $DIR/../common/pyui
rm $DIR/../common/pyui/* 2>/dev/null
for filename in $DIR/../common/ui/*.ui
do
	file="${filename##*/}"
	pyuic5 $filename -o $DIR/../common/pyui/${file%.*}.py
done

mkdir -p $DIR/../miner/pyui
rm $DIR/../miner/pyui/* 2>/dev/null
for filename in $DIR/../miner/ui/*.ui
do
	file="${filename##*/}"
	pyuic5 $filename -o $DIR/../miner/pyui/${file%.*}.py
done
