# -*- coding:utf-8 -*-
# @author xupingmao <578749341@qq.com>
# @since 2018/09/30 20:53:38
# @modified 2020/07/29 00:43:51
from io import StringIO
import xconfig
import codecs
import time
import functools
import os
import json
import socket
import os
import autoreload
import xtemplate
import xutils
import xauth
import xmanager
import xtables
import web
import copy
from xtemplate import BasePlugin
from xutils import History
from xutils import cacheutil
from xutils import Storage
from xutils import fsutil
from xutils import textutil, SearchResult, dateutil, dbutil, u

MAX_HISTORY = 200

class PluginContext:

    def __init__(self):
        self.title = ""
        self.description = ""
        self.fname = ""

    # sort方法重写__lt__即可
    def __lt__(self, other):
        return self.title < other.title

    # 兼容Python2
    def __cmp__(self, other):
        return cmp(self.title, other.title)

def is_plugin_file(fpath):
    return os.path.isfile(fpath) and fpath.endswith(".py")

def load_plugin_file(fpath, fname = None):
    if fname is None:
        fname = os.path.basename(fpath)
    dirname = os.path.dirname(fpath)

    # plugin name
    pname = fsutil.get_relative_path(fpath, xconfig.PLUGINS_DIR)

    vars = dict()
    vars["script_name"] = pname
    vars["fpath"] = fpath
    try:
        module = xutils.load_script(fname, vars, dirname = dirname)
        main_class = vars.get("Main")
        if main_class != None:
            main_class.fname = fname
            main_class.fpath = fpath
            instance = main_class()
            context = PluginContext()
            context.fname = fname
            context.fpath = fpath
            context.name = os.path.splitext(fname)[0]
            context.title = getattr(instance, "title", "")
            context.category = xutils.attrget(instance, "category")
            context.required_role = xutils.attrget(instance, "required_role")

            context.url = "/plugins/%s" % pname
            if hasattr(main_class, 'on_init'):
                instance.on_init(context)
            context.clazz = main_class
            xconfig.PLUGINS_DICT[pname] = context
    except:
        # TODO 增加异常日志
        xutils.print_exc()

def load_sub_plugins(dirname):
    for fname in os.listdir(dirname):
        fpath = os.path.join(dirname, fname)
        if is_plugin_file(fpath):
            # 支持插件子目录
            load_plugin_file(fpath, fname)

def load_plugins(dirname = None):
    if dirname is None:
        dirname = xconfig.PLUGINS_DIR

    xconfig.PLUGINS_DICT = {}
    for fname in os.listdir(dirname):
        fpath = os.path.join(dirname, fname)
        if os.path.isdir(fpath):
            load_sub_plugins(fpath)
        if is_plugin_file(fpath):
            load_plugin_file(fpath, fname)

@xutils.timeit(logfile=True, logargs=True, name="FindPlugins")
def find_plugins(category):
    role = xauth.get_current_role()
    plugins = []

    if role is None:
        # not logged in
        return plugins

    if category == "None":
        category = None

    for fname in xconfig.PLUGINS_DICT:
        p = xconfig.PLUGINS_DICT.get(fname)
        if p and p.category == category:
            required_role = p.required_role
            if role == "admin" or required_role is None or required_role == role:
                plugins.append(p)
    plugins.sort()
    return plugins

def link(name, url, title = ""):
    if title == "":
        title = name
    return Storage(name = name, 
        url = url, 
        link = url, 
        title = title, 
        fname = name,
        editable = False, 
        atime = "")

def inner_link(name, url):
    return Storage(name = name, 
        url = url, 
        link = url, 
        fname = name,
        title = name, 
        editable = False, 
        category = "inner", 
        atime="")

INNER_TOOLS = [
    inner_link("浏览器信息", "/tools/browser_info"),
    # 文本
    inner_link("文本对比", "/tools/text_diff"),
    inner_link("文本转换", "/tools/text_convert"),
    inner_link("随机字符串", "/tools/random_string"),
    # 图片
    inner_link("图片合并", "/tools/img_merge"),
    inner_link("图片拆分", "/tools/img_split"),
    inner_link("图像灰度化", "/tools/img2gray"),
    # 编解码
    inner_link("base64", "/tools/base64"),
    inner_link("HEX转换", "/tools/hex"),
    inner_link("md5签名", "/tools/md5"),
    inner_link("sha1签名", "/tools/sha1"),
    inner_link("URL编解码", "/tools/urlcoder"),
    inner_link("条形码", "/tools/barcode"),
    inner_link("二维码", "/tools/qrcode"),
    # 其他工具
    inner_link("分屏模式", "/tools/multi_win"),
    inner_link("RunJS", "/tools/runjs"),
    inner_link("摄像头", "/tools/camera"),
]


