#!/usr/bin/python

import re
import socket
import sys

RPC_BACKEND = re.compile('^\s*rpc_backend')
DEFAULT = re.compile('^\s*\[DEFAULT\]\s*$')

with open(sys.argv[1], 'r') as fl:
    content = fl.readlines()

newcontent = []
time_to_put_config = False
for line in content:
    if line == 'rpc_backend = zmq\n':
        # we already hacked the file
        sys.exit(0)
    if time_to_put_config:
        time_to_put_config = False
        newcontent.append('rpc_backend = zmq\n')
        newcontent.append('rpc_zmq_matchmaker = redis\n')
        newcontent.append('rpc_zmq_host = %s\n' % socket.gethostname())

    if RPC_BACKEND.match(line):
        continue

    if DEFAULT.match(line):
        time_to_put_config = True

    newcontent.append(line)

newcontent.append('[matchmaker_redis]\n')
newcontent.append('sentinel_hosts=node-1:26379,node-2:26379,node-3:26379\n')

with open(sys.argv[1], 'w') as fl:
    fl.write(''.join(newcontent))
