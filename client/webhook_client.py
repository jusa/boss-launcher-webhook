#!/usr/bin/env python -tt
import sys
import os
import json
import subprocess
from argparse import ArgumentParser, RawDescriptionHelpFormatter

WEBHOOK = 'https://webhook.jollamobile.com/webhook/api/webhookmappings/'

def geturl(*arg):
    """ Convenience funtion to create url with trailing slash. Joins arguments together.
    """
    path = os.path.join(WEBHOOK, *arg)
    # make sure path has trailins slash
    if not path.endswith('/'):
        path = os.path.join(path, '')
    return path

def curl(*args):
    cmd = ('curl', '--location', '--write-out', '\n%{http_code}', '--header', json_header , '--show-error',  '--netrc', '--silent') + args
    try:
        output = subprocess.check_output(cmd, stderr=subprocess.STDOUT).splitlines()
        code = output[1].strip()
        response = ""
        if output[0].strip():
            response = json.loads(output[0].strip())
        #http://www.django-rest-framework.org/api-guide/status-codes/#successful-2xx
        if code in ["200", "201", "202", "203", "204", "205", "206"]:
            return response
        else:
            for key, val in response.items():
                sys.stderr.write("%s: %s\n" % (key, ",".join(val)))
            sys.exit()
    except subprocess.CalledProcessError, exc:
        for line in exc.output.splitlines()[:-1]:
            if line.strip():
                sys.stderr.write(line.strip() + '\n')
        sys.exit()

json_header = "Content-Type: application/json"
get = lambda url: curl(url)
put = lambda url: curl('--request', 'PUT', url)
delete = lambda url: curl('--request', 'DELETE', url)
post = lambda url, data: curl('--request', 'POST', '--data', json.dumps(data), url)
patch = lambda url, data: curl('--request', 'PATCH', '--data', json.dumps(data), url)

webhook_print_template = "%(id)5s | %(project)5s | %(package)5s | %(branch)5s | %(repourl)5s"

def print_hook(data, verbose=False):
    if verbose:
        print json.dumps(data, indent=4)
    else:
        print webhook_print_template % data

def get_hooks(opts):
    url = geturl()
    query_url = ""
    if opts.filter_prj:
        query_url += "project=%s&" % opts.filter_prj
    if opts.filter_pkg:
        query_url += "package=%s&" % opts.filter_pkg
    if opts.filter_user:
        query_url += "user__username=%s&" % opts.filter_user
    if opts.filter_repourl:
        query_url += "repourl=%s&" % opts.filter_repourl
    if opts.filter_build:
        # rest of the options work with lower case false/true
        # so make also this to work like that. Filtering needs
        # True / False to work
        if opts.filter_build.lower() == "false":
            build_flag = "False"
        elif opts.filter_build.lower() == "true":
            build_flag = "True"
        if build_flag:
            query_url += "build=%s&" % build_flag
    if query_url:
        url += "?" + query_url
    hooklist = get(url)
    return hooklist

def print_list(hooks, verbose=False):
    for hook in hooks:
        print_hook(hook, verbose)

def get_hook(hook_id):
    url = geturl(hook_id)
    webhook = get(url)
    detail = webhook.get('detail', None)
    if detail and detail == "Not found":
        return None
    return webhook

def create_hook(opts):
    data = {}
    for k,v in vars(opts).items():
        if 'create' in k: # strip away the creation argument
            continue
        if v:
            data[k] = v
    url = geturl()
    return post(url, data)

def patch_hook(hook_id, opts):

    data = {}
    url = geturl(str(hook_id))

    for k, v in vars(opts).items():
        if 'modify' in k or 'hook_id' in k or 'verbose' in k:
            continue
        if not v: continue
        # special case for last seen revision:
        if 'tag' in k or 'revision' in k:
            if not 'lsr' in data.keys():
                data['lsr'] = {}
            data['lsr'][k] = v
        elif v:
            data[k] = v

    return patch(url, data)

def delete_hook(hook_id):
    url = geturl(str(hook_id))
    return delete(url)

def trigger_hook(hook_id):
    url = geturl(str(hook_id))
    return put(url)