def build_inner_tools():
    return copy.copy(INNER_TOOLS)

def build_plugin_links(plugins):
    links = []
    for plugin in plugins:
        fname = plugin.fname
        fpath = plugin.fpath

        item = link(plugin.title, plugin.url)
        item.editable = True
        atime = cacheutil.zscore("plugins.history", plugin.name)
        if atime:
            item.atime = xutils.format_date(atime)
        else:
            item.atime = ""

        item.edit_link = "/code/edit?path=" + fpath
        item.title = plugin.title
        item.fname = plugin.fname

        links.append(item)

    return links

def sorted_plugins(user_name, plugins):
    # 把最近访问的放在前面
    logs = list_visit_logs(user_name, 0, 20)
    
    url_dict = dict()
    for p in plugins:
        url_dict[p.url] = p

    recent_plugins = []
    recent_urls = []

    for log in logs:
        if log.url in url_dict:
            recent_plugins.append(url_dict[log.url])
            recent_urls.append(log.url)
            del url_dict[log.url]

    # print(plugins)
    # print("Recent Urls:", recent_urls)
    # print("Recent Plugins:", recent_plugins)

    rest_plugins = list(filter(lambda x:x.url not in recent_urls, plugins))
    return recent_plugins + rest_plugins

def list_plugins(category, sort = True):
    if category == "other":
        plugins = find_plugins(None)
        links = build_plugin_links(plugins)
    elif category and category != "all":
        # 某个分类的插件
        plugins = find_plugins(category)
        links = build_plugin_links(plugins)
    else:
        # 所有插件
        links = build_inner_tools()
        links += build_plugin_links(xconfig.PLUGINS_DICT.values())

    user_name = xauth.current_name()
    if sort:
        return sorted_plugins(user_name, links)
    return links

def find_plugin_by_name(name):
    plugins = list_plugins("all", sort = False)
    name, ext = os.path.splitext(name)
    for p in plugins:
        if u(p.name) == u(name):
            return p
    return None

def list_recent_plugins():
    user_name = xauth.current_name()
    items = list_visit_logs(user_name, 0, 5)
    links = [find_plugin_by_name(log.name) for log in items]

    return list(filter(None, links))

def list_visit_logs(user_name, offset = 0, limit = -1):
    logs = dbutil.prefix_list("plugin_visit_log:%s" % user_name, 
        offset = offset, limit = limit, reverse = True)
    logs.sort(key = lambda x: x.time, reverse = True)
    return logs

def find_visit_log(user_name, url):
    for key, log in dbutil.prefix_iter("plugin_visit_log:%s" % user_name, include_key = True):
        if log.url == url:
            log.key = key
            return log
    return None

def update_visit_log(log, name):
    log.name = name
    log.time = dateutil.format_datetime()
    if log.visit_cnt is None:
        log.visit_cnt = 1
    log.visit_cnt += 1
    dbutil.put(log.key, log)

def add_visit_log(user_name, name, url):
    exist_log = find_visit_log(user_name, url)
    if exist_log != None:
        update_visit_log(exist_log, name)
        return

    log = Storage()
    log.name = name
    log.url  = url
    log.time = dateutil.format_datetime()

    dbutil.insert("plugin_visit_log:%s" % user_name, log)

def load_plugin(name):
    user_name = xauth.current_name()
    add_visit_log(user_name, name, "/plugins/" + name)

    context = xconfig.PLUGINS_DICT.get(name)
    if xconfig.DEBUG or context is None:
        script_name = "plugins/" + name
        fpath = os.path.join(xconfig.PLUGINS_DIR, name)
        if not os.path.exists(fpath):
            return None
        vars = dict()
        vars["script_name"] = script_name
        vars["fpath"] = fpath
        xutils.load_script(script_name, vars)
        main_class = vars.get("Main")
        main_class.fpath = fpath
        
        # 发现了新的插件，先临时重新加载一下，后续优化成按需加载的模式
        load_plugins()

        return main_class
    else:
        return context.clazz

