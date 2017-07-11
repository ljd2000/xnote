# -*- coding:utf-8 -*-  
# Created by xupingmao on 2017/06/17
# 

"""Description here"""

import re
from urllib import request
from bs4 import BeautifulSoup
import xutils
import xtables
import xconfig

class handler:

    def GET(self):
        city_code = xutils.get_argument("city_code", "101020100")
        city_name = xutils.get_argument("city_name", "上海")

        message = None

        db = xtables.get_record_table()
        record = db.select_one(where="type='weather' AND DATE(ctime)=$date_str AND key=$key", 
            vars=dict(date_str=xutils.format_date(), key=city_name))
        if record is not None:
            message = record.value
        else:
            url = "http://www.weather.com.cn/weather1d/%s.shtml" % city_code
            html = request.urlopen(url).read()
            if html == b"<!-- empty -->":
                return dict(code="fail", message="city_code错误")
            soup = BeautifulSoup(html, "html.parser")
            elements = soup.find_all(id="hidden_title")
            # print(elements)
            # print(len(html))
            # return html
            if len(elements) > 0:
                weather = elements[0]
                message = weather.attrs["value"]
                message = message.replace("/", "至")
                db.insert(ctime=xutils.format_datetime(), 
                    type="weather",
                    key=city_name,
                    value=message
                )

        if message is not None:
            if not xconfig.is_mute():
                xutils.say("%s %s" % (city_name, message))
            return dict(code="success", data=message)
        else:
            return dict(code="fail", message="结果为空")