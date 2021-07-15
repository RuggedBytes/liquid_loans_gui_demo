#!/bin/bash
# format the python code
isort -fass $1
isort $1
black -l 79 $1
