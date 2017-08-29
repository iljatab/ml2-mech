#
# MRV ML2 Mechanism Driver
#

from oslo_log import log as logger

import neutron.db.api as db

from networking_mrv.ml2.drivers.mrv import models

LOG = logger.getLogger(__name__)


def add_network(network_id, vlan_id, physical_network, name):
    """ Store a network unless it already exists """
    session = db.get_session()
    with session.begin():
        network = (session.query(models.MRVNetwork)
                   .filter_by(network_id=network_id).first())

        if not network:
            network = models.MRVNetwork(
                network_id=network_id,
                vlan_id=vlan_id,
                physical_network=physical_network,
                name=name)
            session.add(network)
            session.flush()
            return network

        return None


def get_network(network_id):
    """ Get network by Neutron network_id """
    session = db.get_session()
    with session.begin():
        network = (session.query(models.MRVNetwork)
                   .filter_by(network_id=network_id).first())

    return (network if network else None)


def del_network(network_id):
    """ Delete network by Neutron network_id """
    session = db.get_session()
    with session.begin():
        network = (session.query(models.MRVNetwork)
                   .filter_by(network_id=network_id).first())

        if network:
            (session.query(models.MRVNetwork)
             .filter_by(network_id=network_id).delete())

        return network    


def add_port(port_id, network_id, host):
    """ Store a port unless it already exists """
    session = db.get_session()
    with session.begin():
        port = (session.query(models.MRVPort)
                .filter_by(port_id=port_id).first())

        if not port:
            port = models.MRVPort(
                port_id=port_id, network_id=network_id, host=host)
            session.add(port)
            session.flush()
            return port

        return None


def del_port(port_id):
    """ Delete port by Neutron port_id """
    session = db.get_session()
    with session.begin():
        port = (session.query(models.MRVPort)
                .filter_by(port_id=port_id).first())

        if port:
            (session.query(models.MRVPort)
             .filter_by(port_id=port_id).delete())

        return port


def get_networks():
    """ Get all networks """
    session = db.get_session()
    with session.begin():
        networks = session.query(models.MRVNetwork).all()
    return networks


def get_ports():
    """ Get all ports """
    session = db.get_session()
    with session.begin():
        ports = session.query(models.MRVPort).all()
    return ports