def parse_args():
    usage = """Examples of usage:

  passing -v or --verbose flag will output raw JSON

  list hooks:
    whcli --list --filter-project=foo:bar

  modify:
    whcli --id --modify --<field_to_modify> <value>
    e.g. --id 999 --modify --build false

  delete:
    whcli --id <id> --delete

  trigger webhook:
    whcli --id <id> --trigger
 """

    parser = ArgumentParser(prog="whcli", description="A command line client for WebHooks", epilog=usage, formatter_class=RawDescriptionHelpFormatter)
    parser.add_argument('--version', action='version', version='0.1')

    # main action modes: list, create, modify, delete
    actions = parser.add_argument_group("actions", "what to do with the webhooks")
    actions.add_argument('--list', action='store_true', dest='list_hooks', help="list one or more webhook mappings")
    actions.add_argument('--create', action='store_true', dest='create', help="create a new webhook mapping")
    actions.add_argument('--modify', action='store_true', dest='modify', help="modify an already existing wehook mapping")
    actions.add_argument('--delete', action='store_true', dest='delete', help="delete an already existing webhook mapping")
    actions.add_argument('--trigger', action='store_true', dest='trigger', help="Build trigger an existing webhook, can be used with --list, --create and --modify")

    # select specific hook
    select = parser.add_argument_group("selection", "how to select the webhooks")
    select.add_argument('--id', action='store', dest='hook_id', help="select a specific webhook mapping ID")
    # filter hook(s)
    select.add_argument('--filter-repourl', action='store', dest='filter_repourl', help="select webhook mappings from a certain repourl")
    select.add_argument('--filter-user', action='store', dest='filter_user', help="select webhook mappings owned by a certain user")
    select.add_argument('--filter-project', action='store', dest='filter_prj', help="select webhook mappings targeting a certain project")
    select.add_argument('--filter-package', action='store', dest='filter_pkg', help="select webhook mappings targeting a certain package")
    select.add_argument('--filter-build', action='store', dest='filter_build', help="select only build enabled webhook mappings")

    parser.add_argument('-v', '--verbose', action='store_true', dest='verbose')

    # trigger webhook(s)

    # fields available for create and modify
    fields = parser.add_argument_group("fields", "data fields used when creating or modifying webhooks")
    fields.add_argument('--repourl', action='store', dest='repourl')
    fields.add_argument('--branch', action='store', dest='branch')
    fields.add_argument('--project', action='store', dest='project')
    fields.add_argument('--package', action='store', dest='package')
    fields.add_argument('--build', action='store', dest='build')
    fields.add_argument('--notify', action='store', dest='notify')
    fields.add_argument('--token', action='store', dest='token')
    fields.add_argument('--comment', action='store', dest='comment')
    fields.add_argument('--tag', action='store', dest='tag')
    fields.add_argument('--revision', action='store', dest='revision')
    fields.add_argument('--obs', action='store', dest='obs')

    opts = parser.parse_args()
    modes = [opts.create, opts.delete, opts.modify, opts.list_hooks, opts.trigger]
    filters = [opts.filter_build, opts.filter_repourl, opts.filter_user, opts.filter_prj, opts.filter_pkg]
    any_filters = any(filters)

    # make sure one of the modes is selected
    if modes.count(True) != 1:
        parser.exit(status=2, message="Must specify one of --list, --create, --modify, --trigger or --delete, see --help for usage\n")

    if opts.delete and opts.trigger:
        parser.exit(status=2, message="Can't --delete and --trigger at the same time\n")

    if opts.create:
        if opts.hook_id or any_filters:
            parser.exit(status=2, message="Create doesn't support using --id or filters\n")
        if not all([opts.repourl, opts.branch, opts.project, opts.package, opts.obs, opts.revision]):
            parser.exit(status=2, message="Create requires at least --repourl, --branch, --project,  --package, --obs, --revision\n")
    else:
        if not opts.hook_id and not any_filters:
            parser.exit(status=2, message="Specific --id or at least one --filter option required\n")

    if opts.hook_id and any_filters:
        sys.stderr.write("WARNING: using specific webhook id %s, ignoring filters\n" % opts.hook_id)

    # all local checks done. now check if we have a valid list of hooks to process
    hooks = []
    if opts.hook_id:
        hook = get_hook(opts.hook_id)
        if hook:
            hooks.append(hook)
    elif any_filters:
        hooks = get_hooks(opts)

    if not hooks and not opts.create:
        parser.exit(status=2, message="No hooks found\n")

    if (opts.modify or opts.delete) and len(hooks) > 1:
        print_list(hooks)
        parser.exit(status=2, message="Can modify or delete only one webhook at a time\n")

    return opts, hooks

if __name__ == "__main__":
    opts, hooks = parse_args()

    if opts.list_hooks:
        print_list(hooks, opts.verbose)

    elif opts.create:
        hooks = [create_hook(opts)]
        print_list(hooks)

    elif opts.modify:
        print_hook(patch_hook(hooks[0]["id"], opts))

    elif opts.delete:
        delete_hook(hooks[0]["id"])

    if opts.trigger:
        print_list([trigger_hook(hook) for hook in hooks])
    sys.exit(0)
