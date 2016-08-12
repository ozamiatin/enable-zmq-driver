#!/usr/bin/python

import re
import sys
import subprocess

from hack_config_with_zmq import get_command_output
from hack_config_with_zmq import REDIS_HOST


def generate_proxy_conf():
    with open('./zmq-proxy.conf', 'w') as conf_f:
        conf_f.write("[oslo_messaging_zmq]\n"
                     "rpc_zmq_host=%s\n"
                     "[matchmaker_redis]\n"
                     "host=%s" % (get_command_output("hostname"), REDIS_HOST))

def main():

    generate_proxy_conf()

if __name__=="__main__":
    main()
