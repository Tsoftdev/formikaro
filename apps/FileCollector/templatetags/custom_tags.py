import time
import os

from django import template
from django.utils.safestring import mark_safe
from apps.FileCollector.models import OrderProduct
from apps.ProductManager.models import ProductText

from django.conf import settings

RUNTIME_SAVE_INTERVAL = settings.RUNTIME_SAVE_INTERVAL

register = template.Library()


@register.filter(name='seconds_to_clock')
def seconds_to_clock(seconds):
    return time.strftime('%H:%M:%S', time.gmtime(seconds))


@register.simple_tag
def product_text_title(product_id, language):
    product_text = ProductText.objects.filter(language__abbreviation__iexact=language, product_id=product_id).first()
    return product_text.title if product_text else None


@register.simple_tag
def client_total_products(client_id):
    return OrderProduct.objects.filter(order__client_id=client_id).count()


@register.simple_tag
def client_asset_exists(asset, client):
    state = asset.exists_client(client)
    return state


@register.simple_tag
def company_asset_exists(asset, company):
    state = asset.exists_company(company)
    return state


@register.simple_tag
def asset_company_folder_intranet(asset, company):
    folder = asset.get_company_folder(True, company, True)
    return folder


@register.simple_tag
def asset_client_folder_intranet(asset, client):
    folder = asset.get_client_folder(True, client, True)
    return folder


@register.simple_tag
def asset_folder(asset, client):
    folder = asset.get_client_folder(True, client)
    return folder


@register.simple_tag
def project_folder(project):
    folder = project.get_folder(True)
    return folder

# this function is formating the internal log information on various models to be more human readable in the views
# as each log entry is written with a time stamp it uses this to inject a <br> tag. This should work until 2100 :)


@register.filter('format_log')
def format_log(log):
    pattern = '[20'
    formated_log = log.replace(pattern, '<br>' + pattern)
    return mark_safe(formated_log)


@register.filter('filesize_format')
def filesize_format(num, suffix='B'):
    if not num: return '0'
    for unit in ['', 'K', 'M', 'G', 'T', 'P', 'E', 'Z']:
        if abs(num) < 1024.0:
            return "%3.1f %s%s" % (num, unit, suffix)
        num /= 1024.0
    return "%.1f %s%s" % (num, 'Yi', suffix)

@register.filter('bitrate_format')
def bitrate_format(num, suffix='B/s'):
    if not num: return '0'
    for unit in ['', 'K', 'M', 'G', 'T', 'P', 'E', 'Z']:
        if abs(num) < 1024.0:
            return "%3.1f %s%s" % (num, unit, suffix)
        num /= 1024.0
    return "%.1f %s%s" % (num, 'Yi', suffix)


def td_format(td_object):
    seconds = int(td_object.total_seconds())
    periods = [
        ('year', 60 * 60 * 24 * 365),
        ('month', 60 * 60 * 24 * 30),
        ('day', 60 * 60 * 24),
        ('hour', 60 * 60),
        ('minute', 60),
        # ('second',      1)
    ]

    strings = []
    for period_name, period_seconds in periods:
        if seconds > period_seconds:
            period_value, seconds = divmod(seconds, period_seconds)
            has_s = 's' if period_value > 1 else ''
            strings.append("%s %s%s" % (period_value, period_name, has_s))

    return " ".join(strings)


@register.filter('date_diff')
def date_diff(later_date, earlier_date):
    diff = later_date - earlier_date
    return td_format(diff)


@register.filter('time_diff')
def time_diff(seconds):
    periods = [
        ('day', 60 * 60 * 24),
        ('hour', 60 * 60),
        ('minute', 60),
        ('second', 1)
    ]

    strings = []
    for period_name, period_seconds in periods:
        if seconds > period_seconds:
            period_value, seconds = divmod(seconds, period_seconds)
            has_s = 's' if period_value > 1 else ''
            strings.append("%s %s%s" % (period_value, period_name, has_s))

    return " ".join(strings)


@register.filter(name='subtract')
def subtract(value, arg):
    return value - arg


# Return dictionary value given the key. Return None if key doesn't exist
@register.filter(name='get_dict_item')
def get_dict_item(dictionary, key):
    return dictionary.get(key)

@register.simple_tag
def get_RuntimeSaveInterval():
    return settings.RUNTIME_SAVE_INTERVAL


@register.simple_tag
def get_env_var(key):
    return os.environ.get(key)