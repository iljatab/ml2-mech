#
# MRV ML2 Mechanism Driver
#

from oslo_log import log as logger
from oslo_config import cfg

LOG = logger.getLogger(__name__)


def get_config():
    """ Returns configuration dictionary from [ml2_mech_mrv:*] groups """
    conf_dict = {}
    for sw_id, sw_cfg in _read_config_file().items():
        conf_dict[sw_id] = {}

        for opt in sw_cfg:
            k, v = opt
            if k == 'vlan_subnets':
                conf_dict[sw_id][k] = set(map(str.strip, v[0].split(',')))
            elif k == 'link':
                conf_dict[sw_id][k] = {}
                for link in v:
                    try:
                        node, port = map(str.strip, link.split(':'))
                    except ValueError:
                        continue
                    conf_dict[sw_id][k][node] = port
            else:
                conf_dict[sw_id][k] = v[0]

    return conf_dict


def _read_config_file():
    file_dict = {}
    mparser = cfg.MultiConfigParser()
    mparser.read(cfg.CONF.config_file)

    for parsed_file in mparser.parsed:
        for parsed_item in parsed_file.keys():

            try:
                switch, switch_id = parsed_item.split(':')
            except ValueError:
                continue

            if switch.lower() == 'ml2_mech_mrv':
                file_dict[switch_id] = parsed_file[parsed_item].items()

    return file_dict

