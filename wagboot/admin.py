# Register your models here.
from django.contrib.admin import ModelAdmin

try:
    from reversion.admin import VersionAdmin
    base_admin = VersionAdmin
except ImportError:
    # django_reversion is not available
    base_admin = ModelAdmin


class CssAdmin(base_admin):
    pass
