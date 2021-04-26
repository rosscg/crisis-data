from django import template
from django.template.defaultfilters import stringfilter
import re

register = template.Library()

@register.filter
@stringfilter
def add_hyperlink(text):
    regex = re.compile(r"(https?:\/\/\S*)", re.IGNORECASE)
    text = re.sub(regex, r"<a href=\1 target=\"_blank\">\1</a>", text)
    return text
