import base64
import types
from pathlib import Path

import jmespath
import pytest
from _pytest.python import Module
from jsonpath import jsonpath

from src.case_util import load, ApiInfo
from src.config import results, LOG
from src.runner import RunYaml, api
from src.utils import time, get_value, set_value, data_f
from src.wrok_log import RunningLog

logger = RunningLog().get_logger()


def pytest_collection_modifyitems(items) -> None:
    # item表示每个测试用例，解决用例名称中文显示问题
    for item in items:
        item.name = item.name.encode().decode("unicode-escape")
        item._nodeid = item._nodeid.encode().decode("unicode-escape")


def pytest_sessionstart():
    ApiInfo().load_all_data()


def pytest_collect_file(file_path: Path, parent):  # noqa
    if file_path.suffix == ".yaml":
        py_module = Module.from_parent(parent, path=file_path)
        # 动态创建 module
        module = types.ModuleType(file_path.stem)
        # 解析 yaml 内容
        yam_content = load(file_path)
        name = module.__name__
        if yam_content:
            run = RunYaml.from_parent(parent, raw=yam_content, module=module, name=name)
            run.collect_case()
            # 重写属性
            py_module._getobj = lambda: module  # noqa
            return py_module


def pytest_generate_tests(metafunc):  # noqa
    """测试用例参数化功能实现"""
    params_data = getattr(metafunc.module, f"{metafunc.function.__name__}_data")
    # 获取测试用例参数化数据
    if params_data:
        metafunc.parametrize("value", params_data,
                             ids=[value.get("info") for value in params_data],
                             scope="function")


@pytest.hookimpl(hookwrapper=True, tryfirst=True)
def pytest_runtest_makereport(item):
    # 获取钩子方法的调用结果
    out = yield
    # 从钩子方法的调用结果中获取测试报告
    report = out.get_result()
    if report.when == "call":
        value = item.funcargs.get("value")
        name = value.get("api_name") + value.get("info")
        if log_info := LOG.get(name):
            msg = (f'{item.name}-->执行状态：'
                   f'{report.outcome} 请求地址：{log_info.get("address")} 响应状态：{log_info.get("status")} 响应时间:{log_info.get("times")}')
            logger_methods = {
                "failed": logger.warning,
                "error": logger.error,
                "passed": logger.success,
            }
            logger_methods.get(report.outcome, logger.info)(msg)


def pytest_terminal_summary(terminalreporter):
    """收集测试结果"""
    type_list = [
        "failed",
        "passed",
        "skipped",
        "deselected",
        "xfailed",
        "xpassed",
        "warnings",
        "error",
    ]
    duration = round(time() - terminalreporter._sessionstarttime, 2)
    stats = {key: terminalreporter.stats.get(key, []) for key in type_list}
    count = {key: len(value) for key, value in stats.items()}
    results.update(
        stats=stats,
        count=count,
    )
    results.update({"total": terminalreporter._numcollected, "duration": duration})


@pytest.fixture()
def login_admin():
    client = login("admin")
    if not get_value("uid"):
        set_value("uid", client.res_to_json_path("$.id"))
    return True


@pytest.fixture()
def login_test():
    client = login("test")
    if not get_value("test_uid"):
        set_value("test_uid", client.res_to_json_path("$.id"))
    return True


def login(user="admin"):
    if user == "admin":
        data = {"email": get_value("admin_email"), "password": get_value("admin_password")}
    else:
        data = {"email": get_value("test_email"), "password": get_value("test_password")}
    client = api(api_name="login", data=data)
    ticket = client.res_to_json_path("$.result.ticket")
    client = auth(ticket, "login", "password")
    return client


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


@pytest.fixture(scope="session", autouse=True)
def session_setup_teardown():
    client = login("admin")
    set_value("uid", client.res_to_json_path("$.id"))
    team_ids = jsonpath(client.res_json, '$.teams[?(@.name=="接口自动化团队")]..id')
    if team_ids:
        for team_id in team_ids:
            dissolve_tenant(team_id)
    setup_team()
    clear_tester()
    create_team()
    corp_setup()
    setup_tester()
    yield
    if team_id := get_value("team_id"):
        login("admin")
        dissolve_tenant(team_id)


def corp_setup():
    api(api_name="create_team_setting", data={"create_team_switch": True}, cookie=get_value("cookie"))
    api(api_name="process_info", data={"active_status": False, "id": 1}, cookie=get_value("cookie"))
    api(api_name="process_info", data={"active_status": False, "id": 2}, cookie=get_value("cookie"))


def create_team():
    data = {"name": "接口自动化团队"}
    params = {"team_id": data_f("uuid")}
    client = api(api_name="create_team", cookie=get_value("cookie"), data=data, params=params)
    set_value("team_id", client.res_to_json_path("$..id"))


def setup_tester():
    client = api(api_name="get_company_member", cookie=get_value("cookie"),
                 data={"search_key": get_value("test_email"), "order_key": "time|desc"})

    if not jmespath.search(f"result.users[?(@.email=='{get_value('test_email')}')].id", client.res_json):
        api(api_name="register", data={"email": get_value("test_email"), "password": get_value("test_password")})
    # if tester_id := jmespath.search(f"result.users[?(@.email=='{get_value('test_email')}')].id",
    #                                 client.res_json):
    #     api(api_name="del_company_member", cookie=get_value("cookie"),
    #         data={"user_id": tester_id, "transfer_user_id": get_value("uid")})


def dissolve_tenant(team_id):
    dissolve_data = {"tenant_id": team_id, "name": "接口自动化团队", "password": get_value("admin_password"),
                     "cur_user_id": get_value("uid")}

    api(api_name="dissolve_tenant", cookie=get_value("cookie"), data=dissolve_data)
