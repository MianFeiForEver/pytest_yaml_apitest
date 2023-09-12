from enum import Enum

PARAMS = {}
results = {}
req_results = {}
LOG = {}
env_info = {}
collect = {"total": 0, "passed": 0, "failed": 0, "skipped": 0}


class BasePath(Enum):
    config_path = "tests"
    case_path = "case"
    logs_path = "logs"
    monitor_path = "monitor"
    html_path = "reports"
    files_path = "files/"
