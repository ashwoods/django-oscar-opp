from django.conf import settings  # noqa

from appconf import AppConf


class OpenPasswordPlatformConf(AppConf):
    USERID = None
    ENTITYID = None
    PASSWORD = None
    BASEURL = None
