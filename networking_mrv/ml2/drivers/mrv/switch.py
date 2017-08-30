#
# MRV ML2 Mechanism Driver
#

import os
import sys
import copy
import inspect
import pprint

from ncclient import manager as ncm
from ncclient import NCClientError

from oslo_log import log as logger

from networking_mrv.ml2.drivers.mrv import db

LOG = logger.getLogger(__name__)
PP = pprint.PrettyPrinter()


class MrvSwitchConnector(object):
    """ Program MRV switch equipment using Netconf API """

    def __init__(self, switch_id, switch_cfg):
        self._id = switch_id
        self._host = switch_cfg.get('host', switch_id)
        self._username = switch_cfg.get('username', 'admin')
        self._password = switch_cfg.get('password', '')
        self._subnets = switch_cfg.get('vlan_subnets', set())
        self._links = switch_cfg.get('link', {})


    def __repr__(self):
        return '<{} {}: {}>'.format(self.__class__.__name__, id(self), self.__dict__)


    def _apply_conf(self, conf):
        conf_nets = { n.network_id: n for n in conf['networks'] }
        conf_ports = { p.port_id: p for p in conf['ports'] }

        for port_id, port in self._ports_in_sw.items():
            if port_id not in conf_ports:
                if self._switch_del_port(port):
                    del self._ports_in_sw[port_id]

        for network_id, net in self._nets_in_sw.items():
            if network_id not in conf_nets:
                if self._switch_del_network(net):
                    del self._nets_in_sw[network_id]

        for network_id, net in conf_nets.items():
            if network_id not in self._nets_in_sw:
                if net.physical_network not in self._subnets:
                    continue
                if self._switch_add_network(net):
                    self._nets_in_sw[network_id] = net

        for port_id, port in conf_ports.items():
            if port_id not in self._ports_in_sw:
                if port.host not in self._links:
                    continue
                if self._switch_add_port(port):
                    self._ports_in_sw[port_id] = port


    def add_network(self, network):
        if not self._is_my_network(network):
            return
        reqs = self._add_network_xml(network)
        return self._talk_to_switch(reqs)


    def del_network(self, network):
        reqs = self._del_network_xml(network)
        return self._talk_to_switch(reqs)


    def add_port(self, port, network):
        if not network:
            return
        if port.host not in self._links:
            return
        reqs = self._add_port_xml(port, network)
        return self._talk_to_switch(reqs)


    def del_port(self, port, network):
        if not network:
            return
        if port.host not in self._links:
            return
        reqs = self._del_port_xml(port, network)
        return self._talk_to_switch(reqs)


    def _is_my_network(self, network):
        return network.physical_network in self._subnets


    def _elan_name(self, network):
        return 'ML2-{}'.format(network.vlan_id)


    def _elan_service_id(self, network):
        return str(network.vlan_id)


    def _elan_description(self, network):
        return 'ML2:' + network.network_id


    def _ac_name(self, port, network):
        return self._links[port.host] + '.' + str(network.vlan_id)


    def _ac_outer_tag(self, port, network):
        return str(network.vlan_id)


    def _ac_description(self, port, network):
        return 'ML2:' + port.port_id


    def _add_network_xml(self, network):
        x = '''
            <config>
              <mpls_elan_objects xmlns="http://www.mrv.com/ns/mpls-elan">
                <config-elans>
                  <config-elan 
                    xmlns:nc="urn:ietf:params:xml:ns:netconf:base:1.0"
                    nc:operation="create">
                    <name>{name}</name>
                    <service-id>{service_id}</service-id>
                    <description>{description}</description>
                    <enable>true</enable>
                  </config-elan>
                </config-elans>
              </mpls_elan_objects>
            </config>
        '''
        return [ x.format(name=self._elan_name(network),
                          service_id=self._elan_service_id(network),
                          description=self._elan_description(network)) ]


    def _del_network_xml(self, network):
        x = '''
            <config>
              <mpls_elan_objects xmlns="http://www.mrv.com/ns/mpls-elan">
                <config-elans>
                  <config-elan 
                    xmlns:nc="urn:ietf:params:xml:ns:netconf:base:1.0"
                    nc:operation="delete">
                    <name>{name}</name>
                  </config-elan>
                </config-elans>
              </mpls_elan_objects>
            </config>
        '''
        return [ x.format(name=self._elan_name(network)) ]


    def _add_port_xml(self, port, network):
        x1 = '''
            <config>
              <ac_objects xmlns="http://www.mrv.com/ns/ac">
                <ac-interface 
                  xmlns:nc="urn:ietf:params:xml:ns:netconf:base:1.0"
                  nc:operation="create">
                  <name>{name}</name>
                  <outer-tags>{outer_tag}</outer-tags>
                  <description>{description}</description>
                  <enable>true</enable>
                </ac-interface>
              </ac_objects>
            </config>
        '''
        x2 = '''
            <config>
              <mpls_elan_objects xmlns="http://www.mrv.com/ns/mpls-elan">
                <config-elans>
                  <config-elan>
                    <name>{name}</name>
                    <acs 
                      xmlns:nc="urn:ietf:params:xml:ns:netconf:base:1.0"
                      nc:operation="create">
                      <ac>{ac_name}</ac>
                    </acs>
                  </config-elan>
                </config-elans>
              </mpls_elan_objects>
            </config>
        '''
        return [
            x1.format(name=self._ac_name(port, network),
                      outer_tag=self._ac_outer_tag(port, network),
                      description=self._ac_description(port, network)),
            x2.format(name=self._elan_name(network),
                      ac_name=self._ac_name(port, network)) ]


    def _del_port_xml(self, port, network):
        x1 = '''
            <config>
              <mpls_elan_objects xmlns="http://www.mrv.com/ns/mpls-elan">
                <config-elans>
                  <config-elan>
                    <name>{name}</name>
                    <acs 
                      xmlns:nc="urn:ietf:params:xml:ns:netconf:base:1.0"
                      nc:operation="delete">
                      <ac>{ac_name}</ac>
                    </acs>
                  </config-elan>
                </config-elans>
              </mpls_elan_objects>
            </config>
        '''
        x2 = '''
            <config>
              <ac_objects xmlns="http://www.mrv.com/ns/ac">
                <ac-interface 
                  xmlns:nc="urn:ietf:params:xml:ns:netconf:base:1.0"
                  nc:operation="delete">
                  <name>{name}</name>
                </ac-interface>
              </ac_objects>
            </config>
        '''
        return [
            x1.format(name=self._elan_name(network),
                      ac_name=self._ac_name(port, network)),
            x2.format(name=self._ac_name(port, network)) ]


    def _talk_to_switch(self, requests):
        try:
            with ncm.connect(host=self._host,
                             username=self._username,
                             password=self._password,
                             hostkey_verify=False,
                             allow_agent=False,
                             look_for_keys=False,
                             timeout=5) as m:
                for req in requests:
                    LOG.info('ILJA\n%s', req)
                    m.discard_changes()
                    m.edit_config(target='candidate', config=req, test_option='set')
                    m.commit()

        except NCClientError as e:
            LOG.warning("Netconf error for switch {}: {}".format(self._id, e))
            return False

        return True

