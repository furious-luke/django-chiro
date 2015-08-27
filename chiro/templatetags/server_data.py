import json
from django.template import Library
from django.utils.html import escapejs
from django.utils.safestring import mark_safe
from ..serial import ResourceEncoder

register = Library()

@register.filter(is_safe=True)
def server_data(value, name='server_data'):
    data = escapejs(json.dumps(value, cls=ResourceEncoder))
    return mark_safe('%s = "%s";'%(name, data))
