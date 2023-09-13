from enum import Enum

admin_email = "admin@jwzg.com"
admin_password = "Lanhu123"
test_email = "test@jwzg.com"
test_password = "Lanhu123"
init_user = {
    "admin_email": admin_email,
    "admin_password": admin_password,
    "test_email": test_email,
    "test_password": test_password
}
PARAMS = init_user
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
