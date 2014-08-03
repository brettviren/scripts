#!/usr/bin/env python
'''A script to automate a deluge client + deluged + btsync workflow.

This script helps to marshal torrent content from a system running
deluged on a remote system to a disk on the local system running this
script.  Another system may run the deluge client to initate a torrent
download.

On the "remote" system configure:

 - deluged to download torrent content to an "in-progress/" directory
   and to move to a "completed/" directory when done.

 - configure btsync to share this "completed/" directory.  

On the "local" system running this script:

 - configure a coresponding "completed/" directory to be btsync'ed.
   This may be a read-only share and it may exclude the use of
   .SyncArchive/ if desired.

 - select an "inbox/" directory to copy completed torrent content out
   of "completed/" when it's synced.

 - run this script periodically

This script is configured with a ~/.debt.cfg file or a ./debt.cfg
file.  Take care to choose appropriate permissions to protect your
passwords.

It should look like:

[name]
# username to connect to deluged
username = USERNAME
# password to connect to deluged
password = SECRET
# deluged host and port
host = mydelugedhost.domain.com
port = 58846
# Top directory that is btsync'ed with completed deluged download
btsync_dir = /home/media/mydelugedhost
# Non btsync directory to move completed btsync'ed torrents
inbox_dir = /home/media/inbox

Multiple "[name]" sections can be specified. 

Run the script like:

  $ dept.py name

Where "name" is that of the config section you wish to use.

When both deluged and btsync says a torrent is complete and synced
this script will copy the content to the inbox/ and then tell deluged
to remove the torrent and content.  This will trigger the local
btsync-controlled content to also be deleted.  If .SyncArchive/ is
configured for use then the content should still be found there.

This idea for this script was inspired by an Internet friend. Thanks.

'''


import os
import re
import sys
import shutil
import subprocess
from collections import namedtuple

try:                from ConfigParser import SafeConfigParser
except ImportError: from configparser import SafeConfigParser
cfg = SafeConfigParser()
cfg.read([os.path.expanduser('~/.debt.cfg'),'./debt.cfg'])

try:
    section = sys.argv[1]
except IndexError:
    section = 'cac'
params = dict(cfg.items(section))

def deluge_command(cmd, *args, **kwds):
    cmdstr = "deluge-console 'connect {host}:{port} {username} {password} ; {cmd} {args}'"
    dat = dict(params, **kwds)
    args = ' '.join(args)
    args = args.format(**dat)
    cmdstr = cmdstr.format(cmd=cmd, args=args, **dat)
    return subprocess.check_output(cmdstr, shell=True)


def XxxInfo(InfoClass, *args, **kwds):
    p = {k.lower().replace(' ','_'):v for k,v in kwds.items()}
    return InfoClass(*args, **p)
    
def TorrentInfo(*args, **kwds):
    TI = namedtuple('TorrentInfo', 
                    'files peers seed_time name state seeds tracker_status progress id size')
    kwds.setdefault('Progress',None)
    kwds.setdefault('Seeds',None)
    return XxxInfo(TI, *args, **kwds)

def FileInfo(*args, **kwds):
    FI = namedtuple('FileInfo','path size units progress priority')
    args = [a.strip() for a in args]
    return XxxInfo(FI, *args, **kwds)


file_re = re.compile('(.*) \((\d+\.\d) ([KMG]iB)\) Progress: (\d+\.\d+)% Priority: (\w+)')
def parse_info(text):
    '''Parse the text from an "info -v" command and return it as a list of
    TorrentInfo objects.
    '''
    ret = []
    cur = None
    state = None
    for iline, line in enumerate(text.split('\n')):
        line = line.strip()
        if not line:
            continue
        if line.startswith('Name:'):
            if cur:
                ret.append(TorrentInfo(**cur))
            cur = dict(Name = line.split(':',1)[1], Files=list(), Peers=list())
            state = None
            continue
        if line == '::Files':
            state = "files"
            continue
        if line == '::Peers':
            state = "peers"
            continue
        if state is None:
            key,val = line.split(':',1)
            cur[key] = val.strip()
            continue
        if state == "files":
            fi = FileInfo(*re.match(file_re, line).groups())
            cur["Files"].append(fi)
            continue
        if state == "peers":
            cur["Peers"].append(line)
            continue
        continue
    if cur:
        ret.append(TorrentInfo(**cur))
    return ret