@xmanager.searchable()
def on_search_plugins(ctx):
    if not xauth.is_admin():
        return
    if not ctx.search_tool:
        return
    if ctx.search_dict:
        return
    name    = ctx.key
    results = []
    words   = textutil.split_words(name)
    for name in xconfig.PLUGINS_DICT:
        plugin = xconfig.PLUGINS_DICT[name]
        unquote_name = xutils.unquote(plugin.fname)
        unquote_name, ext = os.path.splitext(unquote_name)
        plugin_context = plugin
        if textutil.contains_all(unquote_name, words) \
                or (textutil.contains_all(plugin_context.title, words)):
            result           = SearchResult()
            result.category  = "plugin"
            result.icon      = "fa-cube"
            result.name      = u(unquote_name)
            if plugin_context != None:
                # result.raw = u(plugin_context.title)
                # result.name = u("插件 %s (%s)") % (u(plugin_context.title), unquote_name)
                if plugin_context.title != None:
                    result.name = u(plugin_context.title + "(" + unquote_name + ")")
            result.url       = u(plugin.url)
            result.edit_link = u("/code/edit?path=" + plugin.fpath)
            results.append(result)

    result_count = len(results)
    if ctx.category != "plugin" and len(results) > 3:
        results = results[:3]
        more = SearchResult()
        more.name = u("查看更多插件(%s)") % result_count
        more.icon = "fa-cube"
        more.url  = "/plugins_list?category=plugin&key=" + ctx.key
        results.append(more)
    ctx.tools += results

def search_plugins(key):
    words   = textutil.split_words(key)
    plugins = list_plugins("all")
    result  = []
    for p in plugins:
        if textutil.contains_all(p.title, words) or textutil.contains_all(p.url, words) or textutil.contains_all(p.fname, words):
            result.append(p)
    return result


class PluginsListOldHandler:

    @xauth.login_required()
    def GET(self):
        category = xutils.get_argument("category", "")
        key      = xutils.get_argument("key", "")

        if xauth.is_admin():
            if key != "" and key != None:
                recent  = []
                plugins = search_plugins(key)
            else:
                recent   = list_recent_plugins()
                plugins  = list_plugins(category)
        else:
            recent = []
            if category == "" or category == "all":
                plugins = build_inner_tools()
            else:
                plugins = []

        return xtemplate.render("plugins/plugins_old.html", 
            category = category,
            html_title = "插件",
            show_aside = xconfig.OPTION_STYLE == "aside",
            search_placeholder = "搜索工具",
            search_action = "/plugins_list",
            recent     = recent,
            plugins    = plugins)

def get_plugin_category(category):
    plugin_categories = []

    recent   = list_recent_plugins()
    plugins  = list_plugins(category)
    note_plugins = list_plugins("note")
    dev_plugins  = list_plugins("develop")
    sys_plugins  = list_plugins("system")
    dir_plugins  = list_plugins("dir")
    net_plugins  = list_plugins("network")
    other_plugins = list(filter(lambda x: x.category not in ("inner", "note", "develop", "system", "dir", "network"), plugins))

    plugin_categories.append(["最近", recent])
    plugin_categories.append(["默认工具", build_inner_tools()])
    plugin_categories.append(["笔记", note_plugins])
    plugin_categories.append(["开发工具", dev_plugins])
    plugin_categories.append(["系统", sys_plugins])
    plugin_categories.append(["文件", dir_plugins])
    plugin_categories.append(["网络", net_plugins])
    plugin_categories.append(["其他", other_plugins])
    return plugin_categories

class PluginsListHandler:

    @xauth.login_required()
    def GET(self):
        category = xutils.get_argument("category", "")
        key      = xutils.get_argument("key", "")
        plugin_categories = []

        if xauth.is_admin():
            if key != None and key != "":
                plugin_categories.append(["搜索", search_plugins(key)])
            else:
                plugin_categories = get_plugin_category(category)
        else:
            plugins = build_inner_tools()
            plugin_categories.append(["默认工具", plugins])

        return xtemplate.render("plugins/plugins.html", 
            category = category,
            html_title = "插件",
            plugin_categories = plugin_categories)

