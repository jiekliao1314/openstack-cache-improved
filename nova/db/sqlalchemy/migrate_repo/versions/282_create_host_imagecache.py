#jiekliao
#TODO: add more table arguments
from sqlalchemy import Boolean, Column, DateTime, Integer
from sqlalchemy import MetaData, String, Table
from oslo_log import log as logging

LOG = logging.getLogger(__name__)

def upgrade(migrate_engine):

    meta = MetaData()
    meta.bind = migrate_engine

    host_imagecache = Table('host_imagecache', meta,
            Column('id', Integer(), primary_key=True, nullable=False),
            Column('cache_id',String(255)),
            Column('host',String(255)),
            Column('survival_value', Integer()),
            Column('size', Integer()),

            Column('created_at', DateTime),
            Column('updated_at', DateTime),
            Column('deleted_at', DateTime),
            Column('deleted', Boolean), 
            mysql_engine='InnoDB',
            mysql_charset='utf8'
            )
    try:
        host_imagecache.create()
    except Exception, e:
        LOG.exception('Exception while creating host_imagecache table, error' % str(e))
        raise

def downgrade(migrate_engine):
    meta = MetaData()
    meta.bind = migrate_engine
    host_imagecache = Table('host_imagecache', meta, autoload=True)
    host_imagecache.drop()

