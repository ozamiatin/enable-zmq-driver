#!/usr/bin/python

import re
import sys
import subprocess


RPC_BACKEND = re.compile('^\s*rpc_backend')
DEFAULT = re.compile('^\s*\[DEFAULT\]\s*$')
REDIS_SECTION = re.compile('^\s*\[matchmaker_redis\]\s*$')
SENTINEL_LINE = re.compile('^\s*sentinel_hosts')

IGNORE=['debug', 'rpc_backend', 'rpc_zmq_matchmaker', 'rpc_zmq_host',
        'default_log_levels', 'sentinel_hosts']
SENTINEL_HOSTS = ['node-10:26379', 'node-9:26379', 'node-16:26379']



def get_command_output(cmd):
    print 'Executing cmd: %s' % cmd
    pp = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE)
    outp, err = pp.communicate()

    if pp.returncode != 0:
        print ('RuntimeError: Process returned non-zero code %i' % pp.returncode)

    return outp.strip()


def main():
    with open(sys.argv[1], 'r') as fl:
        content = fl.readlines()

    with open(sys.argv[1]+".backup", 'w') as fl:
        fl.write(''.join(content))

    print "We are here!"
    raise RuntimeWarning("We are here!")

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
            newcontent.append('rpc_zmq_host = %s\n' % get_command_output("hostname"))


        if RPC_BACKEND.match(line) or SENTINEL_LINE.match(line) or REDIS_SECTION.match(line):
            continue

        if DEFAULT.match(line):
            time_to_put_config = True

        newcontent.append(line)

    newcontent.append('[matchmaker_redis]\n')
    newcontent.append('sentinel_hosts=%s\n' % ",".join(SENTINEL_HOSTS))

    with open(sys.argv[1], 'w') as fl:
        fl.write(''.join(newcontent))


if __name__=="__MAIN__":
    main()
