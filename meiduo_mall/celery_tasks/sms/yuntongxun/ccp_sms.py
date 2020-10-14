#!D:\software\python3 python
# -*- coding: utf-8 -*-

from .CCPRestSDK import REST
# python requests SSL证书问题
import ssl

ssl._create_default_https_context = ssl._create_unverified_context

# 主账号
accountSid = "8a216da8685986c201685b01d62a0144"

# 主账号token
accountToken = "8406ce99519d49acabeb28e2ed45fe1a"

# 应用ID
appleId = "8a216da8685986c201685b01d68f014b"

# 请求地址(不需要http)
serverIP = "app.cloopen.com"

# 请求端口
serverPort = "8883"

# REST版本号
softVersion = "2013-12-26"


# 发送模板短信
# @param to 手机号码
# @param datas 内容数据 格式为列表 例如：['12','34']，如不需替换请填 ''
# @param $tempId 模板Id

class CCP:
    """自己封装的发送短信的辅助类"""
    instance = None

    def __new__(cls):
        # 判断CCP类有没有已经创建好的对象，如果没有，创建一个对象，并且保存
        # 如果有，则将保存的对象直接返回
        if cls.instance is None:
            obj = super(CCP, cls).__new__(cls)

            # 初始化REST SDK
            obj.rest = REST(serverIP, serverPort, softVersion)
            obj.rest.setAccount(accountSid, accountToken)
            obj.rest.setAppId(appleId)

            cls.instance = obj

        return cls.instance

    def send_template_sms(self, to, datas, temp_id):
        result = self.rest.sendTemplateSMS(to, datas, temp_id)

        # for k, v in result.items():
        #
        #     if k == 'templateSMS':
        #         for k, s in v.items():
        #             print ('%s:%s' % (k, s))
        #     else:
        #         print ('%s:%s' % (k, v))
        # smsMessageSid:ff75e0f84f05445ba08efdd0787ad7d0
        # dateCreated:20171125124726
        # statusCode:000000
        status_code = result.get('statusCode')
        if status_code == '000000':
            # 发送成功
            return 0
        else:
            # 发送失败
            return -1


if __name__ == '__main__':
    ccp = CCP()
    ret = ccp.send_template_sms('13247135836', ['1234', '5'], 1)
    print(ret)
