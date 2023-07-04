## 简介

pytest + request + allure 接口自动化框架

## 安装brew *

`/bin/zsh -c "$(curl -fsSL https://gitee.com/cunkai/HomebrewCN/raw/master/Homebrew.sh)"`

## 安装allure *

`brew install allure`

## 安装依赖 *

```
pip install -r requirements.txt
```

## Docker

### 构建

```
docker-compose  --build
```

构建镜像名: `apitest`
容器名

### 运行

```
docker run apitest python run.py --e {env} --m {mode} --p {project}
```

### 查看报告

```
 docker cp  <containerId>:/app/allure-results ./allure-results
 allure serve allure-results
```

## 运行方式

- PyCharm 右键运行
- python3 run.py --e {env} --m {mode} --p {project}

## 用例编写方式

### 接口信息

> 路径："/config/{project}/interface

```
notify_team: #接口别称
  project: notify #所属项目用例拼接地址前缀：passport、seat、plugin、dsm、notify、ws_admin，在core.util.saas_base_url中
  address: /api/notify/team=${team_id} #api path,${xxx} 需要替换的变量名
  method: get #请求方式 post get put delete
  body_type: json #请求体格式 url-encode json xml form-data
  data: team_id #非必填，body字段
```

### 用例信息

> 路径："/config/{project}/data

```
sms_register: #用例数据名
  - api_name: sms_register #接口别名
    data: { mobile: $<mobile>, code: $<code> } #data数据
    info: 校验验证码接口：短信注册 #info 用来描述此条数据
    params: { team_id(key): value } #用来替换链接里的变量 key 需要与api_address中变量一致，value可赋予默认值，可从generate &get的并集中获取
    cookies: False #是否需要填充cookie，登录注册需要写false，默认true 无需填写
    authorization: True #默认False 部分接口header需要添加authorization
    get: #需要从其他用例保存的数据中获取
      mobile: mobile #data中名称：保存的字段名
    generate: #需要生成的数据
      code: code #data中名称 ：类型
    status: 200 #接口响应状态码 默认200 无需填写
    set: #需要存储的信息
        存储数据名: jsonpath #user_id: $.id
        特殊场景：
            cookie： 存储当前变量cookie
            plugin_token：插件token
            drawer_page_id
    assertion: 需要断言内容 jsonpath 默认省略 $.
      code: 0 #$.code 值为0
      result: exist  # $.result 存在值， not exist 不存在
      id: $<id> # 从已存数据中取id 并断言
```

### 用例组织

> 路径："/config/{project}/case

```
- test_create_project: #用例名
    title: 创建项目接口 #title
    depends:
        name: create_project #pytest.mark.dependency name
        depends_on: # pytest.mark.dependency depends
          - create_team
        scope: # pytest.mark.dependency scope
          - session # scope可接受四种参数定义的类型（'session'，'package'，'module'或'class'）
    fixture: # 需要执行fixture函数，默认必备rq，value无需填写
      - login
```

run.py 中setup() 会清理 /case/{project}/ 下.py文件，并再次生成

>
> allure serve allure-results 查看报告
>
> run.py 中执行完成会自动生成allure报告，打开目录allure-reports中的index.html即可查看本次运行报告
>
> ps：执行前可先清理allure-results、allure-reports
