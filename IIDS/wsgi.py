"""
WSGI config for IIDS project.

It exposes the WSGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/5.1/howto/deployment/wsgi/
"""
import logging
import os

from django.core.wsgi import get_wsgi_application

from IIDS import settings


# 启动日志监听器
def start_logging_listener():
    from queue import Queue
    log_queue = settings.log_queue  # 从settings中获取队列

    # 配置文件日志处理器
    log_file_handler = logging.handlers.RotatingFileHandler(
        filename=os.path.join(settings.BASE_LOG_DIR, 'taskLog.log'),
        maxBytes=1024 * 1024 * 20,  # 文件最大20MB
        backupCount=5,
        encoding='utf-8',
    )
    log_file_handler.setFormatter(logging.Formatter(
        '[%(asctime)s][%(levelname)s][%(filename)s:%(lineno)d:%(funcName)s]：%(message)s'
    ))

    # 启动队列监听器
    listener = logging.handlers.QueueListener(log_queue, log_file_handler)
    listener.start()

    plc_queue = settings.plc_queue  # 从settings中获取队列

    # 配置文件日志处理器
    plc_log_file_handler = logging.handlers.RotatingFileHandler(
        filename=os.path.join(settings.BASE_LOG_DIR, 'plcLog.log'),
        maxBytes=1024 * 1024 * 20,  # 文件最大20MB
        backupCount=5,
        encoding='utf-8',
    )
    plc_log_file_handler.setFormatter(logging.Formatter(
        '[%(asctime)s][%(levelname)s][%(filename)s:%(lineno)d:%(funcName)s]：%(message)s'
    ))

    # 启动队列监听器
    plc_listener = logging.handlers.QueueListener(plc_queue, plc_log_file_handler)
    plc_listener.start()

# 启动日志监听器
start_logging_listener()

# 只在主进程（Django 启动进程）中启动定时任务
if os.environ.get('RUN_MAIN'):
    from tasks.task import start_scheduler

    # 启动 APScheduler
    start_scheduler()

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'IIDS.settings')

application = get_wsgi_application()