DEFAULT_PLUGIN_TEMPLATE = '''# -*- coding:utf-8 -*-
# @since $since
# @author $author
import os
import re
import math
import time
import web
import xconfig
import xutils
import xauth
import xmanager
import xtables
import xtemplate
from xtemplate import BasePlugin

HTML = """
<!-- Html -->
"""

class Main(BasePlugin):

    title = "PluginName"
    # 提示内容
    description = ""
    # 访问权限
    required_role = "admin"
    # 插件分类 {note, dir, system, network, develop}
    category = None
    
    def handle(self, input):
        # 输入框的行数
        self.rows = 5
        self.writehtml(HTML)

    def on_init(self, context=None):
        # 插件初始化操作
        pass
'''

class NewPluginHandler(BasePlugin):
    """默认的插件声明入口，定义一个叫做Main的类"""

    def handle(self, input):
        self.description = '''请输入插件名称'''
        self.title = '通过模板创建插件'
        self.btn_text = '创建'
        self.rows = 1
        self.editable = False
        if input != '':
            name = os.path.join(xconfig.PLUGINS_DIR, input)
            if not name.endswith(".py"):
                name += ".py"
            if os.path.exists(name):
                return u("文件[%s]已经存在!") % u(name)
            user_name = xauth.current_name()
            code = xconfig.get("NEW_PLUGIN_TEMPLATE", DEFAULT_PLUGIN_TEMPLATE)
            code = code.replace("$since", xutils.format_datetime())
            code = code.replace("$author", user_name)
            xutils.writefile(name, code)
            # 添加一个访问记录，使得新增的插件排在前面
            basename = os.path.basename(name)
            add_visit_log(user_name, basename, "/plugins/" + basename)
            raise web.seeother('/code/edit?path=%s' % name)

DEFAULT_COMMAND_TEMPLATE = '''# -*- coding:utf-8 -*-
# @since $since
# @author $author
import os
import xutils

def main(path = "", confirmed = False, **kw):
    # your code here
    pass
'''

class NewCommandPlugin(BasePlugin):
    """默认的插件声明入口，定义一个叫做Main的类"""

    def handle(self, input):
        self.title = '通过模板创建命令扩展'
        self.description = '''请输入命令扩展名称'''
        self.btn_text = '创建'
        self.rows = 1
        self.editable = False
        if input != '':
            name = os.path.join(xconfig.COMMANDS_DIR, input)
            if not name.endswith(".py"):
                name += ".py"
            if os.path.exists(name):
                return u("文件[%s]已经存在!") % u(name)
            user_name = xauth.get_current_name()
            code = xconfig.get("NEW_COMMAND_TEMPLATE", DEFAULT_COMMAND_TEMPLATE)
            code = code.replace("$since", xutils.format_datetime())
            code = code.replace("$author", user_name)
            xutils.writefile(name, code)
            raise web.seeother('/code/edit?path=%s' % name)

class LoadPluginHandler:

    def GET(self, name = ""):
        user_name = xauth.current_name()
        display_name = xutils.unquote(name)
        name = xutils.get_real_path(display_name)
        if not name.endswith(".py"):
            name += ".py"
        try:
            main_class = load_plugin(name)
            if main_class != None:
                return main_class().render()
            else:
                return xtemplate.render("error.html", 
                    error = "plugin `%s` not found!" % name)
        except:
            error = xutils.print_exc()
            return xtemplate.render("error.html", error=error)

    def POST(self, name = ""):
        return self.GET(name)

class PluginLogHandler:

    @xauth.login_required()
    def GET(self):
        user_name = xauth.current_name()
        logs = list_visit_logs(user_name)
        return logs

@xmanager.listen("sys.reload")
def reload_plugins(ctx):
    load_plugins()

xutils.register_func("plugin.find_plugins", find_plugins)

xurls = (
    r"/plugins_list_new", PluginsListHandler,
    r"/plugins_list", PluginsListOldHandler,
    r"/plugins_new", NewPluginHandler,
    r"/plugins_new/command", NewCommandPlugin,
    r"/plugins_log", PluginLogHandler,
    r"/plugins/(.+)", LoadPluginHandler
)
