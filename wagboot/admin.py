# Register your models here.
from django.contrib import admin

from wagboot.models import Css

try:
    from reversion.admin import VersionAdmin
    base_admin = VersionAdmin
except ImportError:
    # django_reversion is not available
    base_admin = admin.ModelAdmin


class CssAdmin(base_admin):
    pass


admin.site.register(Css, CssAdmin)
