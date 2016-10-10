#!/usr/bin/python

import argparse
import os
import re
import subprocess


REDIS_HOST = ''

RPC_BACKEND = re.compile('^\s*rpc_backend')
DEFAULT = re.compile('^\s*\[DEFAULT\]\s*$')
REDIS_SECTION = re.compile('^\s*\[matchmaker_redis\]\s*$')
ZMQ_SECTION = re.compile('^\s*\[oslo_messaging_zmq\]\s*$')

IGNORE = ['debug', 'rpc_backend', 'rpc_zmq_matchmaker', 'rpc_zmq_host',
          'default_log_levels', 'sentinel_hosts', 'use_router_proxy',
          'rpc_use_acks', 'host']

FRONTEND_PORT = 50001
BACKEND_PORT = 50002
PUBLISHER_PORT = 50003


def get_command_output(cmd):
    print 'Executing cmd: %s' % cmd
    pp = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE)
    outp, err = pp.communicate()

    if pp.returncode != 0:
        print ('RuntimeError: Process returned non-zero code %i' % pp.returncode)

    return outp.strip()


def generate_proxy_conf(use_pub_sub):
    print get_command_output("rm -rf /etc/zmq-proxy/")
    print get_command_output("mkdir /etc/zmq-proxy/")
    with open('/etc/zmq-proxy/zmq.conf', 'w+') as conf_f:
        conf_f.write("[oslo_messaging_zmq]\n"
                     "rpc_zmq_host=%s\n"
                     "use_pub_sub=%s\n"
                     "[matchmaker_redis]\n"
                     "host=%s" % (get_command_output("hostname"),
                                  "true" if use_pub_sub else "false",
                                  get_managable_ip_from_node(REDIS_HOST)))


def start_proxy(debug, use_pub_sub, double_router):
    generate_proxy_conf(use_pub_sub)
    print get_command_output("rm -rf /var/log/zmq-proxy.log")
    print get_command_output("nohup /tmp/venv/bin/python /tmp/oslo.messaging/oslo_messaging/_cmd/zmq_proxy.py %(debug)s "
                             "--frontend-port %(fe)s %(backend_port)s --publisher-port %(pub)s "
                             "--config-file=/etc/zmq-proxy/zmq.conf "
                             "> /var/log/zmq-proxy.log 2>&1 < /var/log/zmq-proxy.log &" %
                             {"debug": "--debug True" if debug else "",
                              "fe": FRONTEND_PORT,
                              "pub": PUBLISHER_PORT,
                              "backend_port": "--backend-port %s" % BACKEND_PORT if double_router else ""})


def kill_proxy():
    p_ids = get_command_output("ps aux | grep zm[q] | awk '{ print $2 }'").split('\n')
    for pid in p_ids:
        get_command_output("kill -9 %s" % pid)


def get_managable_ip_from_node(node):
    return get_command_output("host %s" % node).split(' ')[-1]


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
            replacement = 'bind 127.0.0.1 ' + get_managable_ip_from_node(REDIS_HOST)
            print line + '->' + replacement + '\n'
            newcontent.append(replacement)
        else:
            newcontent.append(line)

    with open(file_name, 'w') as fl:
        fl.write(''.join(newcontent))


def restore_backup():
    file_name = args.file_name
    backup_file_name = file_name+".backup"
    if not os.path.isfile(backup_file_name):
        raise RuntimeWarning("No backup found for %s. Operation is skipped." % file_name)

    if os.path.isfile(file_name):
        print get_command_output("rm -rf %s" % file_name)

    print get_command_output("mv %s %s" % (backup_file_name, file_name))


def hack_services(debug, use_acks, use_router_proxy):

    file_name = args.file_name
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

            if debug:
                newcontent.append('debug = True\n')

            newcontent.append('default_log_levels=amqp=WARN,amqplib=WARN,boto=WARN,iso8601=WARN,keystonemiddleware=WARN,oslo.messaging=%(debug)s,oslo_messaging=%(debug)s,qpid=WARN,requests.packages.urllib3.connectionpool=WARN,requests.packages.urllib3.util.retry=WARN,routes.middleware=WARN,sqlalchemy=WARN,stevedore=WARN,suds=INFO,taskflow=WARN,urllib3.connectionpool=WARN,urllib3.util.retry=WARN,websocket=WARN\n' %
                              {"debug": "DEBUG" if debug else "WARN"})

            newcontent.append('rpc_backend = zmq\n')

        if RPC_BACKEND.match(line) or REDIS_SECTION.match(line) or ZMQ_SECTION.match(line):
            continue

        if DEFAULT.match(line):
            time_to_put_config = True

        newcontent.append(line)

    newcontent.append('[oslo_messaging_zmq]\n')
    newcontent.append('rpc_zmq_host = %s\n' % get_command_output("hostname"))

    if not use_router_proxy:
        newcontent.append('zmq_linger = 20\n')

    newcontent.append('use_router_proxy = %s\n' % ("true" if use_router_proxy else "false"))
    newcontent.append('rpc_use_acks = %s\n' % ("true" if use_acks else "false"))
    newcontent.append('rpc_zmq_matchmaker = redis\n')
    newcontent.append('[matchmaker_redis]\n')
    newcontent.append('host=%s\n' % REDIS_HOST)

    with open(file_name, 'w') as fl:
        fl.write(''.join(newcontent))


parser = argparse.ArgumentParser()
parser.add_argument('--generate', dest='generate', action='store_true')
parser.add_argument('--start-proxy', dest='start_proxy', action='store_true')
parser.add_argument('--double-proxy', dest='double_proxy', action='store_true')
parser.add_argument('--kill-proxy', dest='kill_proxy', action='store_true')
parser.add_argument('--debug', dest='debug', action='store_true')
parser.add_argument('--use-acks', dest='use_acks', action='store_true')
parser.add_argument('--hack', dest='hack', action='store_true')
parser.add_argument('--restore-backup', dest='restore_backup', action='store_true')
parser.add_argument('--hack-redis', dest='hack_redis', action='store_true')
parser.add_argument('--use-pub-sub', dest='use_pub_sub', action='store_true')
parser.add_argument('--use-router-proxy', dest='use_router_proxy', action='store_true')
parser.add_argument('--file', dest='file_name', type=str)
parser.add_argument('--redis-host', dest='redis_host', type=str)
args = parser.parse_args()


if __name__ == "__main__":
    global REDIS_HOST
    try:
        REDIS_HOST = args.redis_host

        if args.generate:
            use_pub_sub = True if args.use_pub_sub else False
            generate_proxy_conf(use_pub_sub)
        elif args.hack:
            hack_services(args.debug, args.use_acks, args.use_router_proxy)
        elif args.restore_backup:
            restore_backup()
        elif args.hack_redis:
            hack_redis()
        elif args.kill_proxy:
            kill_proxy()
        elif args.start_proxy:
            start_proxy(args.debug, args.use_pub_sub, args.double_proxy)

    except RuntimeError as e:
        print(str(e))
