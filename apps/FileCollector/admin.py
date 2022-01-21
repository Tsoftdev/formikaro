from django.contrib import admin
from django.contrib.admin import register
from django.utils.safestring import mark_safe
from django.contrib import messages
from django.utils.translation import ngettext

# Register your models here.
from .models import File, Intake, Product, Order, OrderProduct
from .models import Company, Client, ProjectManager, Project, Video, VimeoResponse, UserRole, Crew, ProjectVideo
from apps.FormikoBot.models import Asset
from django.db.models import Q

from nested_inline.admin import NestedTabularInline, NestedModelAdmin
from django import forms

from formikaro.utils import ExportCsvMixin
from formikaro.admin import custom_admin_site
from .forms import AssetSelectForm

custom_admin_site.register(Intake)


class FilesInline(admin.TabularInline):
    model = File
    extra = 3


class IntakeAdmin(admin.ModelAdmin, ExportCsvMixin):
    #exclude = ['created']
    # fieldsets = [
    #     (None,               {'fields': ['sender']}),
    #     ('Date information', {'fields': ['created'], 'classes': ['collapse']}),
    # ]
    list_display = ('id', 'sender', 'client', 'order', 'shop_order_id', 'created')
    inlines = [FilesInline]
    actions = ['export_as_csv']

    


# @admin.register(Product)
# class ProductAdmin(admin.ModelAdmin):
#    model = Product


class OrderProductInline(admin.StackedInline):
    model = OrderProduct
    min_num = 1
    extra = 0
    form = AssetSelectForm


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin, ExportCsvMixin):
    model = Order
    list_display = ('id', 'fid', 'client', 'origin', 'status', 'product_count', 'shop_order_id', 'placed', 'created', 'updated')
    inlines = [OrderProductInline]
    actions = ['set_pending', 'export_as_csv']
    search_fields = ['id', 'shop_order_id', 'shop_unique_token', 'status', 'payment_reference_number']
    #filter_horizontal = ('orderproduct',)

    # not working, this should return the count for all products linked to this order
    def product_count(self, obj):
        count = OrderProduct.objects.filter(order=obj.id).count()
        return count

    # this action function sets all selected products to active
    def set_pending(self, request, queryset):
        updated = queryset.update(status='PENDING')
        self.message_user(request, ngettext(
            '%d product status was set as pending.',
            '%d products\' status was set as pending.',
            updated,
        ) % updated, messages.SUCCESS)

    set_pending.short_description = "Status: PENDING"


class ProjectProjectmanagerInline(admin.TabularInline):
    model = Project.projectmanager.through
    extra = 0

    
class ProjectVideoInline(NestedTabularInline):
    model = Video
    fields = ['title', 'status', 'version', 'description', 'vimeo_passwd', 'unique_fn', ('url'), 'created', 'updated']
    readonly_fields = (
    'unique_fn', 'description', 'vimeo_passwd', 'title', 'status', 'version', 'url', 'created', 'updated')
    can_delete = False
    extra = 0


class VimeoResponseInline(admin.StackedInline):
    model = VimeoResponse


class VideoInline(NestedTabularInline):
    model = Video
    extra = 0
    fields = ['_appendend_urls', '_linked_title', 'status', 'version', 'description', 'vimeo_passwd', 'unique_fn',
              'url', 'url_review', 'url_download', 'created', 'updated']
    readonly_fields = (
    '_appendend_urls', '_linked_title', 'unique_fn', 'vimeo_passwd', 'status', 'url', 'url_review', 'url_download',
    'created', 'updated')
    ordering = ['created']
    can_delete = False

    def _appendend_urls(self, obj):
        return ('URL: %s &#13;Review-URL: %s &#13;Passwort: %s &#13;Download-Link: %s') % (
        obj.url, obj.url_review, obj.vimeo_passwd, obj.url_download)

    @mark_safe
    def _linked_title(self, obj):
        return '<a href="/admin/app/project/' + str(obj.project.id) + '/change/#videos">%s</a>' % obj.title

    _linked_title.short_description = "Title"
    _appendend_urls.short_description = "Copy clipboard"


class ProjectClientInline(NestedTabularInline):
    model = Project
    extra = 0
    inlines = [VideoInline, ]


class CompanyClientInline(NestedTabularInline):
    model = Project
    extra = 0
    fields = ['_get_linked_name', '_get_linked_client']
    readonly_fields = ['_get_linked_name', '_get_linked_client']

    @mark_safe
    def _get_linked_name(self, obj):
        return '<a href="/admin/app/project/' + str(obj.id) + '/change/#videos">%s</a>' % obj.name

    _get_linked_name.short_description = "Project"

    @mark_safe
    def _get_linked_client(self, obj):
        return '<a href="/admin/app/client/' + str(obj.client.id) + '/change">%s %s</a>' % (
        obj.client.firstname, obj.client.lastname)

    _get_linked_client.short_description = "Client"


class ProjectmanagerInline(admin.TabularInline):
    model = ProjectManager


