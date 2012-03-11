#!/usr/bin/python
# -*- coding: utf-8 -*-

import os
import sys
import json
import re
import subprocess

# define dirs, files and names:
home_dir = os.environ['HOME']
repo_file = home_dir + "/.gitglue_repos.json"
dvcs_name = "git"
dvcs_dir = "." + dvcs_name
start_dir = os.getcwd()

# warnings:
exists_warning = "%s already exists"
noadd_warning = exists_warning + " at %s. Doing nothing with it. Rename it?"
norepo_warning = "%s is not a repo"
notag_warning = "%s is not tagged with %s"
tagged_warning = "%s is already tagged with %s"
chdir_warning = "Can't change directory to %s"
nodir_warning = "Does the directory %s exist?"
nodel_warning = "Can't find %s. Is it spelled right?"
cantdel_warning = "Can't delete %s, check permissions?"
json_warning = "%s seems empty"

# errors:
chdir_error = chdir_warning
norepo_error = norepo_warning
addrepo_error = "You must specify a %s. Commata are used to separate different repos, see REPOS"
emptyfield_error = "This field needs a value. I.e: %s foo"
file_error = "Can't open %s for %s. Check if the appropriate permissions are set and it exists"
exists_error = exists_warning + ". Use -f or --force to overwrite"
notlastarg_error = "%s has additional arguments (%s) but takes none.\n If they are options like --force, --quiet or --verbose, specify them earlier."
missingarg_error = "%s needs %s as an additional argument. Check -h or --help if you are unsure."
emptyarg_error = "Even default mode needs a CMD to execute (over all repos)."
notag_error = "%s is not a tag. Add it or choose one from: %s"
nopath_error = "%s is not a valid path, does it exist?"
noopt_error = "%s is not an option. Check -h or --help"
json_error = "%s is not valid json"
relpath_error = "%s seems to be a relative path. You can use ~/, but absolute paths are necessary."
git_error = "%s says %s. Is this a valid command?"

# cli flags:
arg_force = False
arg_verbose = False
arg_git = False
arg_quiet = False
arg_nohook = False
arg_short = True

#TODO: specfify more than one tag, and use -a and -n as 'and' and 'not'.

def output_handler(output):
    global arg_quiet
    global arg_git
    global arg_short

    if arg_quiet == True:
        return
    elif arg_git == True:
        print output
        return
    elif arg_short == True:
        output = output.split("\n")
        try:
            print output[0]
            #print output[1]
        except:
            try:
                print output[0]
            except:
                pass
    print


def exit_handler():
    global start_dir

    # cleaner? 
    os.chdir(start_dir)
    exit(0)


def error_handler(message):
    if message:
        print "  - ERROR: " + message
    exit_handler()


def usage():
    message='''USAGE: gitglue ( -OPTION | --OPTION ) ( ARGUMENT )

    OPTIONS:
     -i --init              Create a json file with all repos and warn if a repo exists. -f -i deletes the repofile.
     -e --execute CMD       Execute the following CMD as a command to all repos.
     -et --exectag TAG CMD  Execute a command within all repos tagged with TAG. Currently only one TAG possible.
     -ea --execappend CMD   Only usable after -e or -et. Append a command and execute it. Can be specifed often.

     -a --addtag TAG REPOS  Add a tag to one or more repos. Trailing slashes will be removed from the name.
     -d --deltag TAG REPOS  Delete a tag from one or more repos.
     -l --listtags          List all tags.
     -c --clean             Only keep repos with a valid (accessible) path.

     -ar --addrepo REPO PATH TAGS     Add one or multiple repos. Seperate REPO PATH TAGS sequences with commas.
     -dr --delrepo REPOS     Same like addrepo but deletes. Seperate multiple REPOS with spaces.
     -lr --listrepos (REPOS) Lists name, tag(s) and path from all repos, or from matching and existing REPOS.
     -ad --adddir TAGS Add repos from the current directory and tag them with TAGS.

     -h --help         Display this help message.
     -f --force        Overwrite while adding a repo or while creating the repo file.
     -n --nohooks      TODO Do not execute pre- and post-action hooks.
     -v --verbose      Explain everything.
     -q --quiet        Suppress WARNINGs.
     -g --git          Print output from git or your dvcs. Overwrites default -s.
     -s --short        Prints the first two lines. Enabled by default, specify to disable.
     '''
    print message


def warning_handler(message):
    global arg_quiet

    if arg_quiet == False:
        print " - WARNING: " + message


