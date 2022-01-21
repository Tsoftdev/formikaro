#Here are general functions that are used in the different Formikaro apps

from django.http import HttpResponse
from django.db.models import Count, Sum, Q
#from apps.ProductManager.models import ProductTextModel
import csv
import re

col_names_fo = ['BaseName',
             'FSINBASE',
             'FSIN',
             'VARIETY',
             'VERSION',
             'LANGUAGE',
             'RUNTIME',
             'PRICE',
             'RESOLUTION',
             'WIDTH',
             'HEIGHT',
             'ACTIVE',
             'VIMEO_ID',
             'COMMENT',
             'CHANGE_LOG',
             'TITLE (DE)',
             'SHORT DESC (DE)',
             'LONG DESC (DE)',
             'TITLE (EN)',
             'SHORT DESC (EN)',
             'LONG DESC (EN)',
             
               ]

SHOP_TRUE_VALUE = 'True'
SHOP_FALSE_VALUE = 'False'
                
                
col_names_shop = ['Name',
             'Short Description',
             'Long Description',
             'SKU',
             'GTIN',
             'Visibility',
             'Active',
             'Review',
             'Price',
             'SpecialPrice',
             'Product Cost',
             'Disable Buy Button',
             'Call For Price',
             'Tax Exempt',
             'Tax Categories',
             'Meta Title',
             'Meta Keywords',
             'Meta Description',
             'Images',
             'Manage Inventory',
             'Minimum Order Quantity',
             'Maximum Order Quantity',
             'In Stock Quantity',
             'Out Stock Quantity',
             'Low Stock Quantity',
             'Show Stock Availability',
             'Show Stock Quantity',
             'Stock Availability',
             'Selected Categories',
             'Shipping',
             'Free Shipping',
             'Additional Shipping Charge',
             'Weight',
             'Length',
             'Width',
             'Height',
             'Digital Download',
             'Variation',
             'Manufacturer',
             'Rating',
             'Attributes',
             'Slug',
             'IsFeatured',
             'NewStartDate',
             'NewEndDate',
             'GroupAndTier',
             'Display Order',
             
            ]


# this needs to go on one global place as this is a vital function for the
# localization of all files+assets!
# it also needs to be changed to disallow excentic letters íìáà...
def urlify(s):
    # Remove all non-word characters (everything except numbers and letters)
    s = re.sub(r"[^\w\s]", '', s)
    #s = re.sub(r"[^a-zA-Z0-9 -_]", '', s)

    # Replace all runs of whitespace with a single dash
    s = re.sub(r"\s+", '-', s)

    return s



#general export settings
class CSVexportSettings(csv.Dialect):
    delimiter = ';' # delimiter should be only 1-char
    quotechar = '"'
    escapechar = None
    doublequote = True
    skipinitialspace = False
    lineterminator = '\r\n'
    quoting = 1
    
#shop export settings
class CSVexportSettings_shop(csv.Dialect):
    delimiter = ',' # delimiter should be only 1-char
    quotechar = '"'
    escapechar = None
    doublequote = True
    skipinitialspace = False
    lineterminator = '\r\n'
    quoting = 1

