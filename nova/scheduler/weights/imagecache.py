#liaojie

"""
ImageCache Weigher.  Weigh hosts by their matching image cache.
"""

from oslo_config import cfg

from nova.scheduler import weights

import hashlib

#TODO:add the option in conf file
imagecache_weight_opts = [
        cfg.FloatOpt('imagecache_weight_multiplier',
                     default=1.0,
                     help='Multiplier used for weighing imagecache.' ),
]

CONF = cfg.CONF
CONF.register_opts(imagecache_weight_opts)

class ImageCacheWeigher(weights.BaseHostWeigher):
    minval = 0

    def weight_multiplier(self):
        """Override the weight multiplier."""
        return CONF.imagecache_weight_multiplier

    def _weigh_object(self, host_state, weight_properties):
        """Higher weights win."""
        #TODO:find more scheduler weights to score 
        def get_cache_id(image_id):
            return hashlib.sha1(image_id).hexdigest()

        instance_image_id=weight_properties.get('request_spec').get('image').get('id')
        instance_cache_id=get_cache_id(instance_image_id)
        res_val=0
        for imagecache in host_state.imagecaches:
            if instance_cache_id == imagecache.cache_id:
                res_val=1
                break

        return res_val