def verbose(message):
    global arg_verbose

    if arg_verbose:
        print message


def read_repos():
    try:
        fh = open(repo_file, 'rb')
        repos_json = fh.read()
        fh.close()
    except:
        message = file_error % (repo_file, "reading")
        error_handler(message)

    if not re.search(r"{", repos_json):
        message = json_warning % (repo_file)
        warning_handler(message)
        repos = {}
    else:
        try:
            repos = json.loads(repos_json)
        except ValueError:
            message = json_error % (repo_file)
            error_handler(message)
    return repos

def make_json(repos):
    repos_json = json.dumps(repos, sort_keys=True, indent=4)
    return repos_json


def write_json():
    global repos_dict

    repos_json = make_json(repos_dict)
    try:
        fh = open(repo_file, 'wb')
        fh.write(repos_json)
        fh.close()
    except:
        message = file_error % (repo_file, "writing")
        error_handler(message)
    exit_handler()


def add_repo(repo_name, repo_path, repo_tags):
    global repos_dict

    pre_hook = post_hook = None
    if repo_name in repos_dict and arg_force == False:
        message = noadd_warning % (repo_name, repo_path)
        warning_handler(message)
    else:
        repo_path = strip_slash(repo_path)
        repo_name = strip_slash(repo_name)
        repos_dict[repo_name] = {'path':repo_path, 'tags':repo_tags, 'pre':pre_hook, 'post':post_hook}
    try:
        repo_tags = ' '.join(repo_tags)
    except:
        repo_tags = ''
    verbose("  - adding " + repo_name + " from: " + repo_path + " with Tags: " + repo_tags)


def pre_init(repo_path):
    if os.path.exists(repo_file):
        if arg_force == False:
            message = exists_error % (repo_file)
            error_handler(message)
        else:
            try:
                os.remove(repo_file)
            except:
                message = nodel_warning % (repo_file)
                warning_handler(message)

def init(dirname, repo_tags):
    global arg_force
    global repos_dict

    #read dir and search for repos
    verbose(" - searching for repos in " + dirname)

    for root, dirs, files in os.walk(dirname, topdown=True):
        for dirname in dirs:
            if dirname == dvcs_dir:
                repo_name = os.path.basename(root)
                repo_path = root
                pre_hook = post_hook = []
                add_repo(repo_name, repo_path, repo_tags)


# add a tag
def add_tag(tag, repos):
    global repos_dict

    verbose(" - tagging repos")
    for repo in repos:
        if repo in repos_dict:
            try:
                repos_dict[repo]["tags"].index(tag) # if there is such a value, the tag exists already.
                message = tagged_warning % (repo, tag)
                warning_handler(message)
            except:
                repos_dict[repo]["tags"].append(tag)
                verbose("  - " + repo + " is now tagged with " + tag)
        else:
            message = norepo_warning % (repo)
            warning_handler(message)


# delete a tag
def del_tag(tag, repos):
    global repos_dict

    verbose(" - untagging repos")
    for repo in repos:
        if repo in repos_dict:
            try:
                repos_dict[repo]["tags"].remove(tag) # try to remove, if there is none, print a warning
                verbose("  - " + repo + " is not tagged with " + tag + " anymore")
            except:
                message = notag_warning % (repo,tag)
                warning_handler(message)
        else:
            message = norepo_warning % (repo)
            warning_handler(message)

def list_repo(name, path, tags):
    output = "Name: %s Tags:" % (name)
    print output,
    if len(tags) > 0:
        for tag in tags:
            print tag,
    print
    path = "Path: %s\n" % (path)
    print path

# list the name path and tags of none, some or all repos
# TIPP: send this to a pager, ie: vimpager
def list_repos(search_me):
    global repos_dict

    if len(search_me) > 0:
        for search in search_me:
            if search in repos_dict:
                name = search
                path = repos_dict[search]["path"]
                tags = repos_dict[search]["tags"]
                list_repo(name, path, tags)
    else:
        for repo in repos_dict:
            path = repos_dict[repo]["path"]
            tags = repos_dict[repo]["tags"]
            list_repo(repo, path, tags)


def cmd_parse(cmd, you_called):

    # check for additional stuff to execute

    interim=[]
    sub = []

    for do in cmd:
        if do == "-ea" or do == "--execappend":
            if len(sub) == 0:
                message = missingarg_error % (you_called, 'CMD')
                error_handler(message)
            interim.append(sub)
            sub = []
        else:
            sub.append(do)

    interim.append(sub)

    # add quotes to formerly quoted args:

    for cmd in interim:
        for do in cmd:
            if re.search(r" ", do) and not re.match(r"(^\".*\"$)|(^\'.*\'$)", do):
                new = "\"%s\"" % (do)
                cmd[cmd.index(do)] = new
        cmd.insert(0, dvcs_name)

    return(interim)


