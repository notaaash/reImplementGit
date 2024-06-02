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
    args = argparser.parse_args(argv)
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


class GitRepository (object) :
    """A Git Repository"""

    worktree = None
    gitdir = None
    conf = None
    
    def __init__(self, path, force = False):
        self.worktree = path
        self.gitdir = os.path.join(path, ".git")

        #It checks if the .git directory exists in the provided path. 
        #If force is not set and the directory does not exist,
        #it raises an exception indicating that the provided path is not a valid Git repository.
        if not (force or os.path.isdir(self.gitdir)):
            raise Exception("Not a valid Git Repository %s " % path)
        
        #we are using the force boolean as a sort of bruteforce to overwrite any checks and just "create" the repository.
        #even when the path doesn't point to a valid git directory.
        #read configuration file in .git/config
        self.conf = configparser.ConfigParser()
        cf = repo_file(self, "config")

        if cf and os.path.exists(cf):
            self.conf.read([cf])
        elif not force:
            raise Exception("Configuration file is missing :( ")
        
        if not force:
            vers = int(self.conf.get("core", "repositoryformatversion"))
            if vers != 0 :
                raise Exception("Unsupported repositoryformatversion %s :( " % vers)
        
    #creating a general path building function
    def repo_path(repo, *path):
        """Compute path under repo's gitdir."""
        return os.path.join(repo.gitdir, *path)
    
    def repo_file(repo, *path, mkdir=False):

        #file version only creates directories up to the last component, thus the *path[:-1] :))
        """Same as repo_path but create dirname(*path) if absent.
        For example, repo_file(r, \"refs\", \"remotes\", \"origin\") will create 
        .git/refs/remotes/origin."""

        if repo_dir(repo, *path[:-1], mkdir = mkdir):
            return repo_path(repo, *path)
        
    def repo_dir(repo, *path, mkdir = False):
        """same as repo_path, but mkdir *path is *path is absent."""

        path = repo_path(repo, *path)

        if os.path.exists(path):
            if (os.path.isdir(path)):
                return path
            else :
                raise Exception("Not a directory %s :( " % path)
            
        if mkdir:
            os.makedirs(path)
            return path
        else :
            return None
        
    def repo_create(path):
        """Create a new repository at path. :) """

        repo = GitRepository(path, True)

        #first we make sure that the path doesnt exist or is an empty dir

        if os.path.exists(repo.worktree):
            if not os.path.isdir(repo.worktree):
                raise Exception("%s is not a directory ! :( " % path)
            if os.path.exists(repo.gitdir) and os.listdir(repo.gitdir):
                raise Exception("%s is not empty" % path)
        else:
            os.makedirs(repo.worktree)

        assert repo_dir(repo, "branches", mkdir = True)
        assert repo_dir(repo, "objects", mkdir = True)
        assert repo_dir(repo, "refs", "tags", mkdir = True)
        assert repo_dir(repo, "refs", "heads", mkdir=True)

        # .git/description
        with open(repo_file(repo, "description"), "w") as f:
            f.write("Unnamed repository; edit this file 'description' to name the repository.\n")

        # .git/HEAD
        with open(repo_file(repo, "HEAD"), "w") as f:
            f.write("ref: refs/heads/master\n")

        with open(repo_file(repo, "config"), "w") as f:
            config = repo_default_config()
            config.write(f)

        return repo
    
    def repo_default_config():
        ret = configparser.ConfigParser()

        ret.add_section("core")
        ret.set_("core", "repositoryformatversion ", "0")
        ret.set("core", "filemode", "false")
        ret.set("core", "bare", "false")

        return ret
    
    #parser to parse init
    argsp = argsubparsers.add_parser("init", help="initialise a new, empty repository.")

    #also collect the path argument and store it in args.path
    argsp.add_argument("path",
                       metavar = "directory",
                       nargs="?",
                       default=".",
                       help="where to create the repository.")
    
    #function to call the actual creation of the git repository.
    def cmd_init(args):
        repo_create(args.path)

    #this function is to find the root of the respository we are working in
    def repo_find(path=".", required=True):
        path = os.path.realpath(path)

        #the below code is basically joining the current path with the file extension ".git", what that does is makes a path
        #that is a path to the supposed .git file in the current directory, now if the file exists, the if statement returns True
        #and the path of th current directory is returned as the root of the gitdirectory
        #if it doesnt find a .git file, it will go back one step and keep on doing this until it either finds the file
        #or reaches the root of the directory
        if os.path.isdir(os.path.join(path, ".git")):
            return GitRepository(path)
        
        #if we haven't returned, recurse in parent
        parent = os.path.realpath(os.path.join(path, ".."))

        if parent == path:
            #bottom case
            #os.path.join("/", "..") == "/":
            #if parent==path, then path is root
            if required:
                raise Exception("No git directory.")
            else:
                return None
        
        #recursive case
        return repo_find(parent, required)



