import json
import random
import string

import allure
import curlify
import pytest
import requests
import urllib3
from jsonpath import jsonpath
from requests_toolbelt import MultipartEncoder

from .case_util import replace_data
from .config import PARAMS
from .utils import DirPath

urllib3.disable_warnings()


class BodyType(object):
    URL_ENCODE = "url-encode"
    JSON = "json"
    XML = "xml"
    FILES = "form-data"


class Method(object):
    GET = "get"
    POST = "post"
    PUT = "put"
    DELETE = "delete"
    PATCH = "patch"


class HttpClient(object):
    def __init__(
            self, url, data=None, session=None, method="GET", body_type="json", timeout=30
    ):
        self.url = url
        self.method = method
        self.timeout = timeout
        self.body_type = body_type
        self.headers = {"User-From": "testing"}
        self.body = data
        self.res = None
        self.flag = 0
        self.act = None
        self.session = session if session else requests.session()

    def save_session(self):
        PARAMS["session"] = self.session

    def set_header(self, key, value):
        self.headers[key] = value

    def set_headers(self, dic):
        if dic is not None:
            if isinstance(dic, dict):
                self.headers.update(dic)
            else:
                raise Exception("请求头请以字典格式传递")

    def set_cookie(self, dic: dict):
        if dic:
            if isinstance(dic, dict):
                lis = [f"{k}={v}" for k, v in dic.items()]
                cookie_str = ";".join(lis)
                self.set_headers(
                    {"cookie": self.headers.get("cookie", "") + cookie_str}
                )
            else:
                print(Exception("Cookie请以字典格式传递"))

    def set_body(self, data):
        self.body = data

    def requests_value(self):
        requests_value = {}
        if self.method == Method.GET:
            requests_value = {"params": self.body}
        elif self.method == Method.PATCH:
            self.set_header("Content-Type", "application/json")
            requests_value = {"data": self.body}
        elif self.method == Method.PUT:
            requests_value = {"json": self.body}
        elif self.method == Method.DELETE:
            requests_value = {"json": self.body}
        elif self.method == Method.POST:
            if self.body_type == BodyType.URL_ENCODE:
                self.set_header("Content-Type", "application/x-www-form-urlencoded")
                requests_value = {"data": self.body}
            elif self.body_type in [BodyType.JSON, ""]:
                self.set_header("Content-Type", "application/json")
                requests_value = {"json": self.body}
            elif self.body_type == BodyType.XML:
                self.set_header("Content-Type", "text/xml")
                requests_value = {"data": self.body}
            elif self.body_type == BodyType.FILES:
                files_path = self.body["files"]
                self.body["save_par"] = json.dumps(self.body["save_par"])
                self.body["auth_par"] = json.dumps(self.body["auth_par"])
                self.body["files"] = (
                    files_path,
                    open(DirPath().files_path / files_path, "rb"),
                    "image/png",
                )
                boundary = "----WebKitFormBoundary" + "".join(
                    random.sample(string.ascii_letters + string.digits, 16)
                )
                m = MultipartEncoder(fields=self.body, boundary=boundary)
                self.headers.update({"Content-Type": m.content_type})
                requests_value = {"data": m}
        else:
            raise Exception("不支持的请求方法类型", self.method)
        requests_value.update(
            {
                "url": self.url,
                "timeout": self.timeout,
                "method": self.method,
                "headers": self.headers,
                "verify": False,
            }
        )
        return requests_value

    def send(self):
        requests_value = self.requests_value()
        try:
            self.res = self.session.request(**requests_value)
        except Exception as e:
            raise Exception(f"请求发送失败--self.url ", e)
        try:
            with allure.step("请求信息"):
                allure.attach(self.url, name="请求地址")
                allure.attach(self.method, name="请求方法")
                allure.attach(str(self.headers), "请求头")
                if self.body_type != BodyType.FILES:
                    if self.body:
                        allure.attach(
                            json.dumps(self.body, ensure_ascii=False, indent=4),
                            name="请求参数",
                            attachment_type=allure.attachment_type.JSON,
                        )
                    allure.attach(curlify.to_curl(self.res.request), name="CURL")
                allure.attach(f"{self.res.status_code}", name="响应状态码")
                allure.attach(f"{self.res_times}毫秒", name="响应时间")
                if "application/json" in self.res.headers.get("Content-Type"):
                    allure.attach(
                        json.dumps(self.res.json(), ensure_ascii=False, indent=4),
                        name="响应内容",
                        attachment_type=allure.attachment_type.JSON,
                    )
                elif self.res.text:
                    allure.attach(
                        self.res.text,
                        name="响应内容",
                        attachment_type=allure.attachment_type.TEXT,
                    )
        except Exception as e:
            print("step记录异常", e)

    @property
    def session_cookie(self):
        return requests.utils.dict_from_cookiejar(self.session.cookies)

    @property
    def res_cookiejar_cookies(self):
        return requests.utils.dict_from_cookiejar(self.res.cookies)

    @property
    def res_times(self):
        if self.res is not None:
            return round(self.res.elapsed.total_seconds() * 1000)
        else:
            print("响应为空")
            return 100000

    @property
    def res_json(self):
        return self.res.json()

    def res_to_json_path(self, path, index=0):
        if isinstance(path, list):
            path, index = path
        a = self.res.json()
        if a is not None:
            result = jsonpath(a, path)[index]
            if isinstance(result, dict):
                return json.dumps(result, ensure_ascii=False, indent=4)
            return result

    def res_to_json_paths(self, path):
        a = self.res.json()
        if a is not None:
            return jsonpath(a, path)

    # 断言
    def check_status_code(self, exp):
        if exp:
            act = self.res.status_code
            with pytest.assume:
                assert act // 500 != 1, f"接口状态码{act}"
                assert act == exp, f"响应状态码错误：实际结果{act}, 预期结果{exp}"
            return act == exp

    def check_times_less_than(self, exp):
        act = self.res_times
        with pytest.assume:
            assert act < exp, f"响应超时：实际结果{act}ms, 预期结果小于{exp}ms"

    def check_text_equal(self, exp):
        act = self.res.txt
        with pytest.assume:
            assert act == exp, f"响应内容错误：实际结果{act}, 预期结果{exp}"

    def check_text_contains(self, exp):
        act = self.res.txt
        with pytest.assume:
            assert exp in act, f"响应内容错误：实际结果{act}, 预期结果{exp}"

    def get_json_value(self, path, index=0):
        a = self.res.json()
        if a is not None:
            act_list = jsonpath(a, path)
            if act_list:
                if index == 0:
                    r_index = random.randint(0, len(act_list) - 1)
                    act = act_list[r_index]
                else:
                    act = act_list[index - 1]
                return act
            else:
                with pytest.assume:
                    assert False, f" {path}json值不存在"
        else:
            with pytest.assume:
                assert False, "响应非正确的json格式: \n" + self.res.txt

    def check_json_paths(self, assertion: dict):
        if assertion is None:
            return True
        result = True
        with allure.step("返回值断言"):
            for path, value in assertion.items():
                act = self.get_json_value(f"$.{path}")
                result = False
                if value is not None:
                    if isinstance(value, list):
                        values = [
                            replace_data(i, PARAMS) if str(i).startswith("$<") else i
                            for i in value
                        ]
                        with pytest.assume:
                            assert act in values, f"响应内容错误：实际结果{act}, 预期结果{value}"
                            result = True
                        allure.attach(f"实际结果:{act},预期结果:{values}", name=path)
                    else:
                        if value == "exist":
                            act = "exist" if act else "not exist"
                        if str(value).startswith("$<"):
                            value = replace_data(value, PARAMS)
                        with pytest.assume:
                            assert act in [
                                value,
                                str(value),
                            ], f"响应内容错误：实际结果{act}, 预期结果{value}"
                            result = True
                        allure.attach(f"实际结果:{act},预期结果:{value}", name=path)

            return result

    def check_code_assertion(self, value):
        return self.check_status_code(value.get("status", 200)) and (
            self.check_json_paths(value.get("assertion"))
        )
