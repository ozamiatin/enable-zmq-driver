#!/usr/bin/python

import argparse
from hack_config_with_zmq import REDIS_HOST
from hack_config_with_zmq import get_command_output


CONTROLLER_PROCS = [
    'nova-api',
    'nova-cert',
    'nova-conductor',
    'nova-consoleauth',
    'nova-novncproxy',
    'nova-scheduler',

    # All neutron services listed in PCS_RESOURCES
    # 'neutron-dhcp-agent',
    # 'neutron-l3-agent',
    # 'neutron-metadata-agent',
    # 'neutron-ns-metadata-proxy',
    # 'neutron-openvswitch-agent',
     'neutron-server',

    'cinder-api',
    'cinder-backup',
    'cinder-scheduler',
    'cinder-volume',

    'keystone',

    'glance-api',
    'glance-registry',

    'heat-api',
    'heat-api-cfn',
    'heat-api-cloudwatch',
    'heat-engine',
]

COMPUTE_PROCS = [
    'neutron-metadata-agent',
    'nova-compute',
    'neutron-openvswitch-agent',
    'neutron-l3-agent'
]

PCS_RESOURCES = [
    'neutron-openvswitch-agent',
    'neutron-l3-agent',
    'neutron-metadata-agent',
    'neutron-dhcp-agent',
    'p_heat-engine'
]

CONTROLLER_CONFIGS = [
    '/etc/neutron/neutron.conf',
    '/etc/keystone/keystone.conf',
    '/etc/cinder/cinder.conf',
    '/etc/nova/nova.conf',
#    '/etc/murano/murano.conf',
    '/etc/glance/glance-registry.conf',
    '/etc/glance/glance-api.conf',
    '/etc/heat/heat.conf',
]

COMPUTE_CONFIGS = [
    '/etc/nova/nova.conf',
    '/etc/neutron/neutron.conf',
]

CONTROLLER_LOGS = [
    '/var/log/nova*.log*',
    '/var/log/nova/*.log*',
    '/var/log/neutron*.log*',
    '/var/log/neutron/*.log*',
    '/var/log/cinder*.log*',
    '/var/log/cinder/*.log*',
    '/var/log/glance*.log*',
    '/var/log/glance/*.log*',
    '/var/log/heat*.log*',
    '/var/log/heat/*.log*',
#    '/var/log/zmq-proxy.log'
]

COMPUTE_LOGS = [
    '/var/log/nova*.log*',
    '/var/log/nova/*.log*',
    '/var/log/neutron*.log*',
    '/var/log/neutron/*.log*'
]


def get_managable_ip_from_node(node):
    return get_command_output("ssh %s 'hostname'" % node)


def elaborate_processes_on_nodes(nodes, processes, action='restart'):
    for node in sorted(nodes):
        if not node:
            continue

        print '\nElaborating services on node %s' % node

        for proc in processes:
            if args.dry_run:
                print "ssh %s 'service %s %s'" % (node, proc, action)
            else:
                print get_command_output("ssh %s 'service %s %s'" % (node, proc, action))


def elaborate_resources(node, resources, action='restart'):
    print '\nElaborating resources on controller %s' % node
    for res in resources:
        print 'Elaborating resource %s' % res
        if not args.dry_run:
            print get_command_output("ssh %s 'crm resource %s %s'" % (node, action, res))


def clear_logs_on_nodes(nodes, logs):
    for node in nodes:
        print '\nClearing logs on %s' % node

        for log_pattern in logs:
            print 'Removing %s' % log_pattern
            if not args.dry_run:
                print get_command_output("ssh %s 'rm %s'" % (node, log_pattern))


def hack_configs_on_nodes(nodes, configs):
    for node in nodes:
        print '\nHacking configs on %s' % node
        print get_command_output('scp hack_config_with_zmq.py %s:/tmp' % node)

        for conf_file in configs:
            print 'Editing %s' % conf_file
            if not args.dry_run:
                print get_command_output("ssh %s 'rm /tmp/hack_config_with_zmq.pyc'" % node)
                print get_command_output("ssh %s '/tmp/hack_config_with_zmq.py %s > /tmp/hack_config_with_zmq.log 2>&1 < /tmp/hack_config_with_zmq.log  &'" % (node, conf_file))


