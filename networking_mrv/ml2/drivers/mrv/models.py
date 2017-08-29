#
# MRV ML2 Mechanism Driver
#

import sqlalchemy as sa

from oslo_log import log as logger

from neutron.db import model_base

LOG = logger.getLogger(__name__)

MRV_UUID_LEN = 36
MRV_STR_LEN = 255



class MRVNetwork(model_base.BASEV2):

    __tablename__ = "mrv_ml2_networks"

    network_id = sa.Column(sa.String(MRV_UUID_LEN), primary_key=True)
    vlan_id = sa.Column(sa.Integer, nullable=False)
    physical_network = sa.Column(sa.String(MRV_STR_LEN), nullable=False)
    name = sa.Column(sa.String(MRV_STR_LEN), nullable=False)



class MRVPort(model_base.BASEV2):

    __tablename__ = "mrv_ml2_ports"

    port_id = sa.Column(sa.String(MRV_UUID_LEN), primary_key=True)
    network_id = sa.Column(sa.String(MRV_UUID_LEN), nullable=False)
    host = sa.Column(sa.String(MRV_STR_LEN), nullable=False)

