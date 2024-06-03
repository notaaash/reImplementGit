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
    
class GitObject (object):
    def __init__(self, data=None):
        if data != None:
            self.deserialize(data)
        else:
            self.init()
    
    def serialize(self, repo):
        """This function must be implemented in subclasses.
        It must read the objects contents from self.data, a byte string, and do
        whatever it takes to convert it into a meaningful representataion.
        What that exactly means depends on that particular subclass."""
        
        raise Exception("Unimplemented!")
    
    def deserialize(self, data):
        raise Exception("Unimplemented!")
    
    def init(self):
        pass # Just do nothing. This is a reasonable default.

def object_read(repo, sha):
    """read object sha from Git repository repo. Return a GitObject
    whose exact type depends on the object itself"""

    path = repo_file(repo, "objects", sha[0:2], sha[2:])

    if not os.path.isfile(path):
        return None
    
    with open (path, "rb") as f:
        raw = zlib.decompress(f.read())

        #Read object type
        x = raw.find(b' ')
        fmt = raw[0:x]

        #read and validate object size
        y = raw.find(b'\x00', x)
        size = int(raw[x:y].decode("ascii"))
        if size != len(raw)-y-1 :
            raise Exception("Malformed Object {0}: Bad Length".format(sha))
        
        #pick constructor
        match fmt:
            case b'commit' : c=GitCommit
            case b'tree' : c=GitTree
            case b'tag' : c=GitTag
            case b'blob' : c=GitBlob
            case _ :
                raise Exception("Unknown type {0} for object {1}".format(fmt.decode("ascii"), sha))
            
        #call constructor and return object
        return c(raw[y+1:])
    
def object_write(obj, repo=None):
    
    #serialize object data
    data = obj.serialize()

    #add header
    result = obj.fmt + b' ' + str(len(data)).encode() + b'\x00' + data

    #compute the hash
    sha = hashlib.sha1(result).hexdigest()

    if repo:
        #compute the path
        path = repo_path(repo, "objects", sha[0:2], sha[2:], mkdir = True)

        if not os.path.exists(path):
            with open(path, 'wb') as f:
                #compress and write 
                f.write(zlib.compress(result))
    return sha

class GitBlob(GitObject):
    fmt = b'blob'

    def serialize(self):
        return self.blobdata
    
    def deserialize(self, data):
        self.blobdata = data
    
argsp = argsubparsers.add_parser("cat-file", 
                                 help = "provide content of repository objects")

argsp.add_argument("type",
                   metavar="type",
                   choices=["blob", "commit", "tag", "tag"],
                   help="Specify the type!")

argsp.add_argument("object",
                   metavar="object",
                   help="The object to display")

def cmd_cat_file(args):
    repo = repo_find()
    cat_file(repo, args.object, fmt=args.type.encode())

def cat_file(repo, obj, fmt=None):
    obj = object_read(repo, object_find(repo, obj, fmt=fmt))
    sys.stdout.buffer.write(obj.serialize())

def object_find(repo, name, fmt=None, follow=True):
    return name

argsp = argsubparsers.add_parser("hash-object",
                                 help="compute ID and optionally creata a blob from a file")

argsp.add_argument("-t",
                   metavar="type",
                   dest="type",
                   choices=["blob", "commit", "tag", "tree"],
                   default="blob",
                   help="specify the type")

argsp.add_argument("-w",
                   dest="write",
                   action="store_true",
                   help="actually write the object into the database")

argsp.add_argument("path",
                   help="Read object from <file>")

def cmd_hash_object(args):
    if args.write:
        repo = repo_find()
    else:
        repo = None
    
    with open(args.path, "rb") as fd:
        sha = object_hash(fd, args.type.encode(), repo)
        print(sha)

def object_hash(fd, fmt, repo=None):
    """Hash object, writing it to repo if provided"""
    data = fd.read()

    # choose contructor according to fmt argument
    match fmt:
        case b'commit' : obj=GitCommit(data)
        case b'tree' : obj=GitTree(data)
        case b'tag' : obj=GitTag(data)
        case b'blob' : obj = GitBlob(data)
        case _: raise Exception("Unknown type %s!" % fmt)
    
    return object_write(obj, repo)