def execute_cmd(cmd, repo_path):
    if not os.path.exists(repo_path):
        message=nodir_warning % (repo_path)
        warning_handler(message)
    else:
        try:
            os.chdir(repo_path)
        except:
            message=chdir_error % (repo_path)
            error_handler(message)
        for do in cmd:
            try:
                status = subprocess.check_output(do, shell=False)
            except:
                do = ' '.join(do)
                message = git_error % (do, return_value)
                error_handler(message)
            done = ' '.join(do)
            message = "  - Executed %s in %s" % (done, repo_path)
            verbose(message)
            output_handler(status)


# execute the action defined by rest for all repos
def action(cmd, tag):
    global repos_dict

    for repo in repos_dict:
        repo_path = repos_dict[repo]["path"]
        if tag:
            try:
                repos_dict[repo]["tags"].index(tag)
                execute_cmd(cmd, repo_path)
            except:
                pass
        else:
            execute_cmd(cmd, repo_path)
    exit_handler()


def check_lastarg(index, you_called):
    if len(sys.argv) > index:
        rest = ' '.join(sys.argv[index:]) # inner slice, then join = rest.
        message = notlastarg_error % (you_called, rest)
        error_handler(message)


def check_assignnext(index, you_called, missing):
    try:
        tag = sys.argv[index]
    except:
        message = missingarg_error % (you_called, missing)
        error_handler(message)
    return tag


def check_assignrest(index, you_called, missing):
    rest = list(sys.argv[index:])
    if len(rest) == 0:
        message = missingarg_error % (you_called, missing)
        error_handler(message)
    return rest


# parse cli-args
def parse_args():
    global repos_dict
    global arg_nohook
    global arg_verbose
    global arg_quiet
    global arg_force
    global arg_git
    global arg_short
    global home_dir

    # removing the script name or similar stuff
    sys.argv.pop(0)

    # check if there is something else
    if len(sys.argv) == 0:
        error_handler(emptyarg_error)

    # now set options, compare with the usage method
    # every argument finishes with calling:
    # - continue, if it is a simple argument
    # - exit_handler, if it does nothing else
    # - write_json, if it writes stuff
    # - action, if it executes stuff

    for arg in sys.argv:

        index = sys.argv.index(arg)
        index_one = index + 1
        index_two = index_one + 1

        if arg == "-i" or arg == "--init":
            you_called = '-i or --init'
            check_lastarg(index_one, you_called)
            repos_dict = {}
            pre_init(repo_file)
            init(home_dir, None)
            write_json()

        elif arg == "-h" or arg == "--help":
            usage()
            exit_handler()
        elif arg == "-f" or arg == "--force":
            arg_force = True
            continue
        elif arg == "-n" or arg == "--nohook":
            arg_nohook = True
            continue
        elif arg == "-v" or arg == "--verbose":
            arg_verbose = True
            continue
        elif arg == "-q" or arg == "--quiet":
            arg_quiet = True
            continue
        elif arg == "-g" or arg == "--git":
            arg_git = True
            continue
        elif arg == "-s" or arg == "--short":
            if arg_short == False:
                arg_short == True
            else:
                arg_short == False
            continue

        # repos are needed now and this file should exist:
        repos_dict = read_repos()

        if arg == "-et" or arg == "--exectag":
            you_called = '-et or --exectag'
            tag = check_assignnext(index_one, you_called, 'TAG')
            tags = get_tags()
            try:
                tags.index(tag)
            except:
                tags = ' '.join(tags)
                message = notag_error % (tag, tags)
                error_handler(message)
            cmd = check_assignrest(index_two, you_called, 'CMD')
            cmd = cmd_parse(cmd, you_called)
            action(cmd, tag)

        elif arg == "-e" or arg == "--exec":
            you_called = "-e --exec"
            cmd = check_assignrest(index_one, you_called, 'CMD')
            cmd = cmd_parse(cmd, you_called)
            action(cmd, None)

        elif arg == "-a" or arg == "--addtag":
            you_called = '-a --addtag'
            tag = check_assignnext(index_one, you_called, 'TAG')
            repos = check_assignrest(index_two, you_called, 'REPOS')
            add_tag(tag, repos)
            write_json()

        elif arg == "-d" or arg == "--deltag":
            you_called = '-d --deltag'
            tag = check_assignnext(index_one, you_called, 'TAG')
            repos = check_assignrest(index_two, you_called, 'REPOS')
            del_tag(tag, repos)
            write_json()

        elif arg == "-l" or arg == "--listtags":
            list_tags()
            exit_handler()

        elif arg == "-c" or arg == "--clean":
            clean_repos()
            write_json()

        elif arg == "-ar" or arg == "--addrepos":
            you_called = '-ar --addrepos'
            repos = check_assignrest(index_one, you_called, 'REPOS')
            repos = ' '.join(repos)
            repos = re.sub(r"\s*,\s+", ",", repos)
            repos = re.sub(r"\s+", " ", repos)
            repos = repos.split(',')
            repolist = []
            for repo in repos:
                interim = repo.split(' ')
                repolist.append(interim)
            add_repos(repolist)
            write_json()

        elif arg == "-dr" or arg == "--delrepos":
            you_called = '-dr --delrepos'
            repos = check_assignrest(index_one, you_called, 'REPOS')
            del_repos(repos)
            write_json()

        elif arg == "-ad" or arg == "--adddir":
            tags = list(sys.argv[index_one:])
            dirname = os.getcwd()
            init(dirname, tags)
            write_json()

        elif arg == "-lr" or arg == "--listrepos":
            repo = list(sys.argv[index_one:])
            list_repos(repo)
            exit_handler()

        else:
            message = noopt_error % (arg)
            error_handler(message)

