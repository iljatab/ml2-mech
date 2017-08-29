#
# MRV ML2 Mechanism Driver
#

import sys
import time
import os
import copy
import inspect
import pprint

from oslo_log import log as logger
from oslo_service import loopingcall

from neutron import worker

from networking_mrv.ml2.drivers.mrv import db

LOG = logger.getLogger(__name__)


class MRVSyncWorker(worker.NeutronWorker):

    def __init__(self, switches):
        super(MRVSyncWorker, self).__init__(worker_process_count=0)
        self._switches = switches
        self._loop = None


    def start(self):
        super(MRVSyncWorker, self).start()
        if self._loop is None:
            self._loop = loopingcall.FixedIntervalLoopingCall(self._do_sync)
        self._loop.start(interval=15)


    def stop(self, graceful=False):
        if self._loop is not None:
            self._loop.stop()


    def wait(self):
        if self._loop is not None:
            self._loop.wait()


    def reset(self):
        self.stop()
        self.wait()
        self.start()


    def _do_sync(self):
        LOG.info('ILJA - synch started')
        
        nets = { n.network_id: n for n in db.get_networks() }
        ports = { p.port_id: p for p in db.get_ports() }

        for net in nets.values():
            for sw in self._switches.values():
                sw.add_network(net)

        for port in ports.values():
            net = nets.get(port.network_id)
            for sw in self._switches.values():
                sw.add_port(port, net)

        self.stop()
        LOG.info('ILJA - synch finished')

