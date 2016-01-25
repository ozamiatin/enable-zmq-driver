# enable-zmq-driver
A set of scripts to enable ZMQ driver in Fuel OpenStack environment

Run `configure_zmq.py` from the Fuel master node to enable the driver on all
machines in an OpenStack environment. You may also use `--dry-run` option.
In that mode the script will not restart or change configuration of any
component, it will just output what would it do if it was not a dry run.
The script copies zmq-recevier config in dry run mode, but that could be 
neglected.

Before running the script, you should ensure that oslo.messaging package
installed on your environment contains the driver. Also, after the run
is complete, you need to manually start zmq-receiver on each controller and
compute node by running

```bash
oslo-messaging-zmq-receiver --config-file=/etc/oslo-messaging-zmq-receiver.conf >/var/log/oslo-messaging-zmq-receiver.log 2>&1 &
```