class CompanyForm(forms.ModelForm):
    class Meta:
        model = Company
        fields = '__all__'

    def __init__(self, *args, **kwargs):
        super(CompanyForm, self).__init__(*args, **kwargs)
        company = kwargs.get('instance', None)
        assets_queryset = self.fields['assets'].queryset
        if 'assets' in self.initial:
            # show all company owned assets plus public assets
            # Example of generated SQL is SELECT * FROM "fo_asset" WHERE
            # ("fo_asset"."client_owner_id" IS NULL AND
            # ("fo_asset"."company_owner_id" IS NULL OR "fo_asset"."company_owner_id" = 1))
            # is equivalent to filtering for client_owner=null then filter the resulting queryset again for
            # company_owner = null or company_owner_id=id
            self.fields['assets'].queryset = assets_queryset.filter(
                Q(client_owner__isnull=True), Q(company_owner__isnull=True) | Q(company_owner_id=company.id)
            )
        else:
            # just show assets that are not connected to a specific company or client
            self.fields['assets'].queryset = assets_queryset.filter(
                Q(client_owner__isnull=True), Q(company_owner__isnull=True)
            )


@admin.register(Company)
class CompanyAdmin(admin.ModelAdmin, ExportCsvMixin):
    inlines = [CompanyClientInline]  # AssetCompanytInline]
    list_display = ('id', 'name', 'abbreviation', '_get_linked_clients', 'country', 'language', 'created')
    form = CompanyForm
    filter_horizontal = ['assets']
    actions = ['export_as_csv']
    
    @mark_safe
    def _get_linked_clients(self, obj):
        clients = Client.objects.filter(company=obj.id)
        client_links=''
        for client in clients:
            client_links += '<a href="/admin/FileCollector/client/' + str(client.id) + '/change">%s %s</a><br>' % (client.firstname, client.lastname)
        return client_links

    _get_linked_clients.short_description = "Clients" 


@admin.register(UserRole)
class UserRoleAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'created', 'updated')

    
@admin.register(ProjectManager)
class ProjectmanagerAdmin(admin.ModelAdmin):
    list_display = ('id', 'firstname', 'lastname')
    date_hierarchy = 'created'
    inlines = [ProjectProjectmanagerInline, ]

class ClientForm(forms.ModelForm):
    class Meta:
        model = Client
        fields = '__all__'

    def __init__(self, *args, **kwargs):
        super(ClientForm, self).__init__(*args, **kwargs)
        client = kwargs.get('instance', None)
        assets_queryset = self.fields['assets'].queryset
        if 'assets' in self.initial:
            # show all client owned assets + client company assets + public assets
            # Example of generated SQL is SELECT * FROM "fo_asset" WHERE
            # ("fo_asset"."company_owner_id" IS NULL AND
            # ("fo_asset"."client_owner_id" IS NULL OR "fo_asset"."client_owner_id" = 1))
            self.fields['assets'].queryset = assets_queryset. \
                filter(
                Q(company_owner__isnull=True) & Q(client_owner__isnull=True) | Q(client_owner_id=client.id) |
                Q(company_owner_id=client.company_id)
            )
        else:
            # just show assets that are not connected to a specific company or client
            self.fields['assets'].queryset = assets_queryset.filter(
                Q(client_owner__isnull=True), Q(company_owner__isnull=True)
            )


@admin.register(Client)
class ClientAdmin(NestedModelAdmin, ExportCsvMixin):
    list_display = ('_get_client_name', 'abbreviation', 'email', 'company', 'shop_username', 'created', 'updated')
    inlines = [ProjectClientInline]
    filter_horizontal = ['assets']
    actions = ['export_as_csv']
    form = ClientForm
    
    def _get_client_name(self, obj):
        client_name = '%s %s' % (obj.firstname, obj.lastname)
        return client_name

    _get_client_name.short_description = "Full Client name" 


@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    list_display = ('name', 'abbreviation', 'company', 'folderid', 'created', 'updated')
    fieldsets = (
        (None, {
            'classes': 'wide',
            'fields': (('name', 'abbreviation', 'default_vimeo_passwd'), 'change_log', 'deadline', 'feedbackloops', 'budget', 'paid', 'folderid', 'status', 'tasks'),
        }),
        ('Persons', {
            'fields': ('projectmanager', 'company', 'client',),
        }),
        #('Tasks', {
        #    'fields': (('name', 'creator', 'user', 'status'),),
        #}),
        #('Video targets', {
        #    'fields': (('video_target_width', 'video_target_height', 'video_target_size', 'video_target_duration'),),
        #}),

    )
    list_filter = ('company', 'projectmanager', 'created')

    search_fields = ['name']
    autcomplete_field = ['name']
    date_hierarchy = 'created'
    filter_horizontal = ('projectmanager',)
    inlines = [VideoInline, ]


@admin.register(ProjectVideo)
class ProjectVideoAdmin(admin.ModelAdmin):
    model = ProjectVideo
    list_display = ('name', 'created', 'updated')

admin.site.register(Intake, IntakeAdmin)
# admin.site.register(File)

#@register(Video)
#class VideoAdmin(admin.ModelAdmin):
#    pass

@admin.register(Video)
class VideoAdmin(admin.ModelAdmin):
    model = Video
    list_display = ('pk', 'project', 'order_product', 'url', 'version', 'status', 'created', 'updated')