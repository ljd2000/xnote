# -*- coding:utf-8 -*-  
# Created by xupingmao on 2017/05/18
# @modified 2020/03/29 16:12:42

"""时光轴视图"""
import re
import xauth
import xutils
import xtables
import xtemplate
import time
import web
from xutils import Storage, dateutil, textutil
from xtemplate import T
from .constant import *

NOTE_DAO = xutils.DAO("note")
MSG_DAO  = xutils.DAO("message")
USER_DAO = xutils.DAO("user")


class PathLink:

    def __init__(self, name, url):
        self.name = name
        self.url  = url

def get_parent_link(user_name, type):
    if type in ("group", "project"):
        return None
    return PathLink(u"项目", USER_DAO.get_config(user_name, "HOME_PATH"))

class SystemGroup(Storage):
    def __init__(self, name, url):
        super(SystemGroup, self).__init__()
        self.user = xauth.current_name()
        self.type = 'system'
        self.icon = "fa fa-gear"
        self.name = name
        self.url  = url
        self.priority = 1
        self.size = 0

class TaskGroup(Storage):
    def __init__(self, name = "待办任务"):
        super(TaskGroup, self).__init__()
        self.user = xauth.current_name()
        self.type = 'system'
        self.name = name
        self.icon = "fa-calendar-check-o"
        self.ctime = dateutil.format_time()
        self.mtime = dateutil.format_time()
        self.url  = "/message?tag=task"
        self.priority = 1
        self.size = MSG_DAO.get_message_stat(self.user).task_count

class PlanGroup(SystemGroup):
    """计划类型的笔记, @since 2020/02/16"""
    def __init__(self):
        super(PlanGroup, self).__init__(u"计划列表", "/note/plan")
        self.size = NOTE_DAO.get_note_stat(self.user).plan_count

class StickyGroup(SystemGroup):

    def __init__(self):
        super(StickyGroup, self).__init__(u"置顶笔记", "/note/sticky")
        self.size = NOTE_DAO.get_note_stat(self.user).sticky_count
        self.icon = "fa fa-thumb-tack"

class IndexGroup(SystemGroup):

    def __init__(self):
        super(IndexGroup, self).__init__(u"笔记索引", "/note/index")
        self.icon = "fa fa-gear"

def search_group(user_name, words):
    rows = NOTE_DAO.list_group(user_name)
    result = []
    for row in rows:
        if textutil.contains_all(row.name, words):
            result.append(row)
    return result

def split_words(search_key):
    search_key_lower = search_key.lower()
    words = []
    p_start = 0
    for p in range(len(search_key_lower) + 1):
        if p == len(search_key_lower):
            if p > p_start:
                word = search_key_lower[p_start:p]
                words.append(word)
            break

        c = search_key_lower[p]
        if textutil.isblank(c):
            # 空格断字
            if p > p_start:
                word = search_key_lower[p_start:p]
                words.append(word)
            p_start = p + 1
        elif textutil.is_cjk(c):
            if p > p_start:
                words.append(search_key_lower[p_start:p])
            # 中日韩字符集
            words.append(c)
            p_start = p + 1
        else:
            # 其他字符
            continue
    # print(words)
    return words


def build_date_result(rows, orderby = 'ctime', sticky_title = False, group_title = False, archived_title = False):
    tmp_result     = dict()
    sticky_notes   = []
    archived_notes = []
    project_notes  = []

    for row in rows:
        if sticky_title and row.priority != None and row.priority > 0:
            sticky_notes.append(row)
            continue

        if archived_title and row.archived == True:
            archived_notes.append(row)
            continue

        if group_title and row.type == "group":
            project_notes.append(row)
            continue
        
        if orderby == "mtime":
            date_time = row.mtime
        else:
            date_time = row.ctime

        title = re.match(r"\d+\-\d+\-\d+", date_time).group(0)
        # 优化返回数据大小
        row.content = ""
        if title not in tmp_result:
            tmp_result[title] = []
        tmp_result[title].append(row)

    tmp_sorted_result = []
    for key in tmp_result:
        items = tmp_result[key]
        items.sort(key = lambda x: x[orderby], reverse = True)
        tmp_sorted_result.append(dict(title = key, children = items))
    tmp_sorted_result.sort(key = lambda x: x['title'], reverse = True)

    result = []

    if len(sticky_notes) > 0:
        result.append(dict(title = u'置顶', children = sticky_notes))

    if len(project_notes) > 0:
        result.append(dict(title = u'项目', children = project_notes))

    result += tmp_sorted_result

    if len(archived_notes) > 0:
        result.append(dict(title = u'归档', children = archived_notes))

    return dict(code = 'success', data = result)

