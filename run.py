# coding:utf-8
import pytest

from src.case_util import param
from src.utils import save_info, DirPath, LocalDatatime, get_base_url

if __name__ == "__main__":
    args = param()
    base_url = param().u
    mode = param().m
    # base_url = "https://jsonplaceholder.typicode.com" #demo
    base_url = 'https://pdp-test00.lanhuapp.com'
    # project = "project1"
    save_info(base_url)
    # setup()

    try:
        cases = f"./tests/case/"
        # cases = f"./case/{project}/test_XX.yaml"  # 可执行单文件
        main_list = [
            cases,
            "--reruns=1",  # 失败重跑次数
            "--reruns-delay=1",
            "--alluredir=./allure-results",
            "--clean-alluredir",
            "-s",
            "--keep-duplicates",
            # "--durations=10", #根据用例执行时间排序
            "-l",  # --showlocals 打印失败用例的变量值
            f"--html={DirPath().html_path}/{LocalDatatime().datetime()}.html",
            "--self-contained-html",
            "-W",
            "ignore:Module already imported:pytest.PytestWarning",  # 忽略框架警告
        ]
        if mode in ["monitor", "MON"]:
            main_list.extend(["-m", "not NOT_MON"])
        pytest.main(main_list)
        with open("./allure-results/environment.properties", "w+") as f:
            f.write(get_base_url())

        # 生成allure报告，注释后不生成allure报告
        # shell_invoke()

    except Exception as e:
        raise Exception(e)
