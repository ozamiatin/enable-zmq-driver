#!/usr/bin/python

import argparse
import subprocess


CONTROLLER_PROCS = [
    'nova-api',
    'nova-cert',
    'nova-conductor',
    'nova-consoleauth',
    'nova-novncproxy',
    'nova-objectstore',
    'nova-scheduler',

    # All neutron services listed in PCS_RESOURCES
    # 'neutron-dhcp-agent',
    # 'neutron-l3-agent',
    # 'neutron-metadata-agent',
    # 'neutron-ns-metadata-proxy',
    # 'neutron-openvswitch-agent',
    # 'neutron-server',

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
    'neutron-l3-agent',
    'neutron-rootwrap'
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


def get_command_output(cmd):
    print 'Executing cmd: %s' % cmd
    pp = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE)
    outp, err = pp.communicate()

    if pp.returncode != 0:
        raise RuntimeError('Process returned non-zero code %i' % pp.returncode)

    return outp.strip()


def restart_processes_on_nodes(nodes, processes):
    for node in sorted(nodes):
        if not node:
            continue

        print '\nRestarting services on node %s' % node

        for proc in processes:
            if args.dry_run:
                print "ssh %s 'service %s restart'" % (node, proc)
            else:
                print get_command_output("ssh %s 'service %s restart'" % (node, proc))


def restart_resources(node, resources):
    print '\nRestarting resources on controller %s' % node
    for res in resources:
        print 'Restarting resource %s' % res
        if not args.dry_run:
            print get_command_output("ssh %s 'crm resource restart %s'" % (node, res))


def hack_configs_on_nodes(nodes, configs):
    for node in nodes:
        print '\nHacking configs on %s' % node
        print get_command_output('scp hack_config_with_zmq.py %s:/tmp' % node)

        for conf_file in configs:
            print 'Editing %s' % conf_file
            if not args.dry_run:
                print get_command_output("ssh %s '/tmp/hack_config_with_zmq.py %s'" % (node, conf_file))


def start_broker_on_nodes(nodes):
    for node in nodes:
        print '\nStarting oslo-messaging-zmq-proxy on %s' % node
        print get_command_output('scp zmq-proxy.conf %s:/etc' % node)
        print get_command_output("ssh %s 'nohup oslo-messaging-zmq-proxy --debug True "
                                 "--config-file=/etc/zmq-proxy.conf > /var/log/zmq-proxy.log 2>&1 < var/log/zmq-proxy.log  &'" % node)


def detect_roles():
    global controllers, computes
    fuel_columns_count = int(get_command_output("fuel nodes 2>&1 | grep controller | awk '{ print NF }'").split('\n')[0])
    assert fuel_columns_count == EXPECTED_NUMBER_OF_FUEL_COLUMNS, "Columns have to match %d expected value" % EXPECTED_NUMBER_OF_FUEL_COLUMNS

    controllers = get_command_output("fuel nodes 2>&1 | grep controller | awk '{ print $9 }'").split('\n')
    computes = get_command_output("fuel nodes 2>&1 | grep compute | awk '{ print $9 }'").split('\n')

    if args.dry_run:
        controllers = controllers[:1]
        computes = computes[:2]


def deploy_redis():
    pass


BROKER_EXECUTABLE_NAME = "oslo-messaging-zmq-proxy"
EXPECTED_NUMBER_OF_FUEL_COLUMNS = 18

parser = argparse.ArgumentParser()
parser.add_argument('--dry-run', dest='dry_run', action='store_true')
args = parser.parse_args()

controllers = []
computes = []


def main():

    if args.dry_run:
        print 'Performing dry run'

    detect_roles()

    print ("Detected controllers: %s" % controllers)
    print ("Detected computes: %s" % computes)

    hack_configs_on_nodes(controllers, CONTROLLER_CONFIGS)
    hack_configs_on_nodes(computes, COMPUTE_CONFIGS)

    start_broker_on_nodes(controllers)

    restart_resources(controllers[0], PCS_RESOURCES)

    restart_processes_on_nodes(controllers, CONTROLLER_PROCS)
    restart_processes_on_nodes(computes, COMPUTE_PROCS)

if __name__ == "__main__":
    main()