def list_search_func(context):
    # 主要是搜索
    offset     = context['offset']
    limit      = context['limit']
    search_key = context['search_key']
    type       = context['type']
    user_name  = context['user_name']
    parent_id  = xutils.get_argument("parent_id", "")
    words      = None
    rows       = []

    if parent_id == "":
        parent_id = None

    start_time = time.time()
    if search_key != None and search_key != "":
        # TODO 公共笔记的搜索
        search_key = xutils.unquote(search_key)
        words      = split_words(search_key)
        rows       = NOTE_DAO.search_name(words, user_name, parent_id = parent_id)
        rows       = rows[offset: offset + limit]
        cost_time  = time.time() - start_time
        NOTE_DAO.add_search_history(user_name, search_key, "note", cost_time)

    return build_date_result(rows, 'ctime', sticky_title = True, group_title = True)

def list_project_func(context):
    offset    = context['offset']
    limit     = context['limit']
    user_name = context['user_name']
    if offset > 0:
        rows = []
    else:
        rows = NOTE_DAO.list_group(user_name)
        rows.insert(0, StickyGroup())
    return build_date_result(rows, 'mtime', sticky_title = True, archived_title = True)

def list_public_func(context):
    offset = context['offset']
    limit  = context['limit']
    rows   = NOTE_DAO.list_public(offset, limit)
    return build_date_result(rows, 'ctime')

def list_sticky_func(context):
    offset    = context['offset']
    limit     = context['limit']
    user_name = context['user_name']
    rows      = NOTE_DAO.list_sticky(user_name, offset, limit)
    return build_date_result(rows, 'ctime', group_title = True)

def list_removed_func(context):
    offset    = context['offset']
    limit     = context['limit']
    user_name = context['user_name']
    rows      = NOTE_DAO.list_removed(user_name, offset, limit)
    return build_date_result(rows, 'ctime')

def list_archived_func(context):
    offset    = context['offset']
    limit     = context['limit']
    user_name = context['user_name']
    rows      = NOTE_DAO.list_archived(user_name, offset, limit)
    return build_date_result(rows, 'ctime')

def list_by_type_func(context):
    type      = context['type']
    offset    = context['offset']
    limit     = context['limit']
    user_name = context['user_name']
    rows      = NOTE_DAO.list_by_type(user_name, type, offset, limit)
    return build_date_result(rows, 'ctime')

def list_plan_func(context):
    offset    = context['offset']
    limit     = context['limit']
    user_name = context['user_name']
    rows      = NOTE_DAO.list_by_type(user_name, 'plan', offset, limit)
    old_task  = TaskGroup("待办任务(旧版)")
    if old_task.size > 0:
        rows.append(old_task)
    return build_date_result(rows, 'ctime')

def list_all_func(context):
    offset    = context['offset']
    limit     = context['limit']
    user_name = context['user_name']
    rows      = NOTE_DAO.list_recent_created(user_name, offset, limit)
    return build_date_result(rows, 'ctime')

def list_recent_edit_func(context):
    offset    = context['offset']
    limit     = context['limit']
    user_name = context['user_name']
    rows      = NOTE_DAO.list_recent_edit(user_name, offset, limit)
    return build_date_result(rows, 'mtime')
    
def default_list_func(context):
    offset    = context['offset']
    limit     = context['limit']
    user_name = context['user_name']
    parent_id = context['parent_id']
    rows      = NOTE_DAO.list_by_parent(user_name, parent_id, offset, limit, 'ctime_desc')
    return build_date_result(rows, 'ctime', sticky_title = True, group_title = True)


LIST_FUNC_DICT = {
    'root'    : list_project_func,
    'group'   : list_project_func,
    'public'  : list_public_func,
    'sticky'  : list_sticky_func,
    'removed' : list_removed_func,
    'archived': list_archived_func,

    'recent_edit': list_recent_edit_func,

    'md'      : list_by_type_func,
    'gallery' : list_by_type_func,
    'document': list_by_type_func,
    'html'    : list_by_type_func,
    'list'    : list_by_type_func,
    'table'   : list_by_type_func,
    'csv'     : list_by_type_func,

    'plan'    : list_plan_func,
    'all'     : list_all_func,
    "search"  : list_search_func,
}

