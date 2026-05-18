from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from django import template

register = template.Library()


@register.simple_tag
def csv_export_href(url, csv_query_string='', export_type=''):
    parts = urlsplit(str(url))
    query_pairs = [
        (key, value)
        for key, value in parse_qsl(parts.query, keep_blank_values=False)
        if key != 'type'
    ]
    query_pairs.extend(
        (key, value)
        for key, value in parse_qsl(str(csv_query_string or ''), keep_blank_values=False)
        if key != 'type'
    )
    if export_type:
        query_pairs.insert(0, ('type', export_type))
    return urlunsplit((
        parts.scheme,
        parts.netloc,
        parts.path,
        urlencode(query_pairs),
        parts.fragment,
    ))
