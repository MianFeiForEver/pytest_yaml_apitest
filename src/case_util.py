import argparse
import re
import subprocess
from pathlib import Path
from string import Template

from ruamel.yaml import YAML

from .utils import set_value, DirPath, singleton, get_value, get_base_url


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

    def api_info(self, name, params):
        api = self.api_data().get(name)
        api_path = api.get("address")
        api_project = api.get("project", "")
        base_url = get_base_url()
        url = base_url + Template(api_path).safe_substitute(params)
        method = api.get("method")
        body_type = api.get("body_type", "")
        return url, method, body_type, api_project


def param():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--u",
        default="https://pdp-test00.lanhuapp.com"
    )
    parser.add_argument("--m", default="all", choices=["all", "monitor", "MON"])
    return parser.parse_args()


# 封装执行shell语句方法
def shell_invoke():
    cmd = "allure generate ./allure-results -o ./local-reports --clean"
    output, errors = subprocess.Popen(
        cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE
    ).communicate()
    output.decode("utf-8")
