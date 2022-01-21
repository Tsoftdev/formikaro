from django.contrib import admin
from django.contrib import messages
from django.utils.translation import ngettext
from django.http import HttpResponseRedirect
from django.utils.html import format_html
from django.shortcuts import render
from django.template.response import TemplateResponse
from django.db.models import Q
from django.db import IntegrityError
from django.db.models import Count
from django.urls import reverse
from django.utils.safestring import mark_safe
from django.http import HttpResponse
from django.http import JsonResponse
from django import forms

from django.core import serializers
from nested_inline.admin import NestedTabularInline, NestedStackedInline, NestedModelAdmin

import datetime

from .models import Product, Language, Resolution, ProductText, ProductBase, VideoFormat, ProductImage, ProductImageText

from formikaro.utils import ExportCsvMixin

# Register your models here.

#this is the inline form for the multilingual product description texts (including titles)
class ProductTextInline(admin.TabularInline):
    model= ProductText
    extra = 0
    list_display= ('title', 'desc_short', 'desc_long', 'language')

admin.site.register(ProductImageText)

class ProductImageInline(admin.TabularInline):
    model = ProductImage
    extra = 0
    min_num = 0

#@admin.register(Product)
class ProductAdmin(admin.ModelAdmin, ExportCsvMixin):
    model = Product
    save_as = True
    change_form_template = "admin/productmanager/product/change_form.html"
    
    list_display = ('get_title', 'get_base_link',  'is_active', 'variety', 'get_mode', 'version', 'language', 'resolution', '_texts', 'fsin', 'format_date_created', 'format_date_updated')
    actions=['set_active', 'set_inactive', 'duplicate_product', 'export_product_shop_csv', 'export_product_fo_csv', 'export_csv_selector']
    
    #The FSIN cannot be changed by the user as it is generated
    readonly_fields=['fsin']
    
    #this calls the inline function so we can edit the texts directly in the product form
    inlines = [ ProductTextInline, ProductImageInline]
    
    # __ because it refers the via ForeignKey linked model ProductBase
    search_fields = ['base__name', 'fsin']
    list_filter = ['is_active', 'variety', 'resolution', 'version']
    
    def format_date_created(self, obj):
        return obj.created.strftime('%d.%m.%y %H:%M')
    format_date_created.short_description="Created"
    
    def format_date_updated(self, obj):
        return obj.updated.strftime('%d.%m.%y %H:%M')
    format_date_updated.short_description="Updated"
    
    def get_base(self, obj):
        return obj.base.name
    get_base.short_description = 'ProductBase'
    
    def get_title(self, obj):
        #return obj.product_text.title
        #return ProductTextModel.objects.filter(product=obj.pk)[0].title
        #return obj.product_text.through.objects.all()[:1]
        return obj.fsin
        #obj.product_text.through.objects.all()[0]
        #return 'x'
    get_title.short_description = 'Title'
    
    def get_mode(self, obj):
        return obj.base.mode
    get_mode.short_description = 'Mode'
    
    #def show_productbase_url(self, obj):
    #    return '<a href="%s">%s</a>' % (obj.firm_url, obj.firm_url)
    #show_productbase_url.allow_tags = True

    def get_base_link(self, Product):
        #url = reverse("admin:product_base_change", args=#[Product.base.id])
        link = '<a href="%s">%s</a>' % (reverse("admin:ProductManager_productbase_change", args=(Product.base.id,)) , mark_safe(Product.base.name))
        return mark_safe(link)
    get_base_link.short_description = 'ProductBase'

    # list all related product text + links 
    def _texts(self, Product):
        product_texts = ProductText.objects.filter(product=Product.id)
        product_text_info = ''
        for product_text in product_texts:
            product_text_info += '<a href="%s">%s (%s)</a><br>' % (reverse("admin:ProductManager_producttext_change", args=(product_text.id,)), product_text.title, product_text.language)
                                                              
        return mark_safe(product_text_info)
    _texts.short_description = 'ProductTexts'

    
    #product_base_link.short_description = "Click Me"
    
    #ACTIONS
    #this action function sets all selected products to active
    def set_active(self, request, queryset):
        updated = queryset.update(is_active=True)
        self.message_user(request, ngettext(
            '%d product was successfully set as active.',
            '%d products were successfully set as active.',
            updated,
        ) % updated, messages.SUCCESS)
    set_active.short_description = "Activate"

    #this action function sets all selected products to inactive
    def set_inactive(self, request, queryset):
        updated = queryset.update(is_active=False)
        self.message_user(request, ngettext(
            '%d product was successfully set as not active.',
            '%d products were successfully set as not active.',
            updated,
        ) % updated, messages.SUCCESS)
    set_inactive.short_description = "Deactivate"
    
    #this action function duplicates all selected products 
    def duplicate_product(self, request, queryset):
        try:
            updated=0
            for object in queryset:
                object.id = None
                #for security deactived newly created product as it has no FSIN
                object.is_active = False 
                object.fsin = None
                object.save()
                updated=updated+1
                
            self.message_user(request, ngettext(
            '%d product was successfully duplicated.',
            '%d products were successfully duplicated.',
            updated,
        ) % updated, messages.SUCCESS)
        except:
            self.message_user(request, ngettext(
            '%d product could not be duplicated.',
            '%d products could not be duplicated.',
            updated,
        ) % updated, messages.ERROR)
            
            
    duplicate_product.short_description = "Duplicate selected products"
    
    #this is the intermediate page for export functions 
    def export_csv_selector(self, request, queryset):
        # All requests here will actually be of type POST 
        # so we will need to check for our special key 'apply' 
        # rather than the actual request type
        if 'apply' in request.POST:
            # The user clicked submit on the intermediate form.
            # Perform our update action:
            #queryset.update(status='NEW_STATUS')
            test_output = ''
            response = None
            export_format =  request.POST['export_parameter']
            if export_format == 'shop':
                response = ExportCsvMixin.export_product_shop_csv(self, request, queryset)
            elif export_format == 'excel':
                response = ExportCsvMixin.export_as_csv(self, request, queryset)
            else:
                test_output = ''
                
            # Redirect to our admin view after our update has 
            # completed with a nice little info message saying 
            # our models have been updated:
         
            downloaded = queryset.count()
            self.message_user(request, ngettext(
            'Downloaded %d product in ' + export_format + ' format.',
            'Downloaded %d products in ' + export_format + ' formate.',
            downloaded,
        ) % downloaded, messages.SUCCESS)
            return response # HttpResponseRedirect(request.get_full_path())
            #return HttpResponseRedirect(request.get_full_path())
        
        return render(request,
                      'ProductManager/admin/csv_export_selector.html',
                      context={'products':queryset})
    
    export_csv_selector.short_description = "Export CSV [experimental!]"
    
    #this function belongs to the custom 'generate fsin' button in the admin/projectmanager/change_form.html
    def response_change(self, request, obj):
        if "_generate-fsin" in request.POST:
            obj.fsin = obj.get_new_fsin()
            try:
                obj.save()
                self.message_user(request, "New FSIN was created")
            except IntegrityError:
                self.message_user(request, "Could not create FSIN [%s] because it seems to exist. Change variety, version or resolution" % obj.fsin,level=messages.ERROR)
                #return request, obj
            
            return HttpResponseRedirect(".")
        return super().response_change(request, obj)
    
    #MISSING HANDLING OF FSIN CREATION THROUGH BUTTON!
    
    #this function is not yet implemented..
    def manager_actions(self, obj):
        return format_html(
            '<a class="button" href="{}">Deposit</a>&nbsp;'
            '<a class="button" href="{}">Withdraw</a>',
            reverse('admin:account-deposit', args=[obj.pk]),
            reverse('admin:account-withdraw', args=[obj.pk]),
        )
    manager_actions.short_description = 'PM Actions'
    manager_actions.allow_tags = True
    
    # This will help you to disbale add functionality
    #def has_add_permission(self, request):
    #    return False

    # This will help you to disable delete functionaliyt
    #def has_delete_permission(self, request, obj=None):
    #    return False


    # This will help you to disable change functionality
    #def has_change_permission(self, request, obj=None):
    #    return False

   
