#!/usr/bin/python

import re
import socket
import sys
import common

RPC_BACKEND = re.compile('^\s*rpc_backend')
DEFAULT = re.compile('^\s*\[DEFAULT\]\s*$')

IGNORE=['debug', 'rpc_backend', 'rpc_zmq_matchmaker', 'rpc_zmq_host', 'default_log_levels']


with open(sys.argv[1], 'r') as fl:
    content = fl.readlines()

newcontent = []
time_to_put_config = False
for line in content:
    ignore = False
    for prefix in IGNORE:
        if line.startswith(prefix):
            ignore = True

    if ignore:
        continue

    if time_to_put_config:
        time_to_put_config = False

        newcontent.append('debug = True\n')
        newcontent.append('default_log_levels=amqp=WARN,amqplib=WARN,boto=WARN,iso8601=WARN,keystonemiddleware=WARN,oslo.messaging=DEBUG,oslo_messaging=DEBUG,qpid=WARN,requests.packages.urllib3.connectionpool=WARN,requests.packages.urllib3.util.retry=WARN,routes.middleware=WARN,sqlalchemy=WARN,stevedore=WARN,suds=INFO,taskflow=WARN,urllib3.connectionpool=WARN,urllib3.util.retry=WARN,websocket=WARN\n')
        newcontent.append('rpc_backend = zmq\n')
        newcontent.append('rpc_zmq_matchmaker = redis\n')
        newcontent.append('rpc_zmq_host = %s\n' % socket.gethostname())

    if RPC_BACKEND.match(line):
        continue

    if DEFAULT.match(line):
        time_to_put_config = True

    newcontent.append(line)

newcontent.append('[matchmaker_redis]\n')
newcontent.append('sentinel_hosts=%s\n' % ",".join(common.SENTINEL_HOSTS))

with open(sys.argv[1], 'w') as fl:
    fl.write(''.join(newcontent))
