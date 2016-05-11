#jiekliao


from oslo_log import log as logging
import webob.exc

from nova.api.openstack import extensions
from nova import compute
from nova import context as nova_context
from nova import exception
from nova.i18n import _
from nova.i18n import _LI
from nova import objects

from nova.compute import rpcapi as compute_rpcapi

LOG = logging.getLogger(__name__)


class HostImageCacheController(object):
    """The ComputeCache API controller for the OpenStack API."""
    def __init__(self):
        self.host_api = compute.HostAPI()
        self.compute_rpcapi=compute_rpcapi.ComputeAPI()
        super(HostImageCacheController, self).__init__()

    def create(self, req, body):
        #NOTE:get the context
        context = req.environ['nova.context']
        #NOTE: nova policy authrize ,now ignore it
        #authorize(context)
        #nova_context.require_admin_context(context)

        try:
            host=body['host_name']
            image_ids=body['image_ids']
        except (TypeError, KeyError) as ex:
            msg = _("Invalid request body: %s") % ex
            raise webob.exc.HTTPBadRequest(explanation=msg)

        #NOTE:we use the host_api get the host info like the hypervisor in nova-api
        compute_nodes = self.host_api.compute_node_get_all(context)
        local_hosts=[]
        for compute_node in compute_nodes:
            local_hosts.append(compute_node['host'])
        if host not in local_hosts:
            msg=_("Can't find the host %s to cache image") % host
            raise webob.exc.HTTPBadRequest(explanation=msg)

        for image_id in image_ids:
            #NOTE:now we use nova-compute cast to realize the concurrence
            self.compute_rpcapi.cache_host_image(context, host, image_id)
            #NOTE:now we can just use dbgp test only one image cache processing 
            #break

        #TODO:now just return original data for testing
        response_body={}
        response_body['host_imagecache']={
                'hostname':body['host_name'],
                'image_ids':body['image_ids']
                }
        return response_body
    
    def index(self, req):
        pass

    def update(self, req, id, body):
        pass

    def show(self, req, id):
        pass 

class Host_imagecache(extensions.ExtensionDescriptor):
    """compute cache"""

    name = "HostImageCache"
    alias = "host-imagecache"
    namespace = ""
    updated = ""

    def get_resources(self):
        resources = [extensions.ResourceExtension('host-imagecache',
                HostImageCacheController(),
                collection_actions={},
                member_actions={})]
        return resources
