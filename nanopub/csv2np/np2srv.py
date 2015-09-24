#!/usr/bin/env python
# coding=UTF-8

""" POST nanopublications in Trig format to a Nanopublication server """

import os
import argparse
import requests

parser = argparse.ArgumentParser(description='POST nanopublications in Trig \
format to a Nanopublication server')
parser.add_argument('trig_dir', metavar='trigs', type=str, nargs='?',
                    help='path to directory with Trig files')
parser.add_argument('srv_url', metavar='srv_url', type=str, nargs='?',
                    help='path to an output directory')
parser.add_argument('--verbose', '-v', dest='verbose', 
                    action='store_true', help='be verbose')

args = parser.parse_args()
trig_dir = args.trig_dir
srv_url = args.srv_url

for f in os.listdir(trig_dir):
    with open(os.path.join(trig_dir, f),'rb') as np:
        r = requests.post(srv_url, data=np)
        if r.status_code == 201:
            if args.verbose:
                print("Added nanopub", f)
        else:
            print ("Error adding nanopub", f)
            r.raise_for_status()
