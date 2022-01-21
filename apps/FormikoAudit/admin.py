from django.contrib import admin

# Register your models here.

from django.contrib import admin
from .models import LineItem, Shoot, CameraSetting

@admin.register(LineItem)
class LineItemAdmin(admin.ModelAdmin):
    #model = LineItem
    list_display = ('id', 'name', 'status', 'created', 'updated')

@admin.register(Shoot)
class ShootAdmin(admin.ModelAdmin):
    list_display = ('id', 'project', 'starttime', 'location', 'created', 'updated')

@admin.register(CameraSetting)
class CameraSettingAdmin(admin.ModelAdmin):
    list_display = ('id', 'operator', 'whitebalance', 'camera', 'created', 'updated')