admin.site.register(Product, ProductAdmin)


class ProductInline(admin.StackedInline):
    model=Product
    readonly_fields=['fsin']
    #this means that no empty products are shown if we edit the product base because otherwise we would have either to delete it or to fill it otherwise we can't save it
    extra=0

    
class ProductBaseForm(forms.ModelForm):
    class Meta:
        model = ProductBase
        fields = '__all__'

    def __init__(self, *args, **kwargs):
        super(ProductBaseForm, self).__init__(*args, **kwargs)
        ProductBase = kwargs.get('instance', None)
        assets_queryset = self.fields['assets'].queryset
        if 'assets' in self.initial:
            # show all client owned assets + client company assets + public assets
            # Example of generated SQL is SELECT * FROM "fo_asset" WHERE
            # ("fo_asset"."company_owner_id" IS NULL AND
            # ("fo_asset"."client_owner_id" IS NULL OR "fo_asset"."client_owner_id" = 1))
            self.fields['assets'].queryset = assets_queryset. \
                filter(
                Q(company_owner__isnull=True) & Q(client_owner__isnull=True) 
            )
        else:
            # just show assets that are not connected to a specific company or client
            self.fields['assets'].queryset = assets_queryset.filter(
                Q(client_owner__isnull=True), Q(company_owner__isnull=True)
            )
    
