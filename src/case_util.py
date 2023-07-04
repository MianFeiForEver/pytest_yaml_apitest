import argparse
import re
import subprocess
from pathlib import Path
from string import Template

from ruamel.yaml import YAML

from .config import env_info
from .utils import set_value, DirPath, singleton, get_value


def replace_data(data, up_dict):
    if "$<" not in str(data):
        return data
    pattern = r"\$\<(\w+)\>"
    if isinstance(data, list):
        data = [replace_data(value, up_dict) for value in data]
    elif isinstance(data, dict):
        data = {
            replace_data(key, up_dict): replace_data(value, up_dict)
            for key, value in data.items()
        }
    elif isinstance(data, str):
        matches = re.findall(pattern, data)
        for match in matches:
            if match in up_dict:
                replace_value = up_dict[match]
                if isinstance(replace_value, str):
                    data = data.replace(f"$<{match}>", replace_value)
                else:
                    data = replace_value
    return data


def load(path):
    with open(path, encoding="utf-8") as f:
        yaml = YAML(typ="safe")
        return yaml.load(f)


def files_list(file_dir):
    return [i for i in Path(file_dir).iterdir()]


def load_dir(file_dir):
    data = dict()
    for path in files_list(file_dir):
        x = load(path)
        if x:
            data.update(x)
    return data


@singleton
class ApiInfo:
    """接口信息"""

    def __init__(self):
        self.data_path = DirPath().data_path
        self.case_path = DirPath().case_path
        self.api_path = DirPath().api_path

    @staticmethod
    def case_data():
        return get_value("data_content")

    @staticmethod
    def api_data():
        return get_value("api_content")

    def load_all_data(self):
        set_value("data_content", load_dir(self.data_path))
        set_value("api_content", load_dir(self.api_path))

    @staticmethod
    def get_base_url(api_path="", api_project=""):
        project = env_info.get("project")
        base_env = env_info.get("base_env", "www-cicd-test.develop")
        if project == "saas":
            base_url = saas_base_url(base_env, api_project)
        elif project == "project1":
            base_url = base_url1(base_env, api_project)
        elif project == "project2":
            base_url = base_url2(base_env, api_path)
        else:
            base_url = saas_base_url(base_env, api_project)
        set_value("base_url", base_url)
        return base_url

    def api_info(self, name, params):
        api = self.api_data().get(name)
        api_path = api.get("address")
        api_project = api.get("project", "")
        base_url = self.get_base_url(api_path, api_project)
        url = base_url + Template(api_path).safe_substitute(params)
        method = api.get("method")
        body_type = api.get("body_type", "")
        return url, method, body_type, api_project


def base_url1(base_env, api_project):
    def host_path(key):
        base = {
            "passport": {
                "online": "sso"
            },
        }
        if base_env in [""]:
            _host_path = base.get(key).get("online")
        else:
            _host_path = base.get(key).get(base_env)
        return _host_path

    if api_project:
        base_env = host_path(api_project)
    if base_env:
        base_env += "."
    return f"https://{base_env}demo.com"


def base_url2(base_env, api_path):
    if base_env in [""]:
        if "/demo" in api_path:
            base_env = "demo"

    return f"https://{base_env}.demo.com"


def saas_base_url(base_env, api_project):
    def host_path(key):
        base = {
            "plugin": {
                "online": "plugin-api",
            },

        }
        if base_env in [""]:
            _host_path = base.get(key).get("online")
        else:
            _host_path = base.get(key).get(base_env)
        return _host_path

    if api_project:
        base_env = host_path(api_project)
    if base_env:
        base_env += "."
    return f"https://jsonplaceholder.typicode.com"


def param():
    parser = argparse.ArgumentParser()
    parser.add_argument("--p", default="saas", choices=["saas", "project1", "project2"])
    parser.add_argument(
        "--e",
        default="",
        choices=[
            "",
        ],
    )
    parser.add_argument("--m", default="all", choices=["all", "monitor", "MON"])
    parser.add_argument("--r", default=None)
    return parser.parse_args()


# 封装执行shell语句方法
def shell_invoke():
    cmd = "allure generate ./allure-results -o ./local-reports --clean"
    output, errors = subprocess.Popen(
        cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE
    ).communicate()
    output.decode("utf-8")
