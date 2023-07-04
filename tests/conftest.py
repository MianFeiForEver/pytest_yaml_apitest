import types
from pathlib import Path

import pytest
from _pytest.python import Module

from src.case_util import load, ApiInfo
from src.config import results, LOG
from src.core.wrok_log import RunningLog
from src.runner import RunYaml
from src.utils import time

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
    metafunc.parametrize(
        "value",
        params_data,
        ids=[value.get("info") for value in params_data],
        scope="function",
    )


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
            msg = f'{item.name}-->执行状态：{report.outcome} 请求地址：{log_info.get("address")} 响应状态：{log_info.get("status")} 响应时间:{log_info.get("times")}'
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
