#
# MRV ML2 Mechanism Driver
#

import os
import sys
import copy
import inspect
import pprint

from oslo_log import log as logger

from neutron.plugins.ml2 import driver_api as api

from networking_mrv.ml2.drivers.mrv import config
from networking_mrv.ml2.drivers.mrv import switch
from networking_mrv.ml2.drivers.mrv import sync
from networking_mrv.ml2.drivers.mrv import db

LOG = logger.getLogger(__name__)
PP = pprint.PrettyPrinter()


class MrvMechanismDriver(api.MechanismDriver):
    """ ML2 mechanism driver for MRV switch equipment """

    def initialize(self):
        self._cfg_dict = config.get_config()
        LOG.debug('Configuration: %s', self._cfg_dict)

        self._switches = {}
        for sw_id, sw_cfg in self._cfg_dict.items():
            self._switches[sw_id] = switch.MrvSwitchConnector(sw_id, sw_cfg)
        LOG.debug('Switches %s', self._switches)


    def get_workers(self):
        return [sync.MRVSyncWorker(self._switches)]


    def create_network_postcommit(self, context):
        LOG.debug("%s\n%s\n%s", inspect.currentframe().f_code.co_name,
                 PP.pformat(context.current), context.network_segments)

        curr = context.current
        if curr.get('provider:network_type') != 'vlan':
            return

        network_id = curr.get('id')
        vlan_id = curr.get('provider:segmentation_id')
        physical_network = curr.get('provider:physical_network')
        name = curr.get('name')

        added = db.add_network(network_id, vlan_id, physical_network, name)
        if added:
            for sw in self._switches.values():
                sw.add_network(added)


    def update_network_postcommit(self, context):
        LOG.debug("%s\n%s\n%s", inspect.currentframe().f_code.co_name,
                 PP.pformat(context.current), context.network_segments)

        curr = context.current
        if curr.get('provider:network_type') != 'vlan':
            return

        network_id = curr.get('id')
        vlan_id = curr.get('provider:segmentation_id')
        physical_network = curr.get('provider:physical_network')
        name = curr.get('name')

        added = db.add_network(network_id, vlan_id, physical_network, name)
        if added:
            for sw in self._switches.values():
                sw.add_network(added)


    def delete_network_postcommit(self, context):
        LOG.debug("%s\n%s\n%s", inspect.currentframe().f_code.co_name,
                 PP.pformat(context.current), context.network_segments)

        curr = context.current
        deleted = db.del_network(curr.get('id'))
        if deleted:
            for sw in self._switches.values():
                sw.del_network(deleted)


    def update_port_postcommit(self, context):
        LOG.debug("%s\n%s\n%s\n%s\n%s\n%s",
                 inspect.currentframe().f_code.co_name,
                 PP.pformat(context.current),
                 context.binding_levels, context.segments_to_bind,
                 context.bottom_bound_segment, context.top_bound_segment)

        curr = context.current
        port_id = curr.get('id')
        network_id = curr.get('network_id')
        host = context.host.split('.')[0]

        added = db.add_port(port_id, network_id, host)
        if added:
            network = db.get_network(added.network_id)
            for sw in self._switches.values():
                sw.add_port(added, network)
            

    def delete_port_postcommit(self, context):
        LOG.debug("%s\n%s\n%s\n%s\n%s\n%s",
                 inspect.currentframe().f_code.co_name,
                 PP.pformat(context.current),
                 context.binding_levels, context.segments_to_bind,
                 context.bottom_bound_segment, context.top_bound_segment)

        curr = context.current
        deleted = db.del_port(curr.get('id'))
        if deleted:
            network = db.get_network(deleted.network_id)
            for sw in self._switches.values():
                sw.del_port(deleted, network)


