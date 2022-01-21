# Formikaro.FormikoBot.Admin
# Module 1
#

from nested_inline.admin import NestedTabularInline, NestedModelAdmin

from django.contrib import admin
from jsoneditor.admin import JSONFieldAdminMixin
from django.db import models

from .models import WorkStep, Asset, AssetType, AssetPreset, Task, TaskPreset, TaskType
from apps.FileCollector.models import Company


@admin.register(Task)
class TaskAdmin(JSONFieldAdminMixin, admin.ModelAdmin):
    model=Task
    list_display = ('name', 'description', 'creator', 'user',  'status', 'mode', 'priority', 'created')

@admin.register(TaskType)
class TaskAdmin(JSONFieldAdminMixin, admin.ModelAdmin):
    model=TaskType
    list_display = ('name', 'description',  'created')
    
@admin.register(TaskPreset)
class TaskPresetAdmin(JSONFieldAdminMixin, admin.ModelAdmin):
    model=TaskPreset
    list_display = ('title', 'name', 'creator', 'status', 'mode', 'priority',  'pres_created')
    
@admin.register(AssetType)
class AssetTypeAdmin(JSONFieldAdminMixin, admin.ModelAdmin):
    model=AssetType
    list_display = ('title', 'extension', 'is_file', 'maxlength',  'created')
    
@admin.register(Asset)
class AssetAdmin(JSONFieldAdminMixin, admin.ModelAdmin):
    model = Asset
    search_fields = ['name', 'id']
    #list_filter = [ 'type']
    list_display = (
        'id', 'name',  'value', 'asset_used_by', 'company_owner', 'client_owner',
        'use_count', 'was_created'
    )

    def was_created(self, obj):
        return obj.created.strftime('%d.%m.%y %H:%M')
    was_created.short_description = "Created"

    def asset_used_by(self, obj):
        companies = ";".join([company.name for company in obj.company_assets.all()])
        companies = companies if companies else 'None'
        clients = ";".join([client.get_full_name() for client in obj.client_assets.all()])
        clients = clients if clients else 'None'
        return "Companies: {companies}\n Clients:{clients}".format(companies=companies, clients=clients)
    asset_used_by.short_description = "Asset Used By"
    
    # not working!
    def use_count(self, obj):
        #count = Company.objects.filter(assets=obj.id).Count()
        count = Company.objects.filter(assets=obj.id).count() #obj.id
        return count
    use_count.short_description="Used"


    
@admin.register(AssetPreset)
class AssetPresetAdmin(JSONFieldAdminMixin, admin.ModelAdmin):
    model=AssetPreset
    list_display = ('title',  'name', 'value', 'created')
    fields = ('title', 'name', 'value', 'maxlength', 'assettype', 'source', 'tasks', 'description', 'pres_description')
    
    
#@admin.register(WorkStep)
class WorkStepAdmin(JSONFieldAdminMixin, admin.ModelAdmin):
    model = WorkStep
    save_as = True
    list_display = ('name', 'mode', 'created')
    
    #formfield_overrides = {
    #    models.JSONField: {'widget': JSONEditorWidget},
    #}
    
    # how to add additional HELP TEXT                  
    # https://stackoverflow.com/questions/3728617/adding-model-wide-help-text-to-a-django-models-admin-form