class TimelineAjaxHandler:

    def GET(self):
        offset     = xutils.get_argument("offset", 0, type=int)
        limit      = xutils.get_argument("limit", 20, type=int)
        type       = xutils.get_argument("type", "root")
        parent_id  = xutils.get_argument("parent_id", None, type=str)
        search_key = xutils.get_argument("key", None, type=str)
        user_name  = xauth.current_name()

        list_func = LIST_FUNC_DICT.get(type, default_list_func)
        return list_func(locals())

class DateTimeline:
    @xauth.login_required()
    def GET(self):
        year  = xutils.get_argument("year")
        month = xutils.get_argument("month")
        if len(month) == 1:
            month = "0" + month
        user_name  = xauth.current_name()
        rows = NOTE_DAO.list_by_date("ctime", user_name, "%s-%s" % (year, month))
        result = dict()
        for row in rows:
            date = re.match(r"\d+\-\d+", row.ctime).group(0)
            # 优化数据大小
            row.content = ""
            if date not in result:
                result[date] = []
            result[date].append(row)
        return result


class BaseTimelineHandler:

    note_type = "group"

    def GET(self):
        type        = xutils.get_argument("type", self.note_type)
        parent_id   = xutils.get_argument("parent_id", "")
        key         = xutils.get_argument("key", "")
        title       = u"最新笔记"
        show_create = True

        if type == "public":
            show_create = False
        else:
            xauth.check_login()

        if type == "search" and key == "":
            raise web.found("/search")

        user_name  = xauth.current_name()
        title      = NOTE_TYPE_DICT.get(type, u"最新笔记")
        title_link = None

        search_title = u"笔记"
        file         = NOTE_DAO.get_by_id(parent_id)
        
        if file != None:
            title = file.name
            search_title = file.name
            title_link = PathLink(file.name, file.url)

        return xtemplate.render("note/page/timeline.html", 
            title = title,
            type  = type,
            file  = file,
            key   = key,
            show_create = show_create,
            search_action = "/note/timeline",
            search_placeholder = T(u"搜索" + search_title),
            search_ext_dict = dict(parent_id = parent_id),
            parent_link = get_parent_link(user_name, type),
            title_link  = title_link,
            CREATE_BTN_TEXT_DICT = CREATE_BTN_TEXT_DICT,
            show_aside = False)

class TimelineHandler(BaseTimelineHandler):
    note_type = "group"

class PublicTimelineHandler(TimelineHandler):
    """公共笔记的时光轴视图"""
    note_type = "public"


class GalleryListHandler(BaseTimelineHandler):
    note_type = "gallery"


class TableListHandler(BaseTimelineHandler):
    note_type = "csv"


class HtmlListHandler(BaseTimelineHandler):
    note_type = "html"


class MarkdownListHandler(BaseTimelineHandler):
    note_type = "md"


class DocumentListHandler(BaseTimelineHandler):
    note_type = "document"


class ListNoteHandler(BaseTimelineHandler):
    note_type = "list"


class PlanListHandler(BaseTimelineHandler):
    note_type = "plan"


class StickyHandler(BaseTimelineHandler):
    note_type = "sticky"


class RemovedHandler(BaseTimelineHandler):
    note_type = "removed"


xurls = (
    r"/note/timeline/month", DateTimeline,
    r"/note/api/timeline", TimelineAjaxHandler,

    # 时光轴视图
    r"/note/timeline"       , TimelineHandler,
    r"/note/public"         , PublicTimelineHandler,
    r"/note/gallery"        , GalleryListHandler,
    r"/note/table"          , TableListHandler,
    r"/note/csv"            , TableListHandler,
    r"/note/document"       , DocumentListHandler,
    r"/note/html"           , HtmlListHandler,
    r"/note/md"             , MarkdownListHandler,
    r"/note/list"           , ListNoteHandler,
    r"/note/plan"           , PlanListHandler,
    r"/note/sticky"         , StickyHandler,
    r"/note/removed"        , RemovedHandler,
)