# helper function, returns a list of the currently used tags
def get_tags():
    global repos_dict

    tags = {}
    for repo in repos_dict:
        for tag in repos_dict[repo]["tags"]:
            tags[tag] = None
    return list(tags)


def clean_repos():
    global repos_dict
    interim = []

    for repo in repos_dict:
        repo_path = repos_dict[repo]["path"]
        if not os.path.exists(repo_path):
            interim.append(repo)

    del_repos(interim)

def strip_slash(string):
    result = re.sub(r"/$",'',string)
    return result

# list all tags, so you can use the right one
def list_tags():
    tags = get_tags()
    print "Tags:",
    for tag in tags:
        print tag,
    print


# add one or more repos to the list
def add_repos(repos):
    global repos_dict
    global arg_force

    # parse cli subargs:
    for newrepo in repos:
        try:
            repo_name = strip_slash(newrepo[0])
            if len(repo_name) < 1:
                raise Exception()
        except:
            message = addrepo_error % ('name')
            error_handler(message)
        try:
            repo_path = newrepo[1]
            if len(repo_path) < 1:
                raise Exception()
        except:
            message = addrepo_error % ('path')
            error_handler(message)
        if len(newrepo) > 2:
            repo_tags = newrepo[2:]
        else: repo_tags = None

        # perform some checks:
        if not os.path.exists(repo_path):
            message = nopath_error % (repo_path)
            error_handler(message)

        if not re.match("/$", repo_path):
            repo_path = repo_path + "/"

        if not os.path.exists(repo_path + dvcs_dir):
            message = norepo_error % (repo_path)
            error_handler(message)

        # get the absolute path if ~/ was used. Else: error.
        repo_path = re.sub(r"^~", home_dir, repo_path)

        if re.search(r"^[^\/]|\/\.\/|\.\.\/", repo_path):
            # must start with a slash:
            # ^[^\/]
            #
            # dot between slashes is forbidden:
            # \/\.\/
            #
            # two consecutive dots before a slash are forbidden:
            # \.\.\/
            #
            message = relpath_error % (repo_path)
            error_handler(message)

        # and finally add the new repo:
        if repo_name in repos_dict:
            message = exists_warning % (repo_name)
            warning_handler(message)
            if arg_force == True:
               add_repo(repo_name, repo_path, repo_tags)
        else: add_repo(repo_name, repo_path, repo_tags)


# delete one or more repos from the list
def del_repos(repos):
    global repos_dict

    interim=[]
    for repo in repos:
        if repo in repos_dict:
            interim.append(repo)
        else:
            message = nodel_warning % (repo)
            warning_handler(message)

    if len(interim) > 0:
        for i in interim:
            try:
                del repos_dict[i]
                message = "  - removing %s " % (i)
                verbose(message)
            except:
                message = cantdel_warning % (i)
                warning_handler(message)

parse_args()
