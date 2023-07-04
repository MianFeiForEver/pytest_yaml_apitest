import base64
import hashlib
import json
import socket
import subprocess
from datetime import datetime, timedelta, timezone
from pathlib import Path
from time import time

import pyotp
from configobj import ConfigObj
from faker import Faker
from jsonpath import jsonpath

from src.config import PARAMS, env_info, BasePath


def singleton(cls):
    _instance = {}

    def inner():
        if cls not in _instance:
            _instance[cls] = cls()
        return _instance[cls]

    return inner


date_time_format = "%Y-%m-%d-%H-%M-%S"


class LocalDatatime:
    """
    This class provides local date and time functionality.
    """

    @staticmethod
    def _format_time(format_str):
        """
        Formats a datetime object as a string.
        """
        bj_time = (
            datetime.utcnow()
            .replace(tzinfo=timezone.utc)
            .astimezone(timezone(timedelta(hours=8)))
        )
        return bj_time.strftime(format_str)

    def time(self):
        return self._format_time("%H:%M:%S")

    def date(self):
        return self._format_time("%Y-%m-%d")

    def datetime(self):
        return self._format_time(date_time_format)


def is_folder(path):
    if not Path(path).exists():
        Path(path).mkdir(parents=True, exist_ok=True)


def get_date():
    if date := get_value("date"):
        return date
    set_value("date", date := LocalDatatime().date())
    return date


def get_datetime():
    if date := get_value("datetime"):
        return date
    set_value("datetime", date := LocalDatatime().datetime())
    return date


def get_time():
    if date := get_value("time"):
        return date
    set_value("time", date := LocalDatatime().time())
    return date


@singleton
class DirPath:
    def __init__(self):
        self.project = env_info.get("project")
        self.base_dir = Path.cwd()
        self.config_path = self.base_dir / BasePath.config_path.value
        self.allure_path = self.base_dir / "allure-results"
        self.api_path = self.config_path / f"{self.project}/api"
        self.data_path = self.config_path / f"{self.project}/data"
        self.cases_dir = self.config_path / f"case/{self.project}/"
        self.case_path = self.config_path / f"{self.project}/case"
        self.logs_path = self.base_dir / BasePath.logs_path.value / f"{self.project}/{get_date()}/"
        self.log_path = self.logs_path / f"{get_datetime()}.log"
        self.monitor_path = self.base_dir / BasePath.monitor_path.value / f"{self.project}/{get_date()}"
        self.html_path = self.base_dir / BasePath.html_path.value / f"{self.project}/{get_date()}"
        self.files_path = self.base_dir / BasePath.files_path.value / f"{self.project}/{get_date()}"


def data_f(value, key=None):
    f = Faker(locale="zh_CN")

    def create_email():
        return str(int(round(time() * 10)))[1:] + "@1.lanhu"

    def create_uuid():
        return f.uuid4()

    def create_date():
        return datetime.now().strftime("%Y-%m-%d")

    def create_date_time():
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    def create_user_name():
        return f.user_name()

    def create_mobile():
        return "x" + str(int(round(time() * 10)))[1:]

    def create_password():
        return f.phone_number()

    def code():
        return create_code(get_value(key.get("mobile", "")))

    def create_timenow():
        return int(round(time() * 1000))

    actions = {
        "email": create_email,
        "uuid": create_uuid,
        "date": create_date,
        "date_time": create_date_time,
        "user_name": create_user_name,
        "mobile": create_mobile,
        "password": create_password,
        "code": code,
        "timenow": create_timenow,
    }

    if value in actions:
        return actions[value]()
    else:
        return None


def create_code(mobile):
    m = hashlib.md5()
    m.update(bytes(mobile.encode("utf8")))
    md5mobile = m.hexdigest()
    key = "MM3N7TG1ZDC8OJU1BC1TLG3HA1CIZ2UH"
    key += md5mobile
    totp = pyotp.TOTP(
        s=base64.b32encode(bytes(key.encode("utf8"))).decode("utf-8"), interval=30
    )
    return totp.now()


async def save_values(need_set: dict, client):
    if need_set:
        for key, path in need_set.items():
            if key == "cookie":
                value = client.session_cookie
            elif key == "plugin_token":
                base_token = str(client.res_to_json_path(path) + ":").encode("utf-8")
                value = f"Basic {base64.b64encode(base_token).decode('utf-8')}"
            else:
                if isinstance(path, list):
                    data = json.loads(client.res_to_json_path(path[0]))
                    value = jsonpath(data, path[1])[0]
                else:
                    value = client.res_to_json_path(path)
            set_value(key, value)


def set_value(key, value):
    if value not in [None, ""]:
        PARAMS.update({key: value})
    else:
        raise ValueError(f"{key} 不存在")


def update_value(data: dict):
    if isinstance(data, dict):
        PARAMS.update(data)


def get_value(key):
    value = PARAMS.get(key, "")
    return value if value else None


def get_info(key):
    return env_info.get(key)


def get_cookie():
    cookie = get_value("cookie")
    if cookie:
        return cookie


def get_token():
    return get_value("plugin_token")


def save_info(project, env, reporter):
    reporter = (
        "Jenkins"
        if reporter == "jenkins"
        else subprocess.getoutput("git config user.name") or socket.gethostname()
    )
    env_info.update({"project": project, "base_env": env, "reporter": reporter})
    config = ConfigObj("pytest.ini", encoding="UTF8")
    config["pytest"]["reporter"] = reporter
    config["pytest"]["project"] = project
    config["pytest"]["base_env"] = env
    config["pytest"]["testpaths"] = f"tests/{project}/case/"
    config["pytest"]["base_url"] = f'https://{env + "." if env else ""}lanhuapp.com/'
    config.write()
