import json
import uuid
from datetime import datetime

from src.config import env_info, results, req_results, report_msg, FeiShu
from src.case_util import replace_data
from src.client import HttpClient
from src.core.oss_log import UploadLogs
from src.utils import get_value, set_value


def timeout_text():
    timeout_list = [
        f"{key}: {times}ms"
        for key, value in req_results.items()
        if (times := value.get("times")) > 2000
    ]
    timeout_str = ""
    if timeout_num := len(timeout_list):
        timeout_str = "\n".join(timeout_list)
        timeout_str = f"\n有 **{timeout_num}** 个接口请求超过2000ms：\n{timeout_str}\n"
        if timeout_num > 1:
            set_at()
    return timeout_str


def boom_text():
    boom_list = [
        f"{key}: {status}"
        for key, value in req_results.items()
        if (status := value.get("status")) // 500 == 1
    ]

    boom_str = ""
    if boom_num := len(boom_list):
        boom_str = "\n".join(boom_list)
        boom_str = f"\n有 **{boom_num}** 个接口5XX：\n{boom_str}\n"
        set_value("urgent", True)
        set_at()
    return boom_str


def set_at():
    set_value("at", True)


def at():
    if get_value("at"):
        at_text = "\n"
        user_dict = FeiShu().urgent_list.get(env_info["project"])
        for uid, name in user_dict.items():
            at_text += f"<at id='{uid}'>{name}</at>"
        return at_text
    return ""


def report_address():
    return f"{report_msg.get('address')}api_test_{env_info['project']}/allure/"


class SendReport:
    def __init__(self):
        self.elements = []
        self.status = []
        self.log_url, self.monitor_url, self.html_url = UploadLogs().up()
        self.result = results

    def case_stats(self):
        for stats, case_list in self.result.get("stats").items():
            if stats not in ["passed", "warnings"] and case_list:
                if case_list:
                    text = f"\n".join(
                        [i.location[-1] + f": {stats}" for i in case_list]
                    )
                    self.elements.append({"tag": "markdown", "content": text})
            elif stats == "warnings" and case_list:
                print(case_list)

    def com_text(self):
        passed = self.result.get("count").get("passed")
        failed = self.result.get("count").get("failed")
        total = self.result["total"] if self.result["total"] else 1
        host_name = env_info["reporter"]
        com_text = f"用例总数：{total}  成功条数：{passed}  失败条数：{failed}  成功率：{passed / total * 100:.2f}%"
        com_text += f" \n执行时间: {self.result.get('duration')} 秒"
        com_text += f" \n执行人: {host_name}"
        if failed:
            set_at()
        return com_text

    def com_elements(self):
        self.case_stats()
        summary = self.com_text() + boom_text() + timeout_text() + at()
        project = env_info["project"]
        base_env = env_info["base_env"] or "online"
        self.elements.extend(
            [
                {
                    "tag": "markdown",
                    "content": "\n --------------\n",
                },
                {
                    "tag": "markdown",
                    "content": f"项目：{project}\n环境：{base_env}\n" + summary,
                },
                {
                    "tag": "markdown",
                    "content": f"[点击查看：测试日志]({self.log_url}) [完整测试报告]({report_address()})",
                },
            ]
        )
        return self.elements

    def send_qa_report(self):
        base_url = "http://39.105.181.226:5000/"
        api_path = "/addRunHistory.json"
        url = base_url + api_path
        error_num = self.result.get("count").get("failed")
        project_type, module, env = report_info()
        data = {
            "type": project_type,
            "module": module,
            "result_status": 1 if error_num else 0,
            "total_case": self.result.get("total"),
            "error_num": error_num,
            "result_txt": self.log_url,
            "result_html": self.html_url,
            "env": env,
        }

        client = HttpClient(url=url, method="post", body_type="json", session=None)
        client.set_body(data)
        client.send()

    def send_feishu_report(self):
        headers = {"Authorization": f'Bearer {get_value("tenant_access_token")}'}
        value = {
            "config": {"wide_screen_mode": True, "enable_forward": True},
            "elements": self.com_elements(),
            "header": {
                "title": {
                    "content": f"{datetime.today().date()} 接口测试报告",
                    "tag": "plain_text",
                }
            },
        }
        config = FeiShu()
        data = {
            "content": json.dumps(value),
            "msg_type": "interactive",
            "receive_id": config.chat_id,
            "uuid": uuid.uuid4().hex,
        }

        client = HttpClient(url=config.messages_url, method="post")
        client.set_body(data)
        client.set_headers(headers)
        client.send()
        set_value("message_id", client.get_json_value("$.data.message_id"))

    def send_report(self):
        get_access_token()
        self.send_feishu_report()
        urgent_app()
        # self.send_qa_report()


def urgent_app():
    if get_value("urgent") and env_info.get("env", "") not in ["pre", ""]:
        config = FeiShu()
        headers = {"Authorization": f'Bearer {get_value("tenant_access_token")}'}
        url = replace_data(
            config.urgent_app_url, {"message_id": get_value("message_id")}
        )
        user_dict = config.urgent_list.get(env_info["project"])
        data = {"user_id_list": list(user_dict.keys())}
        client = HttpClient(url=url, method="patch", data=json.dumps(data))
        client.set_headers(headers)
        client.send()


def get_access_token():
    config = FeiShu()
    data = {"app_id": config.app_id, "app_secret": config.app_secret}
    client = HttpClient(url=config.tenant_access_token_url, method="post")
    client.set_body(data)
    client.send()
    tenant_access_token = client.res_to_json_path("$.tenant_access_token")
    set_value("tenant_access_token", tenant_access_token)


def report_info():
    project = env_info["project"]
    base_env = env_info["base_env"]
    if project == "saas":
        project_type = "1"
        module = "主站 API"
        env = {"zz-test": "test", "pre": "pre", "": "online"}.get(base_env)
    elif project == "ts":
        project_type = "4"
        module = "TS API"
        env = {"zz-test": "test", "pre": "pre", "": "online"}.get(base_env)
    else:
        project_type = "3"
        module = "私有化 API"
        env = {"zz-test": "test", "pre": "pre", "": "online"}.get(base_env)
    return project_type, module, env
