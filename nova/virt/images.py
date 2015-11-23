# Copyright 2010 United States Government as represented by the
# Administrator of the National Aeronautics and Space Administration.
# All Rights Reserved.
# Copyright (c) 2010 Citrix Systems, Inc.
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

"""
Handling of VM disk images.
"""
import os

from oslo_config import cfg
from oslo_log import log as logging

from nova import exception
from nova.i18n import _, _LE
from nova import image
from nova.openstack.common import fileutils
from nova.openstack.common import imageutils
from nova import utils

#liaojie
import hashlib

LOG = logging.getLogger(__name__)

image_opts = [
    cfg.BoolOpt('force_raw_images',
                default=True,
                help='Force backing images to raw format'),
]

CONF = cfg.CONF
CONF.register_opts(image_opts)
IMAGE_API = image.API()

def get_cache_id(image_id):
    """
    Return a filename based on the SHA1 hash of a given image ID.
    """
    return hashlib.sha1(image_id).hexdigest()

def qemu_img_info(path):
    """Return an object containing the parsed output from qemu-img info."""
    # TODO(mikal): this code should not be referring to a libvirt specific
    # flag.
    # NOTE(sirp): The config option import must go here to avoid an import
    # cycle
    CONF.import_opt('images_type', 'nova.virt.libvirt.imagebackend',
                    group='libvirt')
    if not os.path.exists(path) and CONF.libvirt.images_type != 'rbd':
        msg = (_("Path does not exist %(path)s") % {'path': path})
        raise exception.InvalidDiskInfo(reason=msg)

    out, err = utils.execute('env', 'LC_ALL=C', 'LANG=C',
                             'qemu-img', 'info', path)
    if not out:
        msg = (_("Failed to run qemu-img info on %(path)s : %(error)s") %
               {'path': path, 'error': err})
        raise exception.InvalidDiskInfo(reason=msg)

    return imageutils.QemuImgInfo(out)


def convert_image(source, dest, out_format, run_as_root=False):
    """Convert image to other format."""
    cmd = ('qemu-img', 'convert', '-O', out_format, source, dest)
    utils.execute(*cmd, run_as_root=run_as_root)


def fetch(context, image_href, path, _user_id, _project_id, max_size=0):
    with fileutils.remove_path_on_error(path):
        IMAGE_API.download(context, image_href, dest_path=path)


def get_info(context, image_href):
    return IMAGE_API.get(context, image_href)


def fetch_to_raw(context, image_href, path, user_id, project_id, max_size=0):
    path_tmp = "%s.part" % path
    fetch(context, image_href, path_tmp, user_id, project_id,
          max_size=max_size)

    with fileutils.remove_path_on_error(path_tmp):
        data = qemu_img_info(path_tmp)

        fmt = data.file_format
        if fmt is None:
            raise exception.ImageUnacceptable(
                reason=_("'qemu-img info' parsing failed."),
                image_id=image_href)

        backing_file = data.backing_file
        if backing_file is not None:
            raise exception.ImageUnacceptable(image_id=image_href,
                reason=(_("fmt=%(fmt)s backed by: %(backing_file)s") %
                        {'fmt': fmt, 'backing_file': backing_file}))

        # We can't generally shrink incoming images, so disallow
        # images > size of the flavor we're booting.  Checking here avoids
        # an immediate DoS where we convert large qcow images to raw
        # (which may compress well but not be sparse).
        # TODO(p-draigbrady): loop through all flavor sizes, so that
        # we might continue here and not discard the download.
        # If we did that we'd have to do the higher level size checks
        # irrespective of whether the base image was prepared or not.
        disk_size = data.virtual_size
        if max_size and max_size < disk_size:
            LOG.error(_LE('%(base)s virtual size %(disk_size)s '
                          'larger than flavor root disk size %(size)s'),
                      {'base': path,
                       'disk_size': disk_size,
                       'size': max_size})
            raise exception.FlavorDiskTooSmall()

        if fmt != "raw" and CONF.force_raw_images:
            staged = "%s.converted" % path
            LOG.debug("%s was %s, converting to raw" % (image_href, fmt))
            with fileutils.remove_path_on_error(staged):
                convert_image(path_tmp, staged, 'raw')
                os.unlink(path_tmp)

                data = qemu_img_info(staged)
                if data.file_format != "raw":
                    raise exception.ImageUnacceptable(image_id=image_href,
                        reason=_("Converted to raw, but format is now %s") %
                        data.file_format)

                os.rename(staged, path)
        else:
            os.rename(path_tmp, path)


