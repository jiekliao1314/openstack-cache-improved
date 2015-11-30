#liaojie
#This is obsolete
class DiskFilter(object):
    """
    one of filters.
    filt the host by disk size
    """
    def __init__(self, hosts):
        self.hosts=hosts

    def get_filtered_hosts(self, image):
        """
        return filtered host name by image
        """
        result=[]
        for host in self.hosts:
            if host.max_cache_disk_mb >= image.max_size:
                result.append(host.host_name)

        return result