@admin.register(ProductBase)
class ProductBaseAdmin(admin.ModelAdmin):
    save_as = True
    readonly_fields=['fsin_base']
    list_display = ('name', 'fsin_base', 'owner', 'view_product_link')
    actions=['export_json']
    search_fields = ['name']
    list_filter = ['owner', 'mode']
    model = ProductBase
    show_change_link = True
    inlines = [ ProductInline,]
    form = ProductBaseForm
    
 
    
    
    #returns how many products are linked to this productbase
    #not finished yet
    def view_product_link(self, obj):
        count = Product.objects.filter(base=obj.pk).count()
        count_inactive = Product.objects.filter(base=obj.pk, is_active=True).count()
        #https://realpython.com/customize-django-admin-python/
        #url = (
        #    reverse("admin:core_person_changelist")
        #    + "?"
        #    + urlencode({"products__id": f"{obj.id}"})
        #)
        #return format_html('<a href="{}">{} Products</a>', url, count)
        return "%s total | %s active" % (count, count_inactive)

    view_product_link.short_description = "Products"
    
    #Missing: export product objects as well. Add more information to ASSETS than just the IDs
    def export_json(self, request, queryset):
        response = HttpResponse(content_type='text/json')
        #response['Content-Disposition'] = 'attachment; filename={}.csv'.format(meta)
        #response.write(u'\ufeff'.encode('utf8'))

        #QUOTE_ALL is needed as the shop uses this "" format
        #writer = csv.writer(response,  dialect=CSVexportSettings)
        #writer.writerow(col_names_fo)
        #XMLSerializer = serializers.get_serializer("xml")
        #xml_serializer = XMLSerializer()
        #with open("file.xml", "w") as out:
        #response = xml_serializer.serialize(queryset)
        #data = serializers.serialize("xml", queryset)
        now = datetime.datetime.now()
        filename = 'FO_ProductBase_' + now.strftime('%d%m%y_%H%M%S')
        qs_json = serializers.serialize('json', queryset)
        response = HttpResponse(qs_json, content_type='application/json')
        response['Content-Disposition'] = 'attachment; filename="' + filename + '.json"'
        return response
       
    export_json.short_description = 'Export JSON Object'

@admin.register(VideoFormat)
class LanguageAdmin(admin.ModelAdmin):
    save_as = True
    model = VideoFormat

@admin.register(Language)
class LanguageAdmin(admin.ModelAdmin):
    save_as = True
    model = Language
    
@admin.register(Resolution)
class ResolutionAdmin(admin.ModelAdmin):
    save_as = True
    model = Resolution
    
@admin.register(ProductText)
class ProductTextAdmin(admin.ModelAdmin):
    save_as = True
    list_display = ('title', 'desc_short', 'language')
    model = ProductText