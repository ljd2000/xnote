# encoding=utf-8
# @author xupingmao
# @since
# @modified 2020/05/04 21:26:10
import six
import xutils
import xtemplate
import sys
import inspect
import web

class ModuleInfo:
    def __init__(self, mod, sysname):
        try:
            self.name = mod.__name__
        except:
            # getattr判断无效
            xutils.print_exc()
            self.name = "Unknown"
        self.sysname = sysname
        self.is_builtin = False
        if hasattr(mod, "__file__"):
            self.file = mod.__file__
        else:
            self.file = "?"
        if hasattr(mod, "__spec__"):
            # self.is_builtin = mod.__spec__.origin
            pass
        self.info = str(mod)

    def __lt__(self, info):
        return self.sysname < info.sysname

def query_modules():
    modules = []
    for modname in sys.modules.copy():
        module = sys.modules[modname]
        if module != None:
            mod = ModuleInfo(module, modname)
            modules.append(mod)
        else:
            # Py2中出现这种情况
            six.print_("%s is None" % modname)
    return sorted(modules)

class handler(object):
    
    def GET(self):
        return xtemplate.render("system/page/module_list.html", 
            show_aside = False,
            modules = query_modules(),
            sys = sys)

class DocInfo:

    def __init__(self, name, doc, type="function"):
        self.name = name
        self.doc = doc
        self.type = type

class ModInfo:

    def __init__(self, name):
        self.name = name
        mod = sys.modules[name]
        functions = []
        self.mod = mod
        self.functions = functions
        self.doc = mod.__doc__
        self.file = ""
        if hasattr(mod, "__file__"):
            self.file = mod.__file__
            # process with Py2
            if self.file.endswith(".pyc"):
                self.file = self.file[:-1]

        attr_dict = mod.__dict__
        for attr in sorted(attr_dict):
            if attr[0] == '_':
                # 跳过private方法
                continue
            value = attr_dict[attr]
            # 通过__module__判断是否时本模块的函数
            # isroutine判断是否是函数或者方法
            value_mod = inspect.getmodule(value)
            if value_mod != mod:
                # 跳过非本模块的方法
                continue
            if inspect.isroutine(value):
                functions.append(DocInfo(attr + getargspec(value), value.__doc__))
            elif inspect.isclass(value):
                do_class(functions, attr, value)
            # TODO 处理类的文档，参考pydoc

def getargspec(value):
    argspec = ''
    try:
        signature = inspect.signature(value)
    except (ValueError, TypeError, AttributeError):
        signature = None
    if signature:
        argspec = str(signature)
    return argspec

def do_class(functions, name, clz):
    doc = getattr(clz, "__doc__")
    if doc:
        functions.append(DocInfo(name, doc, "class"))
    for attr in clz.__dict__:
        value = clz.__dict__[attr]
        if inspect.isroutine(value):
            if attr[0] == "_" and value.__doc__ is None:
                continue
            functions.append(DocInfo(name+"."+attr+getargspec(value), value.__doc__, "method"))

class ModuleDetailHandler(object):

    def GET(self):
        name = xutils.get_argument("name")
        force = xutils.get_argument("force")

        if force == "true":
            __import__(name)

        doc_info = None
        if name is not None:
            doc_info = ModInfo(name)
        return xtemplate.render("system/page/module_detail.html", 
            show_aside = False,
            doc_info = doc_info)

xurls = (
    r"/system/pydoc", handler,
    r"/system/modules_info", handler,
    r"/system/document", ModuleDetailHandler
)
        