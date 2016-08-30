#!/usr/bin/python

import os
import re
import sys
import subprocess


REDIS_HOST = sys.argv[2]

RPC_BACKEND = re.compile('^\s*rpc_backend')
DEFAULT = re.compile('^\s*\[DEFAULT\]\s*$')
REDIS_SECTION = re.compile('^\s*\[matchmaker_redis\]\s*$')
ZMQ_SECTION = re.compile('^\s*\[oslo_messaging_zmq\]\s*$')

IGNORE=['debug', 'rpc_backend', 'rpc_zmq_matchmaker', 'rpc_zmq_host',
        'default_log_levels', 'sentinel_hosts']

def get_command_output(cmd):
    print 'Executing cmd: %s' % cmd
    pp = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE)
    outp, err = pp.communicate()

    if pp.returncode != 0:
        print ('RuntimeError: Process returned non-zero code %i' % pp.returncode)

    return outp.strip()


def generate_proxy_conf(use_pub_sub):
    get_command_output("mkdir /etc/zmq-proxy/")
    with open('/etc/zmq-proxy/zmq.conf', 'w+') as conf_f:
        conf_f.write("[oslo_messaging_zmq]\n"
                     "rpc_zmq_host=%s\n"
                     "use_pub_sub=%s\n"
                     "[matchmaker_redis]\n"
                     "host=%s" % (get_command_output("hostname"),
                                  "true" if use_pub_sub else "false",
                                  REDIS_HOST))


def get_managable_ip_from_node(node):
    return get_command_output("ssh %s 'hostname'" % node)


def hack_redis():
    file_name = '/etc/redis/redis.conf'
    print "Rewriting redis config %s" % file_name
    with open(file_name, 'r') as fl:
        content = fl.readlines()

    if not os.path.isfile(file_name+".backup"):
        with open(file_name+".backup", 'w') as fl:
            fl.write(''.join(content))

    newcontent = []
    for line in content:
        if line.startswith('bind 127.0.0.1'):
            replacement = 'bind 127.0.0.1 ' + REDIS_HOST
            print line + '->' + replacement + '\n'
            newcontent.append(replacement)
        else:
            newcontent.append(line)

    with open(file_name, 'w') as fl:
        fl.write(''.join(newcontent))


def hack_services():

    file_name = sys.argv[3]
    with open(file_name, 'r') as fl:
        content = fl.readlines()

    if not os.path.isfile(file_name+".backup"):
        with open(file_name+".backup", 'w') as fl:
            fl.write(''.join(content))

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

            # newcontent.append('debug = True\n')
            newcontent.append('default_log_levels=amqp=WARN,amqplib=WARN,boto=WARN,iso8601=WARN,keystonemiddleware=WARN,oslo.messaging=WARN,oslo_messaging=WARN,qpid=WARN,requests.packages.urllib3.connectionpool=WARN,requests.packages.urllib3.util.retry=WARN,routes.middleware=WARN,sqlalchemy=WARN,stevedore=WARN,suds=INFO,taskflow=WARN,urllib3.connectionpool=WARN,urllib3.util.retry=WARN,websocket=WARN\n')
            newcontent.append('rpc_backend = zmq\n')

        if RPC_BACKEND.match(line) or REDIS_SECTION.match(line) or ZMQ_SECTION.match(line):
            continue

        if DEFAULT.match(line):
            time_to_put_config = True

        newcontent.append(line)

    newcontent.append('[oslo_messaging_zmq]\n')
    newcontent.append('rpc_zmq_host = %s\n' % get_command_output("hostname"))
    newcontent.append('use_router_proxy = true\n')
    newcontent.append('rpc_zmq_matchmaker = redis\n')
    newcontent.append('[matchmaker_redis]\n')
    newcontent.append('host=%s\n' % REDIS_HOST)

    with open(file_name, 'w') as fl:
        fl.write(''.join(newcontent))


if __name__=="__main__":
    try:
        if sys.argv[1] == "generate":
            use_pub_sub = True if sys.argv[3] == '--use-pub-sub' else False
            generate_proxy_conf(use_pub_sub)
        elif sys.argv[1] == "hack":
            hack_services()
        elif sys.argv[1] == "hack_redis":
            hack_redis()
    except RuntimeError as e:
        print(str(e))
