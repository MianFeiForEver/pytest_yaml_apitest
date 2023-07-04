# -*- coding: utf-8 -*-
from pathlib import Path

import oss2

from src.utils import is_folder, LocalDatatime, DirPath


def oss_upload_file(name, file):
    auth = oss2.Auth("123", "123")
    bucket = oss2.Bucket(
        auth,
        "https://oss-cn-beijing.aliyuncs.com",
        "1ddcc557-38af-436b-917d-7f41cd0b22ff",
    )

    with open(file, "rb") as file_obj:
        try:
            file_push = bucket.put_object(
                name, file_obj, headers={"Content-Type": "application/json"}
            )
            if file_push.status == 200:
                upload_url = (
                    "https://1ddcc557-38af-436b-917d-7f41cd0b22ff.oss-cn-beijing.aliyuncs.com/"
                    + name
                )
            file_obj.close()
        except Exception as e:
            print(e)
            return None
        else:
            print(upload_url)
            return upload_url


def last_file(file_path):
    name = path = None
    is_folder(file_path)
    file_list = [i for i in Path(file_path).iterdir()]
    if file_list:
        path = sorted(file_list, key=lambda x: x.stat().st_ctime)[-1]
        name = path.name
    return name, path


def upload_file(file_path):
    name, path = last_file(file_path)
    if name and path:
        return oss_upload_file(name, path)


class UploadLogs:
    def __init__(self):
        self.DirPath = DirPath()
        self.log_path = self.DirPath.logs_path
        self.monitor_path = self.DirPath.monitor_path
        self.html_path = self.DirPath.html_path

    def save_monitor(self, log_url):
        file_path = self.monitor_path + LocalDatatime().date() + ".txt"
        is_folder(self.monitor_path)
        with open(file_path, "a+") as file_obj:
            file_obj.write(f"LogUrl: {log_url}\n")
        file_obj.close()

    def up(self):
        log_url = upload_file(self.log_path)
        self.save_monitor(log_url)
        monitor_url = upload_file(self.monitor_path)
        html_url = upload_file(self.html_path)
        return log_url, monitor_url, html_url