class ExportCsvMixin:
    
    #general CSV export for any model
    def export_as_csv(self, request, queryset):
        meta = self.model._meta
        field_names = [field.name for field in meta.fields]

        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename={}.csv'.format(meta)
        response.write(u'\ufeff'.encode('utf8'))
        writer = csv.writer(response, dialect=CSVexportSettings)
        
        writer.writerow(field_names)
        for obj in queryset:
            row = writer.writerow([getattr(obj, field) for field in field_names])
            return response

    export_as_csv.short_description = "Export Selected as CSV"

    #for this we expect a PRODUCT Queryset in FORMIKARO FORMAT
    def export_product_fo_csv(self, request, queryset):
            meta = self.model._meta
            field_names = [field.name for field in meta.fields]

            response = HttpResponse(content_type='text/csv')
            response['Content-Disposition'] = 'attachment; filename={}.csv'.format(meta)
            response.write(u'\ufeff'.encode('utf8'))

            #QUOTE_ALL is needed as the shop uses this "" format
            writer = csv.writer(response,  dialect=CSVexportSettings)
            writer.writerow(col_names_fo)
           
            for obj in queryset:
                row=[]
                #the following code hard defines GERMAN and ENGLISH texts into the downloads
                #this will suffice for this stage
                #get GERMAN texts
                try:
                    producttext = ProductText.objects.get(Q(product=obj.id) & Q(language=2))
                    desc_short_de = producttext.desc_short
                    desc_long_de = producttext.desc_long
                    title_de = producttext.title
                except:
                    title_de = ''
                    desc_long_de = ''
                    desc_short_de = ''
                
                #get ENGLISH texts
                try:
                    producttext = ProductText.objects.get(Q(product=obj.id) & Q(language=1))
                    desc_short_en = producttext.desc_short
                    desc_long_en = producttext.desc_long
                    title_en = producttext.title
                except:
                    title_en = ''
                    desc_long_en = ''
                    desc_short_en = ''
                
                row.append(obj.base.name)                   #Name
                row.append(obj.base.fsin_base)              #FSIN_BASE
                row.append(obj.fsin)                        #FSIN
                row.append(obj.variety)                     #variety
                row.append(obj.version)                     #version
                row.append(obj.language)                    #language
                row.append(obj.runtime)                     #runtime
                row.append(obj.price)                       #Price
                row.append(obj.resolution.name)             #Resolution Name
                row.append(obj.resolution.width)            #Width
                row.append(obj.resolution.height)           #Height
                row.append(obj.is_active)                   #is_active
                row.append(obj.vimeo_id)                    #vimeo_id
                row.append(obj.comment)                     #comment
                row.append(obj.change_log)                  #change_log
                row.append(title_de)
                row.append(desc_short_de)                   #Short Description GERMAN
                row.append(desc_long_de)                    #Long Description GERMAN
                row.append(title_en)
                row.append(desc_short_en)                   #Short Description ENGLISH
                row.append(desc_long_en)                    #Long Description ENGLISH
                 
                writer.writerow(row)

            
                #row = writer.writerow([getattr(obj, field) for field in field_names])
            return response

    export_product_fo_csv.short_description = "Export Selected as CSV (Formikaro-Format)"
    
    #for this we expect a PRODUCT Queryset
    def export_product_shop_csv(self, request, queryset):
            meta = self.model._meta
            field_names = [field.name for field in meta.fields]

            response = HttpResponse(content_type='text/csv')
            response['Content-Disposition'] = 'attachment; filename={}.csv'.format(meta)
            response.write(u'\ufeff'.encode('utf8'))

            #QUOTE_ALL is needed as the shop uses this "" format
            writer = csv.writer(response,  dialect=CSVexportSettings_shop)
            writer.writerow(col_names_shop)
           
            for obj in queryset:
                row=[]
                try:
                    producttext = ProductText.objects.get(Q(product=obj.id) & Q(language=1))
                    desc_short = producttext.desc_short
                    desc_long = producttext.desc_long
                except:
                    desc_long = ''
                    desc_short = ''
                    
                price = str(obj.price).replace(',','.') 
                
                row.append(obj.base.name)                   #Name
                row.append(desc_short)                    #Short Description
                row.append(desc_long)                     #Long Description
                row.append(obj.fsin)                        #SKU/FSIN
                row.append('')                              #GTIN
                row.append('SearchAndCatalog')              #Visibility
                row.append(SHOP_TRUE_VALUE)                          #Active
                row.append(SHOP_FALSE_VALUE)                         #Review
                row.append(price)                       #Price
                row.append('')                              #SpecialPrice
                row.append('')                              #Product Cost
                row.append(SHOP_FALSE_VALUE)                         #Disable Buy Button
                row.append(SHOP_FALSE_VALUE)                         #Call For Price
                row.append(SHOP_FALSE_VALUE)                         #Tax Exempt
                row.append('20% Austria')                   #Tax Categories
                row.append('')                              #Meta Title
                row.append('')                              #Meta Keywords
                row.append('')                              #Meta Description
                row.append('')                              #Images
                row.append('None')                          #Manage Inventory
                row.append('0')                             #Minimum Order Quantity
                row.append('1')                             #Maximum Order Quantity
                row.append('')                              #In Stock Quantity
                row.append('')                              #Out Stock Quantit
                row.append('')                         #Low Stock Quantity
                row.append(SHOP_FALSE_VALUE)                         #Show Stock Availability
                row.append(SHOP_FALSE_VALUE)                         #Show Stock Quantity
                row.append('InStock')                    #Stock Availability
                row.append('')                              #Selected Categories
                row.append(SHOP_FALSE_VALUE)                         #Shipping
                row.append(SHOP_FALSE_VALUE)                         #Free Shipping
                row.append('0')                             #Additional Shipping Charge
                row.append('0')                             #Weight
                row.append('0')                             #Length
                row.append(obj.resolution.width)            #Width
                row.append(obj.resolution.height)           #Height
                row.append(SHOP_FALSE_VALUE)                         #Digital Download
                row.append('')                              #Variation
                row.append('FSP')                           #Manufacture
                row.append(SHOP_FALSE_VALUE)                         #Rating
                row.append('')                              #Attributes
                row.append('test-product')                  #Slug
                row.append(SHOP_FALSE_VALUE)                         #IsFeatured
                row.append('')                              #NewStartDat
                row.append('')                              #NewEndDate
                row.append('')                            #GroupAndTier
                row.append('0')                             #Display Order
                 
                writer.writerow(row)

            
                #row = writer.writerow([getattr(obj, field) for field in field_names])
            return response

    export_product_shop_csv.short_description = "Export Selected as CSV (Shop-Format)"