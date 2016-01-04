#liaojie
"""Image cache manager.

"""

import hashlib
import os
import re
import time

from oslo_concurrency import lockutils
from oslo_concurrency import processutils
from oslo_config import cfg
from oslo_log import log as logging
from oslo_serialization import jsonutils

from nova.i18n import _LE
from nova.i18n import _LI
from nova.i18n import _LW
from nova.openstack.common import fileutils
from nova import utils
from nova.virt import imagecache
from nova.virt.libvirt import utils as libvirt_utils

#liaojie
from nova import image
from nova import conductor
from nova import objects

LOG = logging.getLogger(__name__)

imagecache_opts = [
    cfg.StrOpt('image_info_filename_pattern',
               default='$instances_path/$image_cache_subdirectory_name/'
                       '%(image)s.info',
               help='Allows image information files to be stored in '
                    'non-standard locations'),
    cfg.BoolOpt('remove_unused_kernels',
                default=False,
                help='Should unused kernel images be removed? This is only '
                     'safe to enable if all compute nodes have been updated '
                     'to support this option. This will be enabled by default '
                     'in future.'),
    cfg.IntOpt('remove_unused_resized_minimum_age_seconds',
               default=3600,
               help='Unused resized base images younger than this will not be '
                    'removed'),
    cfg.BoolOpt('checksum_base_images',
                default=False,
                help='Write a checksum for files in _base to disk'),
    cfg.IntOpt('checksum_interval_seconds',
               default=3600,
               help='How frequently to checksum base images'),
    #TODO:how to set the config in file 
    cfg.IntOpt('max_imagecache_disk',
               default=-1,
               help='max disk size to cache images'),
    ]

CONF = cfg.CONF
CONF.register_opts(imagecache_opts, 'libvirt')
CONF.import_opt('instances_path', 'nova.compute.manager')
CONF.import_opt('image_cache_subdirectory_name', 'nova.virt.imagecache')

def get_cache_id(image_id):
    """
    Return a filename based on the SHA1 hash of a given image ID.
    """
    return hashlib.sha1(image_id).hexdigest()


class HostImageCacheManager(imagecache.ImageCacheManager):
    def __init__(self, host):
        #TODO:how to init multi-parent class
        super(HostImageCacheManager, self).__init__()
        #TODO:use nova-conductor to access db? what about  objects?
        self.host = host
        self.image_api=image.API()
        self.conductor_api = conductor.API()

    def check_or_remove_imagecache(self, context, ignore_imagecaches):
        #NOTE:
        #check whether we should remove the unused LFU image cache
        local_imagecache_size=self._get_all_local_imagecache_size(context)
        max_imagecache_disk=self._get_max_imagecache_disk()
        #if yes, then remove it in local and update the db
        if local_imagecache_size >= max_imagecache_disk:
            selected_cache_id=self._select_discard_imagecache(context, ignore_imagecaches)
            self._remove_imagecache(context, selected_cache_id)

    def _get_all_local_imagecache_size(self, context):
        result_size=0
        all_imagecaches = self.conductor_api.host_imagecache_get_all_by_host(context, self.host)
        for imagecache in all_imagecaches:
            result_size+=imagecache['size']
        return result_size

    def _get_max_imagecache_disk(self):
        #TODO:more complexity
        #NOTE:this value must be the same as cache_disk_mb in glance/host_imagecache/base.py
        cache_disk_mb=15360
        return cache_disk_mb

    def _list_backing_images(self, context):
        """List the backing images currently in use."""
        #TODO:now we just implement it temporarily
        all_instances=objects.InstanceList.get_by_host(context, self.host)
        running = self._list_running_instances(context, all_instances)
        self.instance_names = running['instance_names']
        inuse_images = []
        for ent in os.listdir(CONF.instances_path):
            if ent in self.instance_names:
                disk_path = os.path.join(CONF.instances_path, ent, 'disk')
                if os.path.exists(disk_path):
                    try:
                        backing_file = libvirt_utils.get_disk_backing_file(
                            disk_path)
                    except processutils.ProcessExecutionError:
                        if not os.path.exists(disk_path):
                            continue
                        else:
                            raise

                    if backing_file:
                        if backing_file not in inuse_images:
                            inuse_images.append(backing_file)

                        backing_path = os.path.join(
                            CONF.instances_path,
                            CONF.image_cache_subdirectory_name,
                            backing_file)
                        try:
                            base_file = libvirt_utils.get_disk_backing_file(
                                backing_path)
                        except processutils.ProcessExecutionError:
                            if not os.path.exists(backing_path):
                                continue
                            else:
                                raise                       
                        if base_file and base_file not in inuse_images:
                            inuse_images.append(base_file)
        return inuse_images

    def _select_discard_imagecache(self, context, ignore_imagecaches):
        #TODO:now the processing is simple 
        active_imagecaches=self._list_backing_images(context)
        selected=[]
        all_imagecaches=self.conductor_api.host_imagecache_get_all_by_host(context, self.host)
        for imagecache in all_imagecaches:
            cache_id=imagecache['cache_id']
            if cache_id not in active_imagecaches and cache_id not in ignore_imagecaches:
                selected.append(imagecache)

        selected.sort(cmp=lambda x,y:x.get('survival_value')-y.get('survival_value'))   
        if selected:
            return selected[0]['cache_id']
        else:
            return None

    def _remove_imagecache(self, context, cache_id):
        if not cache_id:
            return

        cache_path = os.path.join(
                            CONF.instances_path,
                            CONF.image_cache_subdirectory_name,
                            cache_id)       
        if os.path.exists(cache_path):
            try:
                os.remove(cache_path)
            except OSError as e:
                if os.path.exists(cache_path):
                    LOG.warn(_LE('Failed to remove %(cache_path)s, '
                                      'error was %(error)s'),
                                  {'cache_path': cache_path,
                                   'error': e})
        self.conductor_api.host_imagecache_delete(context, self.host, cache_id)

    def increase_survival_value(self, context, cache_id, size=0):
        """
        values :host,cache_id, survival_value
        """
        #NOTE:if image cache not exist, then create it with survival_value=0
        values={}
        values['host']=self.host
        values['cache_id']=cache_id
        values['size']=size

        #TODO:the survival_value increase always,it may overflow
        survival_value=0
        old_obj=self.conductor_api.host_imagecache_get(context, self.host, cache_id)
        if old_obj:
            survival_value=old_obj['survival_value']+1
        else:
            #missing
            self.decrease_survival_value(context)

        values['survival_value']=survival_value

        self.conductor_api.host_imagecache_update(context, values)

    def decrease_survival_value(self, context):
        host_imagecaches=self.conductor_api.host_imagecache_get_all_by_host(context, self.host)
        for imagecache in host_imagecaches:
            values={}
            values['host']=imagecache['host']
            values['cache_id']=imagecache['cache_id']
            values['size']=imagecache['size']

            survival_val=imagecache['survival_value']
            survival_val=survival_val/2
            values['survival_value']=survival_val
            self.conductor_api.host_imagecache_update(context, values)




