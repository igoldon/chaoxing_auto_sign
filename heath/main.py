# -*- coding: utf8 -*-
import re
import json
from urllib import parse
from urllib.parse import quote
import requests

# 配置学习通账号密码
USER_INFO = {
    'username': 'xxxxx',
    'password': 'xxxxx',
    'schoolid': '',  # 学号登录才需要填写
}


class HeathReport(object):

    def __init__(self, username: str = "", password: str = "", schoolid: str = ""):
        """
        :params username: 手机号或学号
        :params password: 密码
        :params schoolid: 学校代码，学号登录填写
        """
        headers = {
            'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/84.0.4147.125 Safari/537.36',
            'Content-Type': 'application/x-www-form-urlencoded;charset=UTF-8',
            'X-Requested-With': 'XMLHttpRequest',
        }
        self._username = USER_INFO['username'] if not username else username
        self._password = USER_INFO['password'] if not password else password
        self._schoolid = USER_INFO['schoolid'] if not schoolid else schoolid
        self._session = requests.session()
        self._session.headers = headers
        self.form_data = []

    def _login(self):
        """
        登录: 支持手机和邮箱登录
        """
        login_api = "https://passport2.chaoxing.com/api/login"
        params = {
            "name": self._username,
            "pwd": self._password,
            "verify": "0",
            "schoolid": self._schoolid if self._schoolid else ""
        }
        resp = self._session.get(login_api, params=params)

        if resp.status_code == 403:
            raise Exception("403，登录请求被拒绝")

        data = json.loads(resp.text)
        return data

    def _get_last_heath_info(self) -> dict:
        """
        获取上次提交的健康信息
        """
        params = {
            "cpage": "1",
            "formId": "7185",
            "enc": "f837c93e0de9d9ad82db707b2c27241e",
            "formAppId": ""
        }
        api = 'http://office.chaoxing.com/data/web/apps/forms/fore/user/list'
        resp = self._session.get(api, params=params)
        raw_data = json.loads(resp.text)
        return raw_data

    @staticmethod
    def clean_heath_info(raw_data: dict) -> list:
        form_data = raw_data['data']['formUserList'][0]['formData']
        d = {
            "inDetailGroupIndex": -1,
            "fromDetail": False,
        }
        not_show = [x for x in range(9, 36) if x % 2 != 0]
        not_show.extend([38, 39, 41, 42])
        for f in form_data:
            f.update(d)

            if f['id'] == 5:
                f['fields'][0]['tip']['text'] = r"<p+style=\"text-align:+center;\"><span+style=\"font-size:+large;+font-weight:+bold;\">基本信息</span></p>"
            elif f['id'] == 6:
                f['fields'][0]['tip']['text'] = r"<p+style=\"text-align:+center;\"><span+style=\"font-size:+large;+font-weight:+bold;\">健康状况</span></p>"
            elif f['id'] == 36:
                f['fields'][0]['tip']['text'] = r"<p+style=\"text-align:+center;\"><span+style=\"font-size:+large;+font-weight:+bold;\">出行情况</span></p>"
            elif f['id'] == 8:
                f['fields'][0]['values'][0]['val'] = "健康 "
                f['fields'][0]['options'][0]['title'] = "健康 "

            if f['id'] in not_show:
                f['isShow'] = False
            else:
                f['isShow'] = True
        # print(form_data)
        return form_data

    def form_data_to_urlencoded(self, params: dict) -> str:
        """
        dict -> urlencoded
        """
        payload = parse.urlencode(params)
        str_form_data = str(self.form_data)
        str_form_data = str_form_data.replace('\'', '\"').replace('False', 'false').replace('True', 'true').replace(r"\\", "\\")
        payload += quote(str_form_data, 'utf-8')
        return payload

    def _edit_report(self, hid: str, enc: str) -> dict:
        """
        上报健康信息
        """
        edit_api = "https://office.chaoxing.com/data/apps/forms/fore/user/edit"
        params = {
            "id": hid,
            "formId": "7185",
            "enc": enc,
            "gverify": "",
            "formData": ''
        }
        payload = self.form_data_to_urlencoded(params)
        resp = self._session.post(edit_api, data=payload)
        return json.loads(resp.text)

    def _daily_report(self, check_code) -> dict:
        """
        上报今日信息
        """
        # save_api = "http://office.chaoxing.com/data/apps/forms/fore/user/save?lookuid=127973522"
        save_api = "http://office.chaoxing.com/data/apps/forms/fore/user/save?lookuid=127973604"
        params = {
            "formId": "7185",
            "formAppId": "",
            "version": "2",
            "checkCode": check_code,
            "enc": "f837c93e0de9d9ad82db707b2c27241e",
            "formData": ""
        }
        payload = self.form_data_to_urlencoded(params)
        resp = self._session.post(save_api, data=payload)
        return json.loads(resp.text)

    def _request_form_page(self):
        """
        请求表单页面
        @return:
        @rtype:
        """
        form_url = "http://office.chaoxing.com/front/web/apps/forms/fore/apply?uid=127973604&code=l5RJsW2w&mappId=4545821&appId=1e354ddb52a743e88ed19a3704b1cf1a&appKey=127G2jhIhl05mw3S&id=7185&enc=f837c93e0de9d9ad82db707b2c27241e&state=39037&formAppId=&fidEnc=b06cba4a51ac2253"
        return self._session.get(url=form_url)

    @staticmethod
    def _get_check_code(resp):
        """
        解析表单界面获取checkCode
        @param resp:
        @type resp:
        @return: checkCode
        @rtype: str
        """
        code = re.findall(r"checkCode.*'(.*)'", resp.text)
        if code:
            return code[0]
        else:
            raise Exception("校验码获取失败")

    def _to_begin(self):
        """
        调用登录及健康信息获取函数
        """
        self._login()
        raw_data = self._get_last_heath_info()
        self.form_data = self.clean_heath_info(raw_data)

    def edit_report(self, hid: str, enc: str) -> dict:
        """
        修改已上报的健康信息
        说明：修改已上报信息的功能实际意义不大，主要是开发时测试使用
        :params id: 表单id
        :params form_data: 已编码的上次健康信息
        """
        self._to_begin()
        return self._edit_report(hid, enc)

    def daily_report(self) -> dict:
        """
        健康信息上报入口
        """
        self._to_begin()
        r = self._request_form_page()
        check_code = self._get_check_code(r)
        return self._daily_report(check_code=check_code)


def main_handler(event=None, context=None):
    if event is not None:
        query: dict = event.get("queryString", "")
        if query:
            username, password, schoolid = query.get("name", ''), query.get("pwd", ''), query.get("schoolid", "")

            if not username or not password:
                return {
                    "message": "账号密码不能为空"
                }
            h = HeathReport(username=username, password=password, schoolid=schoolid)
            return h.daily_report()
    h = HeathReport(username=USER_INFO['username'], password=USER_INFO['password'], schoolid=USER_INFO['schoolid'])
    return h.daily_report()


if __name__ == '__main__':
    print(main_handler())