def start_proxy_on_nodes(nodes):

    for node in nodes:
        print get_managable_ip_from_node(node)
        if not args.dry_run:
            with open('./zmq-proxy.conf', 'w') as conf_f:
                conf_f.write("[oslo_messaging_zmq]\n"
                             "rpc_zmq_host=%s\n"
                             "[matchmaker_redis]\n"
                             "host=%s" % (get_managable_ip_from_node(node), REDIS_HOST))
            print '\nStarting oslo-messaging-zmq-proxy on %s' % node
            print get_command_output('scp zmq-proxy.conf %s:/etc' % node)
            print ("ssh %s 'nohup oslo-messaging-zmq-proxy --debug True "
                                     "--config-file=/etc/zmq-proxy.conf > "
                                     "/var/log/zmq-proxy.log 2>&1 < "
                   "/var/log/zmq-proxy.log  &'" % node)
            print get_command_output("ssh %s 'nohup oslo-messaging-zmq-proxy --debug True --frontend-port 50001 --backend-port 50002 --publisher-port 50003 --config-file=/etc/zmq-proxy.conf > /var/log/zmq-proxy.log 2>&1 < /var/log/zmq-proxy.log  &'" % node)
        else:
            print '\nStarting oslo-messaging-zmq-proxy on %s' % node


def install_oslo_messaging_package(package_url, package_name, nodes):

    for node in nodes:
        print '\nInstalling %s on %s' % (package_url, node)
        if not args.dry_run:
            print get_command_output("ssh %s 'mkdir /tmp/zmq-package/'" % node)
            print get_command_output("ssh %s 'wget -N -O /tmp/zmq-package/%s "
                                     "%s'" % (node, package_name, package_url))
            print get_command_output("ssh %s 'dpkg -i /tmp/zmq-package/%s'" % (node, package_name))


def apt_install_package(nodes, package_name):
    for node in nodes:
        print '\nInstalling %s on %s' % (package_name, node)
        print get_command_output("ssh %s 'apt-get install %s'" % (node, package_name))


def detect_roles():
    global controllers, computes
    fuel_columns_count = int(get_command_output("fuel nodes 2>&1 | grep controller | awk '{ print NF }'").split('\n')[0])
    assert fuel_columns_count == EXPECTED_NUMBER_OF_FUEL_COLUMNS, "Columns have to match %d expected value" % EXPECTED_NUMBER_OF_FUEL_COLUMNS

    controllers = get_command_output("fuel nodes 2>&1 | grep controller | awk '{ print $9 }'").split('\n')
    computes = get_command_output("fuel nodes 2>&1 | grep compute | awk '{ print $9 }'").split('\n')

    if args.dry_run:
        controllers = controllers[:1]
        computes = computes[:2]


def firewall_ports_open(nodes, min_port, max_port):
    for node in nodes:
        get_command_output("ssh %s 'iptables -A INPUT -p tcp --match multiport --dports %d:%d -j ACCEPT'" % (node, min_port, max_port))


def restart_redis():
    elaborate_processes_on_nodes(controllers, ['redis-server'])


BROKER_EXECUTABLE_NAME = "oslo-messaging-zmq-proxy"
EXPECTED_NUMBER_OF_FUEL_COLUMNS = 18



PACKAGE_URL = "http://172.18.162.63/review/CR-19937/mos-repos/ubuntu/9.0/pool/main/p/python-oslo.messaging/python-oslo.messaging_4.6.1-3~u14.04%2bmos9_all.deb"
PACKAGE_NAME = "python-oslo.messaging_4.6.1-3~u14.04+mos9_all.deb"

PROXY_PACKAGE_URL = "http://172.18.162.63/review/CR-19937/mos-repos/ubuntu/9.0/pool/main/p/python-oslo.messaging/oslo-messaging-zmq-receiver_4.6.1-3~u14.04%2bmos9_all.deb"
PROXY_PACKAGE_NAME = "oslo-messaging-zmq-receiver_4.6.1-3~u14.04+mos9_all.deb"


