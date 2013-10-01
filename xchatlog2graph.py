#!/usr/bin/env python
'''
Read in a chat log and export a graph showing who highlights whom.
'''

import re
import time
import datetime
import pygraphviz as pgv

class Log(object):

    log_line_re = re.compile('^((\w{3}) (\d{2}) (\d{2}):(\d{2}):(\d{2})) (\S*)\s(.*)$')

    def __init__(self, stamp):
        self.start = stamp
        self.entries = []
        return

    def __str__(self):
        ret = []
        for e in self.entries:
            s = '|%s|%s|%s|%s' % (str(e[0]), e[1], e[2], e[3])
            #print 'Log: "%s"' % s
            ret.append(s)
        return '\n'.join(ret)

    is_known_as_re = re.compile('^(\S+) is now known as (\S+)$')
    am_known_as_re = re.compile('^(You) are now known as (\S+)$')
    emote_re = re.compile('^(\S+) (.*)&')
    quit_re = re.compile('^(\S+) has quit \((.*)\)$')
    join_re = re.compile('^(\S+) \((\S+)\) has joined #\S+$')

    def special_parse(self, msg): 
        'Parse "*" message'
        res = [
            ('R',Log.is_known_as_re),
            ('R',Log.am_known_as_re),
            ('E',Log.emote_re),
            ('Q',Log.quit_re),
            ('J',Log.join_re),
            ]

        for code, search in res:
            answer = search.findall(msg)
            if not answer: continue
            answer = answer[0]
            return (code, answer[0], answer[1])
        return None

    def normal_or_special(self, first, rest):
        'Return tuple (code, nick, payload)'

        if not first: return None
        if first == 'Traceback': return None
        
        if first[0] == '<' and first[-1] == '>': # nick
            nick = first[1:-1]
            return ('M', nick, rest)

        if first == '*':       # special
            return self.special_parse(rest)
            
        return None

    def add_line(self, line):
        found = Log.log_line_re.findall(line)
        if not found: return
        found = found[0]
        ts = time.strptime(str(self.start.year) + ' ' + found[0], 
                           "%Y %b %d %H:%M:%S")
        dt = datetime.datetime(*ts[:6])
        payload = self.normal_or_special(found[6],found[7])
        if not payload:
            #print 'Skipping: "%s"' % line
            return
        ret = tuple([dt] + list(payload))
        self.entries.append(ret)
        return ret
    pass
        
class LogFile(object):

    begin_log_re = re.compile('^\*\*\*\* BEGIN LOGGING AT (\w{3}) ((\w{3}) (\d{2}) (\d{2}):(\d{2}):(\d{2})) (\d{4})')

    def __init__(self, logfilename):
        self.logs = []     
        fp = open(logfilename,'r')
        for line in fp.readlines():
            self.add_line(line)
            continue
        return

    def add_line(self, line):
        line = line.strip()
        if not line: return
        start = LogFile.begin_log_re.findall(line)
        if start:
            ts = time.strptime(start[0][1], "%b %d %H:%M:%S")
            dt = datetime.datetime(*ts[:6])
            log = Log(dt)
            self.logs.append(log)
            return
        log = self.logs[-1]
        log.add_line(line)
        return

    def __str__(self):
        s = []
        for l in self.logs:
            s.append(str(l))
        return '\n'.join(s)

    pass

def nicks(lf):
    nicks = {}
    for log in lf.logs:
        for entry in log.entries:
            if entry[1] != 'M': continue
            nick = entry[2]
            if not nicks.has_key(nick):
                nicks[nick] = 1
                continue
            nicks[nick] += 1
            continue
        continue
    return nicks


if '__main__' == __name__:
    
    import sys
    logfile = sys.argv[1]
    lf = LogFile(logfile)
    #s = str(lf)
    #print s

    counts = [(c,n) for n,c in nicks(lf).iteritems()]
    counts.sort()
    for c,n in sorted(counts):
        print '%s: %d' % (n,c)
        continue
