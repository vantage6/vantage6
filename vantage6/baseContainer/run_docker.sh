#!/bin/sh

# Build the docker image
docker build -t test_image .

# Run the docker image
touch input.txt
touch output.txt

docker run\
 --rm \
 -it \
 -v $PWD/input.txt:/input.txt\
 -v $PWD/output.txt:/output.txt\
 test_image
