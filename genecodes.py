#!/usr/bin/env python
# -*- coding: utf-8; -*-

# Note: This file was copied from Python 3 evdev by Georgi Valkov and trivially
# modified. The only difference is that his version creates a C Python
# extension, while ours creates a small pickled database suitable for
# comrehension by QKOS. This is used to list all the possible keys in the system.
# 
# Thank you Mr. Valkov for your effort

'''
Generate a Python extension module that exports macros from
/usr/include/linux/input.h
'''

import os, sys, re, pickle

header = '/usr/include/linux/input.h' if len(sys.argv) == 1 else sys.argv[1]
regex = r'#define +((?:KEY|ABS|REL|SW|MSC|LED|BTN|REP|SND|ID|EV|BUS|SYN|FF)_\w+)'
regex = re.compile(regex)

if not os.path.exists(header):
    print('no such file: %s' % header)
    sys.exit(1)

def getmacros():
    for line in open(header):
        macro = regex.search(line)
        if macro:
            yield macro.group(1)

uname = list(os.uname()); del uname[1]
uname = ' '.join(uname)
macros = [m for m in getmacros()]

with open("ecodes.p", "wb") as db:
    pickle.dump(macros, db)
    print("Wrote out {0} ecodes to ecodes.p".format(len(macros)))
