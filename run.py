# coding:utf-8
import pytest

from src.case_util import param
from src.utils import save_info, get_value, DirPath, LocalDatatime

if __name__ == "__main__":
    args = param()
    project = param().p
    env = param().e
    mode = param().m
    reporter = param().r
    print(
        r"""
                _ _______        _              _             _           
    /\         (_)__   __|      | |            | |           | |          
   /  \   _ __  _   | | ___  ___| |_           | | __ _ _ __ | |__  _   _ 
  / /\ \ | '_ \| |  | |/ _ \/ __| __|          | |/ _` | '_ \| '_ \| | | |
 / ____ \| |_) | |  | |  __/\__ \ |_           | | (_| | | | | | | | |_| |
/_/    \_\ .__/|_|  |_|\___||___/\__|          |_|\__,_|_| |_|_| |_|\__,_|
         | |                           ______                             
         |_|                          |______|                                                                                                                                                                                                                                       
              """
    )
    # env = ""
    # project = "project1"
    save_info(project, env, reporter)
    # setup()

    try:
        cases = f"./tests/{project}/case/"
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
            f.write(f"base_url= {get_value('base_url')}")

        # 生成allure报告，注释后不生成allure报告
        # shell_invoke()

    except Exception as e:
        raise Exception(e)
