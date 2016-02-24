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
        has_imagecache=0
        imagecache_utilization=0
        imagecache_disk_utilization=0
        res_val=0

        #get has_imagecache value
        def get_cache_id(image_id):
            return hashlib.sha1(image_id).hexdigest()
        instance_image_id=weight_properties.get('request_spec').get('image').get('id')
        instance_cache_id=get_cache_id(instance_image_id)
        for imagecache in host_state.imagecaches:
            if instance_cache_id == imagecache.cache_id:
                has_imagecache=1
                break
        
        if has_imagecache:
            #get imagecache_utilization value
            local_instances_with_imagecache=0
            all_instances_with_imagecache=0
            for id,instance in host_state.instances.iteritems():
                if instance.image_ref == instance_image_id:
                    local_instances_with_imagecache +=1
            for image_ref in host_state.imageinstances:
                if image_ref == instance_image_id:
                    all_instances_with_imagecache +=1
            if all_instances_with_imagecache <= 0:
                imagecache_utilization=1
            else:
                imagecache_utilization=round(1-local_instances_with_imagecache*1.0/all_instances_with_imagecache, 2)

            if imagecache_utilization <0:
                imagecache_utilization=0
        else:
            #get imagecache_disk_utilization value
            all_imagecache_disk=0
            for each_imagecache in host_state.imagecaches:
               all_imagecache_disk+=each_imagecache.size 
            host_cache_disk_mb=15360
            imagecache_disk_utilization=round(1-all_imagecache_disk*1.0/host_cache_disk_mb, 2)
            if imagecache_disk_utilization<0:
                imagecache_disk_utilization=0

        #get the res_val
        res_val=has_imagecache+imagecache_utilization+imagecache_disk_utilization
        print "----------------"+host_state.host+"--------------" 
        print " imagecache_utilization score: %s" % imagecache_utilization
        print " imagecache_disk_utilization score: %s" % imagecache_disk_utilization
        print " imagecache weight score: %s" % res_val
        return res_val
