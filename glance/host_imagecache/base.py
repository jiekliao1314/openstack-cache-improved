#liaojie

from glance.host_imagecache import client
from glance.host_imagecache import diskfilter
from glance.host_imagecache import imageweighter

class ImageCacheManager(object):

    def __init__(self, options):
        self.glance_cs=client.get_glanceclient(options)
        self.nova_cs=client.get_novaclient(options)

    def cache_all(self, args):
        #TODO:now i don't care about whether many hosts download the same image simultaneously
        #or we can use multithreading
        #maybe we can make each compute node to select the images in order of probability
        #XXX:how to distribute the images to hosts to download?It is the critical question !
        images=self.get_images()
        hosts=self.get_hosts()
        hosts_map={}
        for host in hosts:
            hosts_map[host.host_name]=host

        filter=diskfilter.DiskFilter(hosts)
        weighter=imageweighter.ImageWeighter(hosts)
        hosts_num=len(hosts)

        #NOTE:now we just test
        try:
            self.cache_host("gb09", images)
        except:
            print 'wrong !'
        """
        for image in images:
            selected_hosts=self.get_selected_hosts(filter, weighter, image, hosts_num)
            for select_one in selected_hosts:
                flag=self.cache_host(select_one, image)
                if flag:
                    self.update_local_host(hosts_map[select_one], image)
                break
            break
        """

    def cache_host(self, hostname, images):
        #TODO: correct the code
        image_ids=[]
        for image in images:
            image_ids.append(image.image_id)
        result=self.nova_cs.host_imagecache.create(hostname, image_ids)
        print hostname+': ok!'
        return True

    def get_selected_hosts(self, filter, weighter, image, hosts_num):
        """
        get selected host for image
        """
        #filt
        filtered_hosts=filter.get_filtered_hosts(image)
        #weight
        weighted_hosts=weighter.get_weighted_hosts(filtered_hosts)
        #select
        selected_num=hosts_num * image.used_scale   
        selected_num=selected_num if selected_num >1 else 1
        
        return weighted_hosts[:selected_num]

    def update_local_host(self, host, image):
        host.max_cache_disk_mb-=image.max_size
        host.cached_image_count+=1

    def get_images(self):
        """
        get the info of images
        """

        images=self.glance_cs.images.list()

        result=[]
        for image in images:
            image_id=image.id
            image_name=image.name
            status=image.status
            max_size=int(max(image.min_disk, image.size, image.virtual_size)/(1024*1024))
            used_scale=0.5 #TODO:get the used_scale from the image properties
            result.append(ImageState(image_id, image_name, status, max_size, 0.5))

        return result


    def get_hosts(self):
        """
        get the info of hosts
        """
        #TODO:use nova api hypervisor instead to get detailed information about hosts 
        hosts=self.nova_cs.hosts.list()
        host_names=set([host.host_name for host in hosts])
        #TODO:cache_disk_ratio means how many mb disk is used for cache image.cache_disk_ratio can be set in conf file 
        cache_disk_ratio=0.1

        result=[]

        for hostname in host_names:
            info=self.nova_cs.hosts.get(hostname)
            total_disk_mb=info[0].disk_gb*1024
            used_disk_mb=info[1].disk_gb*1024
            max_cache_disk_mb=int((total_disk_mb-used_disk_mb)*cache_disk_ratio)
            host_info=HostState(hostname, max_cache_disk_mb) 
            result.append(host_info)
        
        return result


class ImageState(object):
    """
    encapsulate the image info
    """
    #TODO: Add more info about image to help the image filter or weigher
    def __init__(self, image_id, image_name, status, max_size, used_scale):
        """
        :param used_scale the ratio of used scale
        """
        self.image_id=image_id
        self.image_name=image_name
        self.status=status
        self.max_size=max_size
        self.used_scale=used_scale

class HostState(object):
    """
    encapsulate the host info
    """
    #TODO:add more info about host to help the image cache download
    def __init__(self, host_name, max_cache_disk_mb, cached_image_count=0):
        self.host_name=host_name
        self.max_cache_disk_mb=max_cache_disk_mb
        self.cached_image_count=cached_image_count        


