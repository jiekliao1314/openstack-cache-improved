#jiekliao

"""
Compute Image Cache
"""

import six
from six.moves.urllib import parse

from novaclient import base


class HostImageCache(base.Resource):
    """
    Host Image cache is compute nova image cache
    """

    def __repr__(self):
        #return "<HostImageCache: %s>" % self.id
        pass
    
   

class HostImageCacheManager(base.ManagerWithFind):
    """
    Manage :class:`HostImageCache` resources.
    """
    resource_class = HostImageCache

    def create(self, host_name, image_ids):
        """
        Create image cache in host.

        :param host_name 
        :param image_ids  a list of image_ids
        """

        body={
            'host_name':host_name,
            'image_ids':image_ids
        }
        return self._create('/host-imagecache', body, 'host_imagecache')    

    def list(self):
        #NOTE: an abstract func must been added
        pass

    def get(self, volume_id):
        pass