def kvlm_parse(raw, start=0, dct=None):
    if not dct:
        dct=collections.OrderedDict()
        # you CANNOT declare the argument as dct=OrderedDict() or all
        # call to the functions will endlessly grow the same dict
    
    # this function is recursive, it reads a key/value pair, then call
    # itself back with the new position. So we first need to know
    # where we are: at a keywords or already in the messageQ

    # we search for the next space and the next newline.
    spc = raw.find(b' ', start)
    nl = raw.find(b'\n', start)

    # if space appears before newline, we have a keyword. Otherwise,
    # it's the final message, which we just read to the end of the file.

    # base case
    # =========
    # if newline appears first (or there's no space at all, in which
    # case find returns -1), we assume a blank line. A blank line
    # means the remainder of the data is the message. We store it in 
    # the dictionary, with None as the key, and return.
    if (spc < 0) or (nl < spc):
        assert nl == start
        dct[None] = raw[start+1:]
        return dct
    
    # recursive case
    # ==============
    # we read a key-value pair and recurse for the next.
    key = raw[start:spc]

    # find the end of the value. Continuation lines begin with a 
    # space, so we loop until we find a "\n" not followed by a space.
    end = start
    while True:
        end = raw.find(b'\n', end+1)
        if raw[end+1] != ord(' '):
            break

        # grab the value
        # also, drop the leading space on continutaion lines
        value = raw[spc+1:end].replace(b'\n', b'\n')

        # dont overwrite existing data contents
        if key in dct:
            if type(dct[key]) == list:
                dct[key].append(value)
            else:
                dct[key] = [ dct[key], value]
        else:
            dct[key] = value
        
        return kvlm_parse(raw, start=end+1, dct=dct)

def kvlm_serialize(kvlm):
    ret = b''

    # output fields
    for k in kvlm.keys():
        #skip the message itself
        if k == None:
            continue
        val = kvlm[k]
        #normalize to a list
        if type(val) != list:
            val = [ val ]
        
        for v in val:
            ret += k + b' ' + (v.replace(b'\n', b'\n ')) + b'\n'

    # append message
    ret += b'\n' + kvlm[None] + b'\n'

    return ret

# now we will create the most exciting part!!!! Commit!!!!

class GitCommit(GitObject):
    fmt = b'commit'

    def deserialize(self, data):
        self.kvlm = kvlm_parse(data)

    def serialize(self):
        return kvlm_serialize(self.kvlm)
    
    def init(self):
        self.kvlm = dict()

argsp = argsubparsers.add_parser("log", help="display history of a given commit")

argsp.add_argument("commit",
                   default="HEAD",
                   nargs="?",
                   help="commit to start at.:")

def cmd_log(args):
    repo = repo_find()

    print("digraph wyaglog{")
    print(" node[shape=rect]")
    log_graphviz(repo, object_find(repor, args.commit), set())
    print("}")

def log_graphviz(repo, sha, seen):

    if sha in seen:
        return
    seen.add(sha)

    commit = object_read(repo, sha)
    short_hash = sha[0:8]
    message = commit.kvlm[None].decode("utf-8").strip()
    message = message.replace("\\", "\\\\")
    message = message.replace("\"", "\\\"")

    if "\n" in message: #keep only the first line
        message = message[:message.index("\n")]
    
    print(" c_{0} [label=\"{1}: {2}\"]".format(sha, sha[0:7], message))
    assert commit.fmt == b'commit'

    if not b'parent' in commit.kvlm.keys():
        #this is the base case, the initial commit
        return
    
    parents = commit.kvlm[b'parent']

    if type(parents) != list:
        parents = [ parents ]

    for p in parents:
        p = p.decode("ascii")
        print(" c_{0} -> c{1};".format(sha, p))
        log_graphviz(repo, p, seen)




