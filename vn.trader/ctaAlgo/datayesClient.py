# encoding: UTF-8

'''一个简单的通联数据客户端，主要使用requests开发，比通联官网的python例子更为简洁。'''


import requests
import json

FILENAME = 'datayes.json'
HTTP_OK = 200


########################################################################
class DatayesClient(object):
    """通联数据客户端"""
    
    name = u'通联数据客户端'

    #----------------------------------------------------------------------
    def __init__(self):
        """Constructor"""
        self.domain = ''    # 主域名
        self.version = ''   # API版本
        self.token = ''     # 授权码
        self.header = {}    # http请求头部
        self.settingLoaded = False  # 配置是否已经读取
        
        self.loadSetting()
        
    #----------------------------------------------------------------------
    def loadSetting(self):
        """载入配置"""
        # try:
        #     f = file(FILENAME)
        # except IOError:
        #     print u'%s无法打开配置文件' % self.name
        #     return
        #
        # setting = json.load(f)
        try:
            self.domain = str("http://api.wmcloud.com/data")
            self.version = str("v1")
            self.token = str("2fdd1aeff5c949a5880ddba21903c45fb3da7755224f9442848b4a20231c988b")
        except KeyError:
            print u'%s配置文件字段缺失' % self.name
            return

        self.header['Connection'] = 'keep_alive'
        self.header['Authorization'] = 'Bearer ' + self.token
        self.settingLoaded = True
        
        print u'%s配置载入完成' % self.name
        
    
    #----------------------------------------------------------------------
    def downloadData(self, path, params):
        """下载数据"""
        if not self.settingLoaded:
            print u'%s配置未载入' % self.name
            return None
        else:
            url = '/'.join([self.domain, self.version, path])
            r = requests.get(url=url, headers=self.header, params=params)
            # print u'开始下载数据'
            
            if r.status_code != HTTP_OK:
                print u'%shttp请求失败，状态代码%s' %(self.name, r.status_code)
                return None
            else:
                result = r.json()
                # if 'retCode' in result and result['retMsg'] == 'Success':
                if 'data' in result:
                    #通联数据客户端分钟行情与日周月行情返回值格式有区别
                    #分钟行情返回值在data的barBodys值中
                    if 'barBodys'in result['data'][0]:
                        return result['data'][0]['barBodys']
                    else:
                        return result['data']
                else:
                    if 'retCode' in result:
                        print u'%s查询失败，返回信息%s' %(self.name, result['retMsg'])
                    elif 'message' in result:
                        print u'%s查询失败，返回信息%s' %(self.name, result['message'])
                    return None
                    
                    
    
    