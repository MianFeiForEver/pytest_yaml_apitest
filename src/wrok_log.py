#! /usr/bin/env python3
# -*- coding: UTF-8 -*-

# import logging

from loguru import logger

from src.utils import DirPath


class RunningLog(object):
    """
    log_file_path: 日志生成存放路径；
    参数为 None 时 目标 py 文件在根目录下的文件夹内时使用；
    参数为 1 时 目标 py 文件直接在根目录下时使用；
    日志命名为当前本地时间；
    formatter: 单行日志打印参数与样式，具体参数说明请看 Formatter 模块注释。
    """

    #
    def __init__(self, log_file_path=DirPath().log_path):
        self.logger = logger
        self.logger.remove()  # 移除默认的 handler
        log_path = log_file_path
        self.logger.add(
            log_path,
            format="{time:YYYY-MM-DD HH:mm:ssZZ} | {level} | {message}",
            level="INFO",
            retention="10 days",
        )

    def get_logger(self):
        return self.logger
