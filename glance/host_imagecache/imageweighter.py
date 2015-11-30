#liaojie
#This is obsolete
class ImageWeighter(object):
    """
    one of weighters.
    weight and sort hosts by their cached_image_count 
    """
    def __init__(self,hosts):
        self.hosts={}
        for host in hosts:
            self.hosts[host.host_name]=host

    def get_weighted_hosts(self, host_names):
        """
        sort the host_name by score
        """
        def get_score(host_name):
            return self.hosts[host_name].cached_image_count

        def comp(host1, host2):
            return get_score(host1) - get_score(host2)

        return sorted(host_names, cmp=comp)

