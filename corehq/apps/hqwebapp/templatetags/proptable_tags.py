"""
A collection of templatetags and helper functions for declaratively defining a
property table layout with multiple (optionally named) tables of some number of
rows of possibly differing length, where each row consists of a number of names
and values which are calculated based on an expression and a data source.

Supports psuedo-tables using dls and real tables.

"""

import collections
import datetime
from itertools import zip_longest

from django import template
from django.template.defaultfilters import yesno
from django.utils.html import conditional_escape, escape
from django.utils.safestring import mark_safe

import pytz
from jsonobject.exceptions import BadValueError

from dimagi.ext.jsonobject import DateProperty
from dimagi.utils.chunked import chunked
from dimagi.utils.dates import safe_strftime

from corehq.apps.hqwebapp.doc_info import get_doc_info_by_id
from corehq.apps.hqwebapp.templatetags.hq_shared_tags import pretty_doc_info
from corehq.const import USER_DATE_FORMAT, USER_DATETIME_FORMAT
from corehq.util.dates import iso_string_to_datetime
from corehq.util.timezones.conversions import PhoneTime, ServerTime

register = template.Library()


def _is_list_like(val):
    return isinstance(val, collections.Iterable) and not isinstance(val, str)


def _parse_date_or_datetime(val):
    def parse():
        if not val:
            return None

        # datetime is a subclass of date
        if isinstance(val, datetime.date) or not isinstance(val, str):
            return val

        try:
            dt = iso_string_to_datetime(val)
        except ValueError:
            try:
                return DateProperty().wrap(val)
            except BadValueError:
                return val
        else:
            if not any([dt.hour, dt.minute, dt.second, dt.microsecond]):
                return dt.date()
            else:
                return dt

    result = parse()
    if isinstance(result, datetime.datetime):
        assert result.tzinfo is None
    return result


def _format_slug_string_for_display(key):
    return key.replace('_', ' ').replace('-', ' ')


def _to_html(val, key=None, level=0, timeago=False):
    """
    Recursively convert a value to its HTML representation using <dl>s for
    dictionaries and <ul>s for lists.
    """
    recurse = lambda k, v: _to_html(v, key=k, level=level + 1, timeago=timeago)

    def _key_format(k, v):
        if not _is_list_like(v):
            return _format_slug_string_for_display(k)
        else:
            return ""

    if isinstance(val, dict):
        ret = "".join(
            ["<dl %s>" % ("class='well'" if level == 0 else '')] + 
            ["<dt>%s</dt><dd>%s</dd>" % (_key_format(k, v), recurse(k, v))
             for k, v in val.items()] +
            ["</dl>"])

    elif _is_list_like(val):
        ret = "".join(
            ["<dl>"] +
            ["<dt>%s</dt><dd>%s</dd>" % (key, recurse(None, v)) for v in val] +
            ["</dl>"])

    elif isinstance(val, datetime.date):
        if isinstance(val, datetime.datetime):
            fmt = USER_DATETIME_FORMAT
        else:
            fmt = USER_DATE_FORMAT

        iso = val.isoformat()
        ret = mark_safe("<time %s title='%s' datetime='%s'>%s</time>" % (
            "class='timeago'" if timeago else "", iso, iso, safe_strftime(val, fmt)))
    else:
        if val is None:
            val = '---'

        ret = escape(val)

    return mark_safe(ret)


def get_display_data(data, prop_def, processors=None, timezone=pytz.utc):
    # when prop_def came from a couchdbkit document, it will be a LazyDict with
    # a broken pop method.  This conversion also has the effect of a shallow
    # copy, which we want.
    prop_def = dict(prop_def)

    default_processors = {
        'yesno': yesno,
        'doc_info': lambda value: pretty_doc_info(
            get_doc_info_by_id(data['domain'], value)
        )
    }
    processors = processors or {}
    processors.update(default_processors)

    expr_name = _get_expr_name(prop_def)
    expr = prop_def.pop('expr')
    name = prop_def.pop('name', None) or _format_slug_string_for_display(expr)
    format = prop_def.pop('format', None)
    process = prop_def.pop('process', None)
    timeago = prop_def.get('timeago', False)
    has_history = prop_def.pop('has_history', False)

    val = eval_expr(expr, data)

    if prop_def.pop('parse_date', None):
        try:
            val = _parse_date_or_datetime(val)
        except Exception:
            # ignore exceptions from date parsing
            pass
    is_phone_time = prop_def.pop('is_phone_time', False)
    if isinstance(val, datetime.datetime):
        if not is_phone_time:
            val = ServerTime(val).user_time(timezone).done()
        else:
            val = PhoneTime(val, timezone).user_time(timezone).done()

    try:
        val = conditional_escape(processors[process](val))
    except KeyError:
        val = mark_safe(_to_html(val, timeago=timeago))
    if format:
        val = mark_safe(format.format(val))

    return {
        "expr": expr_name,
        "name": name,
        "value": val,
        "has_history": has_history,
    }


def _get_expr_name(prop_def):
    if callable(prop_def['expr']):
        return prop_def['name']
    else:
        return prop_def['expr']


def eval_expr(expr, dict_data):
    """
    If expr is a string, will do a dict lookup using that string as a key.

    If expr is a callable, will call it on the dict.
    """
    if callable(expr):
        return expr(dict_data)
    else:
        return dict_data.get(expr, None)


def get_tables_as_rows(data, definition, processors=None, timezone=pytz.utc):
    """
    Return a low-level definition of a group of tables, given a data object and
    a high-level declarative definition of the table rows and value
    calculations.

    """

    sections = []

    for section in definition:
        rows = [
            [get_display_data(
                data,
                prop,
                timezone=timezone,
                processors=processors) for prop in row]
            for row in section['layout']]

        max_row_len = max(list(map(len, rows))) if rows else 0
        for row in rows:
            if len(row) < max_row_len:
                row.append({
                    "colspan": 2 * (max_row_len - len(row))
                })

        sections.append({
            "name": section.get('name') or '',
            "rows": rows
        })

    return sections


def get_tables_as_columns(*args, **kwargs):
    sections = get_tables_as_rows(*args, **kwargs)
    for section in sections:
        section['columns'] = list(zip_longest(*section['rows']))
        del section['rows']

    return sections


def get_default_definition(keys, num_columns=1, name=None, phonetime_fields=None, date_fields=None):
    """
    Get a default single table layout definition for `keys` split across
    `num_columns` columns.

    All datetimes will be treated as "phone times".
    (See corehq.util.timezones.conversions.PhoneTime for more context.)

    """
    phonetime_fields = phonetime_fields or set()
    date_fields = date_fields or set()
    layout = chunked(
        [
            {
                "expr": prop,
                "is_phone_time": prop in phonetime_fields,
                "has_history": True,
                "parse_date": prop in date_fields
            }
            for prop in keys
        ],
        num_columns
    )

    return [
        {
            "name": name,
            "layout": list(layout)
        }
    ]
