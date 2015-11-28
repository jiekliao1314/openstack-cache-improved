#liaojie

import random
import copy
from glance.host_imagecache import client
from glance.host_imagecache import diskfilter
from glance.host_imagecache import imageweighter

class ImageCacheManager(object):

    def __init__(self, options):
        self.glance_cs=client.get_glanceclient(options)
        self.nova_cs=client.get_novaclient(options)

    def cache_all(self, args):
        #TODO:now we can't run it more than once because we don't get the cache info firstly 
        hosts=self.get_hosts()
        images=self.get_images()

        #NOTE:now we just test
        for host in hosts:
            print '############'
            print 'host:'+host.host_name
            selected_images=[]
            for image in images:
                if self.should_cache_image(host, image):
                    selected_images.append(copy.deepcopy(image))
                    print 'image:'+image.image_id
            self.filter_image_cache(host, selected_images)
            print '-----------'
            for image in selected_images:
                print image.image_id
        
            self.cache_host(host, selected_images)
        

    def cache_host(self, host, images):
        #NOTE:now we just send the image ids
        if not images:
            return
        image_ids=[]
        for image in images:
            image_ids.append(image.image_id)
        result=self.nova_cs.host_imagecache.create(host.host_name, image_ids)

    def should_cache_image(self, host, image):
        used_scale=image.used_scale
        random_num=random.random()
        if random_num < used_scale:
            return True
        else:
            return False
    
    def filter_image_cache(self, host, images):
        image_num=len(images)
        image_size_sum=0
        for image in images:
            image_size_sum+=image.cache_size_mb

        while image_size_sum > host.cache_disk_mb:
            remove_one=random.randint(0, image_num-1)
            image_num-=1
            image_size_sum-=images[remove_one].cache_size_mb
            del images[remove_one]

    def get_images(self):
        """
        get the info of images
        """
        images=self.glance_cs.images.list()

        result=[]
        for image in images:
            image_id=image.id
            status=image.status

            cache_size_mb=int(image.properties.get('cache_size_mb', 0))
            image_size=int(image.size/(1024*1024))
            cache_size_mb=max(cache_size_mb, image_size)

            used_scale=float(image.properties.get('used_scale', 0))
            result.append(ImageState(image_id, status, cache_size_mb, used_scale))

        return result


    def get_hosts(self):
        """
        get the info of hosts
        """
        #TODO:use nova api hypervisor instead to get detailed information about hosts 
        #get the active host
        hosts=self.nova_cs.hosts.list()
        host_names=set([host.host_name for host in hosts])
        #NOTE:used for test
        cache_disk_ratio=0.0

        result=[]

        for hostname in host_names:
            info=self.nova_cs.hosts.get(hostname)
            total_disk_mb=info[0].disk_gb*1024
            #TODO:how to get the cache_disk_mb of host
            cache_disk_mb=int(total_disk_mb * cache_disk_ratio)
            cache_disk_mb=300
            host_state=HostState(hostname, cache_disk_mb) 
            result.append(host_state)
        
        return result


class ImageState(object):
    """
    encapsulate the image info
    """
    #TODO: Add more info about image to help the image filter or weigher
    def __init__(self, image_id, status, cache_size_mb, used_scale):
        """
        :param used_scale the ratio of used scale
        """
        self.image_id=image_id
        self.status=status
        self.cache_size_mb=cache_size_mb #image cache size
        self.used_scale=used_scale

class HostState(object):
    """
    encapsulate the host info
    """
    #TODO:add more info about host to help the image cache download
    def __init__(self, host_name, cache_disk_mb):
        self.host_name=host_name
        self.cache_disk_mb=cache_disk_mb


