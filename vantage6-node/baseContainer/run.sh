#!/bin/sh
echo "Hi there!"
echo "Reading the data from input.txt"
echo "---------------------------[input.txt]---------------------------"
cat input.txt
echo ""
echo "---------------------------[input.txt]---------------------------"
echo
echo "Writing/appending some data to output.txt"
echo "some data from run.sh" >> /output.txt
echo $(date) >> /output.txt