def get_torinfo(name, torlist):
    for tor in torlist:
        if tor.name == name:
            return tor
    return None

def tor_complete_download(tor):
    for finfo in tor.files:
        if not finfo.progress.startswith('100'):
            return False
    return True

def tor_files_exist(tor, path = '.'):
    for finfo in tor.files:
        path = os.path.join(path, finfo.path)
        try:
            s = os.stat(path)
        except OSError:
            return False

def tor_deluge_status(tor):
    for finfo in tor.files:
        print '%7s%% %5s %s %s' % (finfo.progress, finfo.size, finfo.units, finfo.path)

def tor_btsync_status(tor, path='.'):
    for finfo in tor.files:
        fullpath = os.path.join(path, finfo.path)
        btsync_flag = fullpath+'.!sync'
        if os.path.exists(btsync_flag):
            print '%s [syncing]' % fullpath
            continue
        try:
            s = os.stat(fullpath)
        except OSError:
            print '%s [no stat]' % fullpath
            continue
        if s.st_size == 0:
            print '%s [zero size]' % fullpath
            continue
        print '%s [synced]' % fullpath
    return

def tor_btsynced(tor, path = '.'):
    synced = True
    for finfo in tor.files:
        fullpath = os.path.join(path, finfo.path)
        btsync_flag = fullpath+'.!sync'
        if os.path.exists(btsync_flag):
            synced = False
            continue
        try:
            s = os.stat(fullpath)
        except OSError:
            synced = False
            continue
        if s.st_size == 0:
            synced = False
            continue
    return synced

def tor_copy(tor, srcdir, dstdir):
    '''
    Copy the torrent from <srcpath> to <dstpath>.
    '''
    srcdir = os.path.realpath(srcdir)
    dstdir = os.path.realpath(dstdir)
    for finfo in tor.files:
        dst_filepath = os.path.join(dstdir, finfo.path)
        if os.path.exists(dst_filepath):
            print 'Destination file exists:', dst_filepath
            return False

        src_filepath = os.path.realpath(os.path.join(srcdir, finfo.path))
        if not os.path.exists(src_filepath):
            print 'Source file does not exist:', src_filepath
            return False

        subdir = os.path.dirname(finfo.path)
        dst_subdir = os.path.join(dstdir, subdir)

        if not os.path.exists(dst_subdir):
            os.makedirs(dst_subdir)
        shutil.copy(src_filepath, dst_subdir)
    return True

def deluge_info(**kwds):
    return deluge_command('info -v', **kwds)

def deluge_remove(ident, delete = False):
    args = ''
    if delete: args = '--remove_data'
    return deluge_command('rm %s %s' % (args, ident))

if '__main__' == __name__:
    text = deluge_info()
    #open("lastinfo.txt","w").write(text)

    btsync_dir = params['btsync_dir']
    inbox_dir = params['inbox_dir']

    pi = parse_info(text)
    for tor in pi:
        print 'Torrent: %s' % tor.name
        print 'State: "%s"' % tor.state
        if tor.state == 'Paused':
            continue

        print 'Files:', len(tor.files)

        done = tor_complete_download(tor)
        if not done:
            print 'still downloading'
            tor_deluge_status(tor)
            continue

        synced = tor_btsynced(tor, btsync_dir)
        if not synced:
            print 'still syncing'
            tor_btsync_status(tor, btsync_dir)
            continue

        okay = tor_copy(tor, btsync_dir, inbox_dir)
        print 'tor_copy returns %s' % okay
        if not okay:
            sys.exit(1)

        copied = tor_btsynced(tor, inbox_dir)

        if copied:
            print 'Now removing ', tor.name, tor.id
            print deluge_remove(tor.id, True)