parser = argparse.ArgumentParser()
parser.add_argument('--dry-run', dest='dry_run', action='store_true')
parser.add_argument('--install-packages', dest='install_packages',
                    action='store_true')
parser.add_argument('--start-proxies', dest='start_proxies',
                    action='store_true')
parser.add_argument('--restart-services', dest='restart_services',
                    action='store_true')
parser.add_argument('--stop-services', dest='stop_services',
                    action='store_true')
parser.add_argument('--start-services', dest='start_services',
                    action='store_true')
parser.add_argument('--hack-configs', dest='hack_configs',
                    action='store_true')
parser.add_argument('--clear-logs', dest='clear_logs',
                    action='store_true')
parser.add_argument('--install-pyredis', dest='install_pyredis',
                    action='store_true')

parser.add_argument('--restart-resources', dest='restart_resources',
                    action='store_true')
parser.add_argument('--restart-controller-proc', dest='restart_controller_proc',
                    action='store_true')
parser.add_argument('--restart-computes', dest='restart_computes',
                    action='store_true')
parser.add_argument('--firewall-open', dest='firewall_open',
                    action='store_true')

parser.add_argument('--deploy-redis-sentinel', dest='deploy_redis_sentinel',
                    action='store_true')
parser.add_argument('--restart-redis', dest='restart_redis',
                    action='store_true')

args = parser.parse_args()

controllers = []
computes = []


def main():

    if args.dry_run:
        print 'Performing dry run'

    detect_roles()

    print ("Detected controllers: %s" % controllers)
    print ("Detected computes: %s" % computes)

    if args.install_pyredis:
        apt_install_package(computes, "python-redis")

    if args.clear_logs:
        clear_logs_on_nodes(controllers, CONTROLLER_LOGS)
        clear_logs_on_nodes(computes, COMPUTE_LOGS)

    if args.install_packages:
        install_oslo_messaging_package(PACKAGE_URL, PACKAGE_NAME, controllers)
        install_oslo_messaging_package(PACKAGE_URL, PACKAGE_NAME, computes)
        install_oslo_messaging_package(PROXY_PACKAGE_URL, PROXY_PACKAGE_NAME, controllers)
        install_oslo_messaging_package(PROXY_PACKAGE_URL, PROXY_PACKAGE_NAME, computes)

    if args.start_proxies:
        start_proxy_on_nodes(controllers)

    if args.restart_redis:
        restart_redis()

    if args.hack_configs:
        hack_configs_on_nodes(controllers, CONTROLLER_CONFIGS)
        hack_configs_on_nodes(computes, COMPUTE_CONFIGS)

    if args.restart_services:
        elaborate_resources(controllers[0], PCS_RESOURCES, 'restart')
        elaborate_processes_on_nodes(controllers, CONTROLLER_PROCS, 'restart')
        elaborate_processes_on_nodes(computes, COMPUTE_PROCS, 'restart')
    elif args.stop_services:
        elaborate_resources(controllers[0], PCS_RESOURCES, 'stop')
        elaborate_processes_on_nodes(controllers, CONTROLLER_PROCS, 'stop')
        elaborate_processes_on_nodes(computes, COMPUTE_PROCS, 'stop')
    elif args.start_services:
        elaborate_resources(controllers[0], PCS_RESOURCES, 'start')
        elaborate_processes_on_nodes(controllers, CONTROLLER_PROCS, 'start')
        elaborate_processes_on_nodes(computes, COMPUTE_PROCS, 'start')


    if args.restart_resources:
        elaborate_resources(controllers[0], PCS_RESOURCES, 'restart')

    if args.restart_controller_proc:
        elaborate_processes_on_nodes(controllers, CONTROLLER_PROCS, 'restart')

    if args.restart_computes:
        elaborate_processes_on_nodes(computes, COMPUTE_PROCS, 'restart')

    if args.firewall_open:
        firewall_ports_open(controllers, 49152, 65535)
        firewall_ports_open(computes, 49152, 65535)

if __name__ == "__main__":
    main()
