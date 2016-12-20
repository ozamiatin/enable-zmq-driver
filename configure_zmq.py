#!/usr/bin/python

import argparse
import os
import subprocess


def get_command_output(cmd):
    print 'Executing cmd: %s' % cmd
    pp = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE)
    outp, err = pp.communicate()

    if pp.returncode != 0:
        print ('RuntimeError: Process returned non-zero code %i' % pp.returncode)

    return outp.strip()


REDIS_HOST = None
TRANSPORT_URL = ""
CPP_PROXY_DIR = "/tmp/zeromq-cpp-proxy"
VENV_DIR = "/tmp/venv"

FRONTEND_PORT = 30001
BACKEND_PORT = 30002
PUBLISHER_PORT = 30003
LOCAL_PUBLISHER_PORT = 60001
LOCAL_REDIS_PROXY_PORT = 40001


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
    'glance-glare',

    'heat-api',
    'heat-api-cfn',
    'heat-api-cloudwatch',
    'heat-engine',

    'swift-proxy-server',

    'swift-object-server',
    'swift-object-updater',
    'swift-object-auditor',
    'swift-object-replicator',

    'swift-container-updater',
    'swift-container-sync',
    'swift-container-server'
    'swift-container-auditor',

    'swift-account-auditor',
    'swift-account-server',
    'swift-account-replicator',
    'swift-account-reaper'
]

COMPUTE_PROCS = [
    'neutron-metadata-agent',
    'nova-compute',
    'neutron-openvswitch-agent',
    'neutron-l3-agent',
    'neutron-rootwrap',
    'cinder-backup',
    'cinder-volume'
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
    '/etc/glance/glance-glare.conf',
    '/etc/heat/heat.conf',

    '/etc/swift/proxy-server.conf'
    '/etc/swift/object-server.conf',
    '/etc/swift/container-server.conf',
    '/etc/swift/account-server.conf'
]

