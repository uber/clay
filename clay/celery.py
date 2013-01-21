from __future__ import absolute_import
from celery import Celery
from clay import config


log = config.get_logger('clay.celery')

celery = Celery(log=log)
celery.config_from_object(config.get('celery'))


def main():
    '''
    Run a celery worker process
    '''
    celery.worker_main()


if __name__ == '__main__':
    main()
