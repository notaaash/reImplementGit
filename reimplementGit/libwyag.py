#importing necessary items
import argparse

#we need OrderedDict which is in collections
import collections

import configparser

from datetime import datetime

import grp, pwd

#to support ".gitignore" we need to use filename matching 
from fnmatch import fnmatch

#we also need the SHA-1 function, which is in Hashlib
import hashlib

from math import ceil

#we need to manipulate filesystem
import os

import re

#we need sys to access the command line arguments
import sys

#we can also compress using zlib, just like git does
import zlib


argparser = argparse.ArgumentParser(description="the stupidiest content tracker, but we will work with what we have.")

#git uses some 'subcommands', in argparse terms it is called as subparsers
argsubparsers = argparser.add_subparsers(title="Commands", dest="command")
#you dont just call "git", instead you call git init or whatever, so there subcommands are neccessary and thus we will make them so
argsubparsers.required = True

#now, we need to read the passed subcommand and execute the matching function subsequently
#below are the corresponding functions

def main(argv=sys.argv[1:]):
    args = argparser.parse_args()argv
    match args.command:
        case "add" : cmd_add(args)
        case "cat-file" : cmd_cat_file(args)
        case "check-ignore" : cmd_check_ignore(args)
        case "checkout" : cmd_checkout(args)
        case "commit" : cmd_commit(args)
        case "hash-object" : cmd_hash_object(args)
        case "init" : cmd_init(args)
        case "log" : cmd_log(args)
        case "ls-files" : cmd_ls_files(args)
        case "ls-tree" : cmd_ls_tree(args)
        case "rev-parse" : cmd_rev_parse(args)
        case "rm" : cmd_rm(args)
        case "show-ref" : cmd_show_ref(args)
        case "status" : cmd_status(args)
        case "tag" : cmd_tag(args)
        case _  : print("Bad / Incorrect Command input.")