COMPUTE_CONFIGS = [
    '/etc/nova/nova.conf',
    '/etc/neutron/neutron.conf',
    '/etc/cinder/cinder.conf'
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




PROXY_EXECUTABLE_NAME = "oslo-messaging-zmq-proxy"
EXPECTED_NUMBER_OF_FUEL_COLUMNS = 18


PACKAGE_URL = "http://172.18.162.63/review/CR-29351/mos-repos/ubuntu/9.0/pool/main/p/python-oslo.messaging/python-oslo.messaging_4.6.1-3~u14.04%2bmos20_all.deb"
PACKAGE_NAME = "python-oslo.messaging_all.deb"


PROXY_PACKAGE_URL = "http://172.18.162.63/review/CR-29351/mos-repos/ubuntu/9.0/pool/main/p/python-oslo.messaging/oslo-messaging-zmq-receiver_4.6.1-3~u14.04%2bmos20_all.deb"
PROXY_PACKAGE_NAME = "oslo-messaging-zmq-receiver_all.deb"

OSLO_MESSAGING_GIT_REPO = "https://git.openstack.org/openstack/oslo.messaging"
OSLO_MESSAGING_GIT_BRANCH = "master"


def get_managable_ip_from_node(node):
    return get_command_output("ssh %(node)s 'host %(node)s'" % {"node": node}).split(' ')[-1]


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


def paste_remote_configurer(node):
    print get_command_output('scp remote_config.py %s:/tmp' % node)


def exec_remote_configurer(node, command="", **kwargs):
    paste_remote_configurer(node)
    file_name = kwargs.get("file")
    transport_url = TRANSPORT_URL#kwargs.get("transport_url")
    print get_command_output("ssh %(node)s 'python /tmp/remote_config.py %(cmd)s "
                             "--redis-host %(redis_host)s%(file)s%(use_pub_sub)s%(use_router_proxy)s%(debug)s%(use_acks)s%(double_proxy)s"
                             "%(transport_url)s'" %
                             {"node": node,
                              "cmd": command,
                              "redis_host": kwargs.pop("redis_host", REDIS_HOST),
                              "file": " --file %s" % file_name if file_name else "",
                              "use_pub_sub": " --use-pub-sub" if kwargs.pop("use_pub_sub", False) else "",
                              "use_router_proxy": " --use-router-proxy" if kwargs.pop("use_router_proxy", False) else "",
                              "debug": " --debug" if kwargs.pop("debug", False) else "",
                              "use_acks": " --use-acks" if kwargs.pop("use_acks", False) else "",
                              "double_proxy": " --double-proxy" if kwargs.pop("double_proxy", False) else "",
                              "transport_url": (" --transport-url %s" % transport_url) if transport_url else ""})


def hack_configs_on_nodes(nodes, configs, use_pub_sub=True, use_router_proxy=True, debug=False, use_acks=False):
    for node in nodes:
        print '\nHacking configs on %s' % node

        for conf_file in configs:
            print 'Editing %s' % conf_file
            if not args.dry_run:
                exec_remote_configurer(node, command="--hack", redis_host=REDIS_HOST, file=conf_file,
                                       use_pub_sub=use_pub_sub, use_router_proxy=use_router_proxy, debug=debug, use_acks=use_acks # , transport_url=TRANSPORT_URL
                                       )


def restore_configs(nodes, configs):
    for node in nodes:
        print '\nHacking configs on %s' % node

        for conf_file in configs:
            print 'Editing %s' % conf_file
            if not args.dry_run:
                exec_remote_configurer(node, command="--restore-backup", file=conf_file)


def generate_config_for_proxy(node, use_pub_sub):
    exec_remote_configurer(node, command="--generate", redis_host=REDIS_HOST, use_pub_sub=use_pub_sub)

def generate_config_for_redis_proxy(node, use_pub_sub):
    exec_remote_configurer(node, command="--generate-redis-proxy", redis_host=REDIS_HOST, use_pub_sub=use_pub_sub)


def start_proxy_on_nodes(nodes, use_pub_sub, debug=False, double_proxy=False):

    for node in nodes:
        print get_managable_ip_from_node(node)
        if not args.dry_run:
            generate_config_for_proxy(node, use_pub_sub)

            print get_command_output("ssh %(node)s 'nohup oslo-messaging-zmq-proxy %(debug)s "
                                     "--frontend-port %(fe)s %(backend_port)s --publisher-port %(pub)s "
                                     "--config-file=/etc/zmq-proxy/zmq.conf "
                                     "> /var/log/zmq-proxy.log 2>&1 < /var/log/zmq-proxy.log  &'" %
                                     {"node": node,
                                      "debug": "--debug" if debug else "",
                                      "fe": FRONTEND_PORT,
                                      "pub": PUBLISHER_PORT,
                                      "backend_port": "--backend-port %s" % BACKEND_PORT if double_proxy else ""})
        else:
            print '\nStarting oslo-messaging-zmq-proxy on %s' % node


def start_local_publisher_on_nodes(nodes, debug=False):
    for node in nodes:
        print get_managable_ip_from_node(node)
        if not args.dry_run:
            generate_config_for_proxy(node, True)

            print get_command_output("ssh %(node)s 'nohup oslo-messaging-zmq-proxy %(debug)s "
                                     "--local-publisher --publisher-port %(pub)s "
                                     "--config-file=/etc/zmq-proxy/zmq.conf "
                                     "> /var/log/zmq-local-proxy.log 2>&1 < /var/log/zmq-local-proxy.log  &'" %
                                     {"node": node,
                                      "debug": "--debug" if debug else "",
                                      "pub": LOCAL_PUBLISHER_PORT})
        else:
            print '\nStarting oslo-messaging-zmq-proxy on %s' % node


def start_redis_proxies_on_nodes(nodes, debug=False):
    for node in nodes:
        print get_managable_ip_from_node(node)
        if not args.dry_run:
            generate_config_for_redis_proxy(node, True)

            print get_command_output("ssh %(node)s 'nohup oslo-messaging-zmq-proxy %(debug)s "
                                     "--redis-proxy --frontend-port %(port)s "
                                     "--config-file=/etc/zmq-proxy/zmq-redis-proxy.conf "
                                     "> /var/log/zmq-redis-proxy.log 2>&1 < /var/log/zmq-redis-proxy.log  &'" %
                                     {"node": node,
                                      "debug": "--debug" if debug else "",
                                      "port": LOCAL_REDIS_PROXY_PORT})
        else:
            print '\nStarting oslo-messaging-zmq-proxy on %s' % node


def setup_venv(nodes):
    for node in nodes:
        print get_command_output("ssh %s 'apt-get update && apt-get -y install git python-pip virtualenv python-dev'" % node)
        print get_command_output("ssh %(node)s 'rm -rf /tmp/venv /tmp/oslo.messaging "
                                 "&& git clone %(repo)s /tmp/oslo.messaging "
                                 "&& cd /tmp/oslo.messaging "
                                 "&& git fetch %(repo)s %(patch)s "
                                 "&& git checkout FETCH_HEAD'" % {"node": node,
                                                                  "repo": OSLO_MESSAGING_GIT_REPO,
                                                                  "patch": OSLO_MESSAGING_GIT_BRANCH})
        print get_command_output("ssh %s 'mkdir /tmp/venv && cd /tmp/venv && virtualenv --no-setuptools . && "
                                 "source /tmp/venv/bin/activate && "
                                 "pip install setuptools && "
                                 "pip install eventlet PyYAML oslo.messaging petname redis zmq && "
                                 "pip install /tmp/oslo.messaging'" % node)


def start_proxy_on_nodes_venv(nodes, use_pub_sub, debug=False, double_proxy=False):

    for node in nodes:
        print get_managable_ip_from_node(node)
        if not args.dry_run:

            print '\nStarting oslo-messaging-zmq-proxy on %s' % node

            exec_remote_configurer(node, command="--start-proxy", redis_host=REDIS_HOST,
                                   debug=debug, double_proxy=double_proxy, use_pub_sub=use_pub_sub)
        else:
            print '\nStarting oslo-messaging-zmq-proxy on %s' % node


def stop_proxies_on_nodes(nodes):
    for node in nodes:
        exec_remote_configurer(node, command="--kill-proxy", redis_host=REDIS_HOST)


def install_oslo_messaging_package(package_url, package_name, nodes):

    for node in nodes:
        print '\nInstalling %s on %s' % (package_url, node)
        if not args.dry_run:
            print get_command_output("ssh %s 'mkdir /tmp/zmq-package/'" % node)
            print get_command_output("ssh %s 'wget -N -O /tmp/zmq-package/%s "
                                     "%s'" % (node, package_name, package_url))
            print get_command_output("ssh %s 'dpkg --force-overwrite -i /tmp/zmq-package/%s'" % (node, package_name))


def apt_install_package(nodes, package_name):
    for node in nodes:
        print '\nInstalling %s on %s' % (package_name, node)
        print get_command_output("ssh %s 'apt-get -y install %s'" % (node, package_name))


def detect_roles():
    global controllers, controller0, computes
    fuel_columns_count = int(get_command_output("fuel nodes 2>&1 | grep controller | awk '{ print NF }'").split('\n')[0])
    assert fuel_columns_count == EXPECTED_NUMBER_OF_FUEL_COLUMNS, "Columns have to match %d expected value" % EXPECTED_NUMBER_OF_FUEL_COLUMNS

    controllers = get_command_output("fuel nodes 2>&1 | grep controller | awk '{ print $9 }'").split('\n')
    computes = get_command_output("fuel nodes 2>&1 | grep compute | awk '{ print $9 }'").split('\n')

    controller0 = "node-" + get_command_output("fuel nodes 2>&1 | grep controller_0 | awk '{ print $1 }'")

    if not controllers or not computes:
        raise RuntimeError("Nodes discovery step failure. Please run again.")

    print "Controller0 = %s" % controller0

    if args.dry_run:
        controllers = controllers[:1]
        computes = computes[:2]


def firewall_ports_open(nodes, ports_list):
    for node in nodes:
        get_command_output("ssh %s 'iptables -A INPUT -p tcp --match multiport --dports %s -j ACCEPT'" % (node, ','.join(str(port) for port in ports_list)))


def firewall_port_range_open(nodes, min_port, max_port):
    for node in nodes:
        get_command_output("ssh %s 'iptables -A INPUT -p tcp --match multiport --dports %d:%d -j ACCEPT'" % (node, min_port, max_port))


def restart_redis():
    elaborate_processes_on_nodes(controllers, ['redis-server'])


def deploy_redis(node):
    update_dpkg_keys()
    print get_command_output("ssh %s 'apt-get -y install git redis-server redis-tools'" % node)
    for controller in controllers:
        print get_command_output("ssh %s 'apt-get -y install redis-tools'" % controller)
    exec_remote_configurer(node, command="--hack-redis", redis_host=REDIS_HOST)
    firewall_ports_open(controllers, [6379, 16379, 26379, FRONTEND_PORT, BACKEND_PORT, PUBLISHER_PORT,
                                      30001, 30002, 30003, 40001, 40002, 40003])
    elaborate_processes_on_nodes([node], ['redis-server'])


def update_dpkg_keys():
    def update_node(node):
        print get_command_output("ssh %s 'dpkg --configure -a'" % node)

    for node in controllers:
        update_node(node)
    for node in computes:
        update_node(node)


def build_cpp_proxy(node):
    print get_command_output("ssh %s 'apt-get -y install git'" % node)
    print get_command_output("ssh %(node)s 'rm -rf %(proxy_dir)s "
                             "&& git clone %(repo)s %(proxy_dir)s "
                             "&& cd %(proxy_dir)s "
                             "&& git fetch %(repo)s %(patch)s "
                             "&& git checkout FETCH_HEAD "
                             "&& /bin/bash %(proxy_dir)s/install_deps_ubuntu.sh "
                             "&& /bin/bash %(proxy_dir)s/build "
                             "&& /bin/bash %(proxy_dir)s/build_release'" %
                             {"node": node,
                              "proxy_dir": CPP_PROXY_DIR,
                              "repo": OSLO_MESSAGING_GIT_REPO,
                              "patch": OSLO_MESSAGING_GIT_BRANCH})


def start_cpp_proxy_on_nodes(nodes, use_pub_sub, debug=False, double_proxy=True):

    # Force double proxy for now
    double_proxy = True

    for node in nodes:
        print get_managable_ip_from_node(node)
        if not args.dry_run:
            generate_config_for_proxy(node, use_pub_sub)

            cpp_proxy_binary = os.path.join(CPP_PROXY_DIR,
                                            "build-Debug" if debug else "build-Release",
                                            "zmq-proxy")

            print get_command_output("ssh %(node)s 'nohup  %(proxy_binary)s "
                                     "--frontend-port %(fe)s %(backend_port)s --publisher-port %(pub)s "
                                     "--config-file=/etc/zmq-proxy/zmq.conf "
                                     "> /var/log/zmq-proxy.log 2>&1 < /var/log/zmq-proxy.log  &'" %
                                     {"node": node,
                                      "proxy_binary": cpp_proxy_binary,
                                      "fe": FRONTEND_PORT,
                                      "pub": PUBLISHER_PORT,
                                      "backend_port": "--backend-port %s" % BACKEND_PORT if double_proxy else ""})
        else:
            print '\nStarting oslo-messaging-zmq-proxy on %s' % node


parser = argparse.ArgumentParser()
parser.add_argument('--dry-run', dest='dry_run', action='store_true')
parser.add_argument('--install-packages', dest='install_packages',
                    action='store_true')
parser.add_argument('--update-public-keys', dest='update_public_keys', action='store_true')

parser.add_argument('--start-proxies', dest='start_proxies',
                    action='store_true')
parser.add_argument('--start-local-proxies', dest='start_local_proxies',
                    action='store_true')
parser.add_argument('--start-proxies-venv', dest='start_proxies_venv',
                    action='store_true')
parser.add_argument('--setup-venv', dest='setup_venv', action='store_true')

parser.add_argument('--start-proxies-cpp', dest='start_proxies_cpp',
                    action='store_true')
parser.add_argument('--build-cpp-proxy', dest='build_cpp_proxy', action='store_true')

parser.add_argument('--double-proxy', dest='double_proxy',
                    action='store_true')
parser.add_argument('--kill-proxies', dest='kill_proxies',
                    action='store_true')
parser.add_argument('--restart-services', dest='restart_services',
                    action='store_true')
parser.add_argument('--stop-services', dest='stop_services',
                    action='store_true')
parser.add_argument('--start-services', dest='start_services',
                    action='store_true')
parser.add_argument('--hack-configs', dest='hack_configs',
                    action='store_true')
parser.add_argument('--restore-configs', dest='restore_configs',
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

parser.add_argument('--deploy-redis', dest='deploy_redis', action='store_true')
parser.add_argument('--deploy-redis-sentinel', dest='deploy_redis_sentinel',
                    action='store_true')
parser.add_argument('--restart-redis', dest='restart_redis',
                    action='store_true')
parser.add_argument('--redis-host', dest='redis_host', type=str)

parser.add_argument('--git-repo', dest='git_repo', type=str)
parser.add_argument('--git-branch', dest='git_branch', type=str)
parser.add_argument('--package-url', dest='package_url', type=str)
parser.add_argument('--package-name', dest='package_name', type=str)
parser.add_argument('--proxy-package-url', dest='proxy_package_url', type=str)
parser.add_argument('--proxy-package-name', dest='proxy_package_name', type=str)

parser.add_argument('--generate-config', dest='generate_config', action='store_true')
parser.add_argument('--use-pub-sub', dest='use_pub_sub', action='store_true')
parser.add_argument('--use-router-proxy', dest='use_router_proxy', action='store_true')
parser.add_argument('--debug', dest='debug', action='store_true')
parser.add_argument('--log-level', dest='log_level', type=str)
parser.add_argument('--use-acks', dest='use_acks', action='store_true')
parser.add_argument('--transport-url', dest='transport_url', type=str)
parser.add_argument('--change-request', dest='change_request', type=str)


args = parser.parse_args()

controllers = []
computes = []
controller0 = None


def main():

    if args.dry_run:
        print 'Performing dry run'

    detect_roles()

    global REDIS_HOST
    if args.redis_host:
        REDIS_HOST = args.redis_host
    else:
        REDIS_HOST = controller0

    global TRANSPORT_URL
    if args.transport_url:
        TRANSPORT_URL = args.transport_url

    global OSLO_MESSAGING_GIT_REPO
    if args.git_repo:
        OSLO_MESSAGING_GIT_REPO = args.git_repo

    global OSLO_MESSAGING_GIT_BRANCH
    if args.git_branch:
        OSLO_MESSAGING_GIT_BRANCH = args.git_branch

    global PACKAGE_NAME, PACKAGE_URL
    global PROXY_PACKAGE_NAME, PROXY_PACKAGE_URL
    global CHANGE_REQUEST

    if args.package_url:
        PACKAGE_URL = args.package_url
    if args.proxy_package_url:
        PROXY_PACKAGE_URL = args.proxy_package_url
    if args.package_name:
        PACKAGE_NAME = args.package_name
    if args.proxy_package_name:
        PROXY_PACKAGE_NAME = args.proxy_package_name

    use_pub_sub = args.use_pub_sub if args.use_pub_sub else False
    use_debug_logging = args.debug if args.debug else False

    print ("Detected controllers: %s" % controllers)
    print ("Detected computes: %s" % computes)

    if args.build_cpp_proxy:
        for node in controllers:
            build_cpp_proxy(node)

    if args.update_public_keys:
        update_dpkg_keys()

    if args.generate_config:
        for node in controllers:
            generate_config_for_proxy(node, use_pub_sub=use_pub_sub)

    if args.deploy_redis:
        deploy_redis(REDIS_HOST)

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
        apt_install_package(computes, "python-redis")

    if args.start_proxies:
        start_proxy_on_nodes(controllers, use_pub_sub=use_pub_sub, debug=use_debug_logging, double_proxy=args.double_proxy)

    if args.start_local_proxies:
        start_local_publisher_on_nodes(controllers + computes, use_debug_logging)
        start_redis_proxies_on_nodes(controllers + computes, use_debug_logging)

    if args.setup_venv:
        setup_venv(controllers)

    if args.start_proxies_venv:
        start_proxy_on_nodes_venv(controllers, use_pub_sub=use_pub_sub, debug=use_debug_logging, double_proxy=args.double_proxy)

    if args.start_proxies_cpp:
        start_cpp_proxy_on_nodes(controllers, use_pub_sub=use_pub_sub, debug=use_debug_logging, double_proxy=args.double_proxy)

    if args.kill_proxies:
        stop_proxies_on_nodes(controllers + computes)

    if args.restart_redis:
        restart_redis()

    if args.hack_configs:
        hack_configs_on_nodes(controllers, CONTROLLER_CONFIGS, use_pub_sub=use_pub_sub, use_router_proxy=args.use_router_proxy, debug=use_debug_logging, use_acks=args.use_acks)
        hack_configs_on_nodes(computes, COMPUTE_CONFIGS, use_pub_sub=use_pub_sub, use_router_proxy=args.use_router_proxy, debug=use_debug_logging, use_acks=args.use_acks)

    if args.restore_configs:
        restore_configs(controllers, CONTROLLER_CONFIGS)
        restore_configs(computes, COMPUTE_CONFIGS)

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
        firewall_port_range_open(controllers, 49152, 65535)
        firewall_port_range_open(computes, 49152, 65535)

if __name__ == "__main__":
    main()
