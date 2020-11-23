#!/usr/bin/env python3
import sys
import json


def run(filename):
    with open(filename) as fp:
        BUILD = json.load(fp)

    BUILD += 1
    with open(filename, 'w') as fp:
        json.dump(BUILD, fp)


if __name__ == '__main__':
    run(sys.argv[1])
