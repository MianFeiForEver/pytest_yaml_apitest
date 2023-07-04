import asyncio
import base64
import time
import types
from inspect import Parameter, Signature

import pytest

from src.case_util import replace_data, ApiInfo
from src.client import HttpClient
from src.config import req_results, LOG
from src.utils import (
    get_value,
    update_value,
    data_f,
    save_values,
    set_value,
    get_token,
    get_cookie,
)


class RunYaml(pytest.Item):
    """运行yaml"""

    def __init__(self, raw: dict, module: types.ModuleType, name, **kw):
        super().__init__(name, **kw)
        self.raw = raw  # 读取yaml 原始数据
        self.module: types.ModuleType = module  # 动态创建的 module 模型
        self.module_variable = {}  # 模块变量
        self.context = {}
        self.hooks = {}  # 全局hooks
        self.data_content = ApiInfo().case_data()
        self.dependencies = set()

    def collect_case(self):
        for function_name, data in self.raw.items():
            case_data = self.data_content.get(str(function_name).replace("test_", ""))
            title = data.get("title")
            config_fixtures = data.get("fixture", [])
            self.context.update(__builtins__)  # noqa 内置函数加载
            fixture = function_fixture(config_fixtures)
            depends = data.get("depends", {})

            f = create_test_function(
                name=function_name,
                func=self.send_request,
                fixture=fixture,
                depends=depends,
            )
            setattr(self.module, f"{function_name}_data", case_data)
            setattr(self.module, function_name, f)

    def send_request(self, args):
        value = args.get("value")
        data = value.get("data", {})
        params = value.get("params", {})
        need_get = value.get("get", {})
        need_set = value.get("set", {})
        api_name = value.get("api_name")
        generate = value.get("generate", {})
        if sleep_value := value.get("sleep", 0):
            time.sleep(sleep_value)
        # 更新请求参数中的变量
        up_dict = {}
        if generate:
            for key, val in generate.items():
                up_dict.update({key: data_f(val, need_get)})
            update_value(up_dict)
        for key, val in need_get.items():
            up_dict.update({key: get_value(val)})

        if calc := value.get("calc", {}):
            for key, val in calc.items():
                result = 1
                for i in val:
                    if isinstance(i, str):
                        result *= up_dict.get(i, 1)
                    else:
                        result *= i
                up_dict.update({key: result})
        if up_dict:
            data = replace_data(data, up_dict)
            if "$<" in str(data):
                print(up_dict)
                print("最终data", data)
                pytest.fail(f"请求失败，数据中有未知字符变量的计算值！")
            if params:
                for key in params.keys():
                    params.update({key: up_dict.get(key)} or params[key])

        # 发送请求
        if not api_name:
            raise ValueError("未填写api_name")
        cookie = None if not value.get("cookies", True) else get_cookie()
        authorization = (
            get_value("authorization") if value.get("authorization") else None
        )
        client = api(
            api_name=api_name,
            data=data,
            params=params,
            cookie=cookie,
            token=get_token(),
            authorization=authorization,
        )
        asyncio.run(save_req_result(api_name, value.get("info"), client))
        # 断言请求返回码
        if client.check_code_assertion(value):
            pass
        # 保存请求结果中的值
        asyncio.run(save_values(need_set, client))


def function_fixture(fixtures) -> list:
    """测试函数传 fixture"""
    # 测试函数的默认请求参数
    return [
        Parameter(fixture, Parameter.POSITIONAL_OR_KEYWORD)
        for fixture in ["value"] + fixtures
    ]


def create_test_function(name, func, fixture, depends):
    depends_name = depends.get("name")
    depends = depends.get("depends_on", [])

    @pytest.mark.dependency(name=depends_name, depends=depends)
    def test_function(**kwargs):
        func(kwargs)

    test_function.__signature__ = Signature(fixture)
    test_function.__name__ = name
    return test_function


async def save_req_result(api_name, value_info, client):
    info = {
        "address": client.url,
        "status": client.res.status_code,
        "times": client.res_times,
    }
    req_results.update({api_name: info})
    LOG.update({api_name + value_info: info})


def api(api_name, data=None, params=None, cookie=None, token=None, authorization=None):
    if data is None:
        data = {}
    url, method, body_type, project = ApiInfo().api_info(api_name, params)
    client = HttpClient(url=url, method=method, body_type=body_type)
    client.set_body(data)
    if authorization:
        client.set_header("authorization", authorization)
    if project != "plugin":
        client.set_cookie(cookie)
    else:
        client.set_header("authorization", token)
    client.send()
    return client


def Login():
    data = {"mobile_or_email": "QA@2022.lanhu", "password": "12345678"}
    client = api(api_name="login", data=data)
    ticket = client.res_to_json_path("$.data.ticket")
    set_value("uid", client.res_to_json_path("$.data.id"))
    auth(ticket, "login", "password")
    if not get_value("team_id_EE"):
        client = api(api_name="service_multi", cookie=get_value("cookie"))


def auth(ticket, action, action_type):
    data = {
        "request_from": "web",
        "sso_ticket": ticket,
        "action": action,
        "action_type": action_type,
    }
    client = api(api_name="auth", data=data)
    set_value("cookie", cookie := client.session_cookie)
    client = api(api_name="entry", cookie=cookie)
    base_token = str(client.res_to_json_path("$.token") + ":").encode("utf-8")
    token = f"Basic {base64.b64encode(base_token).decode('utf-8')}"
    set_value("authorization", token)
    return client