#liaojie
def fetch_to_qcow2(context, image_href,path, user_id, project_id, max_size=0):
    path_tmp = "%s.part" % path
    fetch(context, image_href, path_tmp, user_id, project_id,
          max_size=max_size)

    with fileutils.remove_path_on_error(path_tmp):
        data = qemu_img_info(path_tmp)

        fmt = data.file_format
        if fmt is None:
            raise exception.ImageUnacceptable(
                reason=_("'qemu-img info' parsing failed."),
                image_id=image_href)
        
        disk_size = data.virtual_size
        if max_size and max_size < disk_size:
            LOG.error(_LE('%(base)s virtual size %(disk_size)s '
                          'larger than flavor root disk size %(size)s'),
                      {'base': path,
                       'disk_size': disk_size,
                       'size': max_size})
            raise exception.FlavorDiskTooSmall()

        if fmt != "qcow2":
            staged = "%s.converted" % path
            LOG.debug("%s was %s, converting to qcow2" % (image_href, fmt))
            with fileutils.remove_path_on_error(staged):
                convert_image(path_tmp, staged, 'qcow2')
                os.unlink(path_tmp)

                data = qemu_img_info(staged)
                if data.file_format != "qcow2":
                    raise exception.ImageUnacceptable(image_id=image_href,
                        reason=_("Converted to qcow2, but format is now %s") %
                        data.file_format)

                os.rename(staged, path)
        else:
            os.rename(path_tmp, path)

#liaojie
def fetch_to_all(context, image_href, path, user_id, project_id, host_imagecache_manager, max_size=0):
    """
    fetch the image_href and its backing file 
    used in building instance
    """
    #get info of backfile
    image_meta=IMAGE_API.get(context, image_href)
    backfile_href=image_meta['properties'].get('base_id', None)
    if backfile_href:
        backfile_filename=hashlib.sha1(backfile_href).hexdigest()
        backfile_path=os.path.join(os.path.dirname(path), backfile_filename)
    
    #1.check and download image_href's backing_file
    if backfile_href and not os.path.exists(backfile_path):
        fetch_to_raw(context, backfile_href, backfile_path, user_id, project_id, max_size)

    #2.check and download image_href
    if not os.path.exists(path):
        if backfile_href:
            fetch_to_qcow2(context, image_href, path, user_id, project_id, max_size)
            #3.rebase image_href
            cmd = ('qemu-img', 'rebase', '-u', '-b', backfile_path, path)
            utils.execute(*cmd, run_as_root=False)
        else:
            fetch_to_raw(context, image_href, path, user_id, project_id, max_size)
            
    #3.update the image cache 
    ignore_imagecaches=[]
    cache_id=get_cache_id(image_href)
    host_imagecache_manager.update_imagecache(context, 
                                cache_id,
                                image_meta['properties'].get('max_size', 0))
    ignore_imagecaches.append(cache_id)
    if backfile_href:
        backfile_image_meta=IMAGE_API.get(context, backfile_href)
        host_imagecache_manager.update_imagecache(context, 
                                    backfile_filename,
                                    backfile_image_meta['properties'].get('max_size', 0))
        ignore_imagecaches.append(backfile_filename)

    #4.check and remove old image cache
    host_imagecache_manager.check_or_remove_imagecache(context, ignore_imagecaches)

#liaojie
def fetch_to_cache(context, image_href, path, host_imagecache_manager) :
    """
    fetch the image_href and cache it 
    used in cache pre-fetching
    """
    def fetch_and_convert(context, image_href, path, image_fmt):
        path_tmp = "%s.part" % path
        #fetch image
        with fileutils.remove_path_on_error(path_tmp):
            IMAGE_API.download(context, image_href, dest_path=path_tmp)
        #convert image
        with fileutils.remove_path_on_error(path_tmp):
            data = qemu_img_info(path_tmp)

            fmt = data.file_format
            if fmt is None:
                raise exception.ImageUnacceptable(
                    reason=_("'qemu-img info' parsing failed."),
                    image_id=image_href)
            
            if fmt != image_fmt:
                staged = "%s.converted" % path
                with fileutils.remove_path_on_error(staged):
                    convert_image(path_tmp, staged, image_fmt)
                    os.unlink(path_tmp)

                    data = qemu_img_info(staged)
                    if data.file_format != image_fmt:
                        raise exception.ImageUnacceptable(image_id=image_href,
                            reason=_("Converted to %s, but format is now %s") %
                            (image_fmt, data.file_format))

                    os.rename(staged, path)
            else:
                os.rename(path_tmp, path)

    image_meta=IMAGE_API.get(context, image_href)
    backfile_href=image_meta['properties'].get('base_id', None)
    if backfile_href:
        #app image:download to qcow2 and rebase 
        fetch_and_convert(context, image_href, path, "qcow2")
        backfile_filename=hashlib.sha1(backfile_href).hexdigest()
        backfile_path=os.path.join(os.path.dirname(path), backfile_filename)
        cmd = ('qemu-img', 'rebase', '-u', '-b', backfile_path, path)
        utils.execute(*cmd, run_as_root=False)
    else:
        #base image:download to raw
        fetch_and_convert(context, image_href, path, "raw")
    #update the imagecache db 
    #TODO:how to get the size
    host_imagecache_manager.update_imagecache(context, 
                                get_cache_id(image_href),
                                image_meta['properties'].get('max_size', 0))
