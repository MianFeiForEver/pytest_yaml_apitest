from enum import Enum

PARAMS = {}
results = {}
req_results = {}
LOG = {}
env_info = {}
collect = {"total": 0, "passed": 0, "failed": 0, "skipped": 0}

at_list = {
    "saas": {
        "demo": "demo",
    }
}

report_msg = {
    "address": "test",
    "hook_id": "test",
}


class BasePath(Enum):
    config_path = "tests"
    case_path = "case"
    logs_path = "logs"
    monitor_path = "monitor"
    html_path = "reports"
    files_path = "files/"


class FeiShu:
    feishu_base_url = "https://open.feishu.cn/open-apis"
    tenant_access_token_url = feishu_base_url + "/auth/v3/tenant_access_token/internal"
    messages_url = feishu_base_url + "/im/v1/messages?receive_id_type=chat_id"
    urgent_app_url = (
            feishu_base_url
            + "/im/v1/messages/$<message_id>/urgent_app?user_id_type=user_id"
    )
    app_id = "XXX"
    app_secret = "XXX"
    chat_id = "XXX"
    urgent_list = {
        "saas": {
            "demo": "demo",
        },
    }
