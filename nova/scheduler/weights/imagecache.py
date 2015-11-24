#liaojie
#TODO:finish imagecache
"""
RAM Weigher.  Weigh hosts by their RAM usage.

The default is to spread instances across all hosts evenly.  If you prefer
stacking, you can set the 'ram_weight_multiplier' option to a negative
number and the weighing has the opposite effect of the default.
"""

from oslo_config import cfg

from nova.scheduler import weights

ram_weight_opts = [
        cfg.FloatOpt('ram_weight_multiplier',
                     default=1.0,
                     help='Multiplier used for weighing ram.  Negative '
                          'numbers mean to stack vs spread.'),
]

CONF = cfg.CONF
CONF.register_opts(ram_weight_opts)


class RAMWeigher(weights.BaseHostWeigher):
    minval = 0

    def weight_multiplier(self):
        """Override the weight multiplier."""
        return CONF.ram_weight_multiplier

    def _weigh_object(self, host_state, weight_properties):
        """Higher weights win.  We want spreading to be the default."""
        return host_state.free_ram_mb
