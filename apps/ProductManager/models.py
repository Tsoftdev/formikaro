from django.conf import settings
from django.db import models
from django.db.models import Max
from pathlib import Path
from datetime import datetime
from thumbnails.fields import ImageField
import os
from PIL import Image
import math
from io import BytesIO
from django.core.files import File
import uuid

# here are some custom functions
from django.urls import reverse
#from apps.FormikoBot.models import Asset    
import re

from formikaro.settings.storage_backends import FormikaroS3Storage
from formikaro.utils import urlify

SHOP_FOLDER = settings.SHOP_FOLDER
SHOP_SHELF_FOLDER = settings.SHOP_SHELF_FOLDER

def rem_vowel(string):
    vowels = ('a', 'e', 'i', 'o', 'u')
    for x in string.lower():
        if x in vowels:
            string = string.replace(x, "")
    return string


# RESOLUTION
class Resolution(models.Model):
    width = models.IntegerField(default='1280')
    height = models.IntegerField(default='720')
    quality = models.IntegerField(default='2')
    name = models.CharField(max_length=25)
    description = models.TextField()

    class Meta:
        db_table = 'fo_resolution'

    def __str__(self):
        # return '%s (%s x %s ),%s, [q:%s]' % (self.description, self.width, self.height, self.name, self.quality)
        # return '%s (%s x %s)' % (self.description, self.width, self.height)
        return self.name


# LANGUAGE
class Language(models.Model):
    abbreviation = models.CharField(max_length=10, unique=True)
    name = models.CharField(max_length=256)
    system_language = models.BooleanField(default=False)

    class Meta:
        db_table = 'fo_language'
        ordering = ['name']

    def __str__(self):
        # return '%s (%s)' % (self.abbreviation, self.name)
        return self.abbreviation


# VIDEO FORMAT

class VideoFormat(models.Model):
    name = models.CharField(max_length=25)
    resolution = models.ForeignKey(Resolution, on_delete=models.SET_NULL, blank=True, null=True, related_name="videoformats")
    description = models.TextField(blank=True, null=True)

    class Meta:
        db_table = 'fo_videoformat'

    def __str__(self):
        # return '%s (%s x %s ),%s, [q:%s]' % (self.description, self.width, self.height, self.name, self.quality)
        # return '%s (%s x %s)' % (self.description, self.width, self.height)
        return self.name



# PRODUCT/BASE

class AbstractBaseModel(models.Model):
    # Model with extra common properties
    def get_admin_url(self):
        """the url to the Django admin interface for the model instance useful for linking from the Frontend"""
        return reverse('admin:{0}_{1}_change'.format(self._meta.app_label, self._meta.model_name), args=(self.pk,))

    class Meta:
        abstract = True


AE_STATUS_VALUE = 'AE'
AE_STATUS_TEXT = 'After Effects'
PR_STATUS_VALUE = 'PR'
PR_STATUS_TEXT = 'Premiere'
FO_STATUS_VALUE = 'FO'
FO_STATUS_TEXT = 'FormikoBot'


class ProductBase(AbstractBaseModel):
    MODE = (
        (AE_STATUS_VALUE, AE_STATUS_TEXT),
        (PR_STATUS_VALUE, PR_STATUS_TEXT),
        (FO_STATUS_VALUE, FO_STATUS_TEXT),
    )
    fsin_base = models.CharField(max_length=10, unique=True, null=True, blank=True)
    mode = models.CharField(max_length=8, choices=MODE, default='AE')
    name = models.CharField(max_length=30)
    owner = models.ForeignKey('FileCollector.ProjectManager', on_delete=models.SET_NULL, blank=True, null=True)
    needs_intake = models.BooleanField(default=False) #if the products of this base need an intake(=client files) to be rendered
    #assets needed to generate this product
    assets = models.ManyToManyField('FormikoBot.Asset', related_name='product_assets', blank=True)
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'fo_product_base'
        
    def generate_fsin_base(self):
        new_fsin = self.name.replace(" ", "")
        
        #shorten the product name to meet the 8-digit requirement
        if len(new_fsin) > 8:
            #remove vowels to make it shorter
            new_fsin = rem_vowel(new_fsin)
            new_fsin = new_fsin[:8]
            
        new_fsin = new_fsin + self.mode
        self.fsin_base=new_fsin.upper()
        return self.fsin_base
    
    def get_folder(self, absolute=False):
        folder = str(self.id) + '_' + self.fsin_base
        if absolute:
            folder = Path(SHOP_FOLDER) / SHOP_SHELF_FOLDER / folder

        return Path(folder)

    #this overrides the save function for this object because we want
    #to make sure a product is given the right FSIN (SKU) number 
    def save(self, *args, **kwargs):
        if not self.fsin_base:
            self.fsin_base = self.generate_fsin_base()
        
        super().save(*args, **kwargs)

    def __str__(self):
        return '%s' % (self.fsin_base)


# PRODUCT MODELS
class Product(AbstractBaseModel):
    base = models.ForeignKey(ProductBase, on_delete=models.PROTECT)
    fsin = models.CharField(max_length=30, unique=True, null=True, blank=True)
    is_active = models.BooleanField(default=False)
    price = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    variety = models.CharField(max_length=4, default='', blank=True)
    version = models.IntegerField(default='1')
    comment = models.TextField(blank=True)
    vimeo_id = models.CharField(max_length=10, blank=True)
    language = models.ForeignKey(Language, on_delete=models.PROTECT)
    resolution = models.ForeignKey(Resolution, on_delete=models.PROTECT) #, blank=True)
    runtime = models.IntegerField(default='0') # in seconds
    rendertime = models.IntegerField(default='0')
    change_log = models.TextField(blank=True)
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'fo_product'

    #returns a simple link
    def get_vimeo_link(self, text=''):
        if not self.vimeo_id:
            return False
        if not text:
            text = self.base.name 
            
        vimeo_link = f'<a href="https://vimeo.com/%s">%s</a>' % (self.vimeo_id, text)
    
        return vimeo_link
        
        
    #this will generate a completely new FSIN for the product by
    #first calling generate_fsin and then check if the fsin already exists, if yes get the highest possible new version of it
    def get_new_fsin(self):
        newFsin = self.generate_fsin()
        
        #check if the proposed new FSIN already exists
        if Product.objects.filter(fsin=newFsin).exists():
            highestVersion = Product.objects.filter(fsin=newFsin).aggregate(Max('version'))
            highestVersion = highestVersion['version__max']+1
            newFsin=self.generate_fsin(highestVersion)
            #we also have to increment this products version as
            #it's now increased and we are going to save it
            self.product_version = highestVersion
        self.fsin = newFsin
        try:
            self.save()
        except:
            return False
        
        return newFsin

    #this function generates a new standardizes FSIN for the product
    #based on the products properties. In case the version parameter is
    #given a FSIN incorporating this version will be created
    def generate_fsin(self, version=0):
        #token_1 = self.product_name.replace(" ", "")
        #shorten the product name to meet the 8-digit requirement
        #if len(token_1) > 8:
            #remove vowels to make it shorter
        #    token_1 = self.rem_vowel(token_1)
        #    token_1 = token_1[:8]
        if not self.base.fsin_base:
            return False
        
        token_1=self.base.fsin_base#ProductBase.objects.get(id=self.base)
        
        #if no version parameter has been given this means we need a new 
        #FSIN with a higher version number
        if version == 0:
            version = self.version
        else:
            self.version = version

        newFsin = token_1 + str(version) + str(self.language) + str(self.variety) + self.resolution.name
        newFsin = newFsin.upper()
        
        return newFsin
    
    #gets the file name of the effective file in which the product is stored on the drive
    def get_project_file_name(self, get_extention=False):
        extention = ''
        if get_extention:
            if self.base.mode == AE_STATUS_VALUE:
                extention = '.aep'
            elif self.base.mode == PR_STATUS_VALUE:
                extention = '.prproj'
            elif self.base.mode == FO_STATUS_VALUE:
                extention = '.FO'
            
        filename = self.fsin + extention
        return filename
    
    # log function for internal monitoring
    def write_log(self, message=''):
        if not message:
            message = 'called but message missing'
        self.change_log += '[%s] %s\n' % (datetime.now(), message)
        self.save()
        return True
    
    #gets the name of the product folder under which it is stored on the drive
    def get_folder(self, absolute=True):
        folder = str(self.language) + str(self.variety) + str(self.version)
        folder = folder.upper()
        folder = Path(self.base.get_folder(absolute)) / folder
        return folder
    
    # check all the fields that could possible set in an ambigious state by the user
    def clean(self):
        print(">CLEAN UP")
        if len(self.variety) > 4:
            self.variety = self.variety[4]
            
    # this checks if the product actually exists and returns True if so  
    def check_online(self):
        if os.path.isdir(self.get_folder()):
            self.is_active = True
            self.save()
            return True
        else:
            self.is_active = False
            self.save()
            return False

    # this overrides the save function for this object because we want
    # to make sure a product is given the right FSIN (SKU) number
    def save(self, *args, **kwargs):
        # if not self.fsin:
        #    self.fsin = self.get_new_fsin()
        super().save(*args, **kwargs)

    def __str__(self):
        # return '%s [%s]' % (self.base.name, self.fsin)
        title = 'Product ' + str(self.id)
        return '%s [%s]' % (title, self.fsin)
        # return '%s (%s) B:%s' % (newFsin, self.fsin, Product.objects.filter(fsin=newFsin).exists())
        # highestVersion = Product.objects.filter(fsin=self.fsin).aggregate(Max('product_version'))
        # highestVersion = highestVersion['product_version__max']+1
        # newFsin=self.generate_fsin(highestVersion)
        # return "%s v: %s high: %s F: %s " % (self.product_name, self.product_version, highestVersion, self.fsin)


class BaseTranslationTextModel(AbstractBaseModel):
    language = models.ForeignKey(Language, on_delete=models.PROTECT)
    title = models.CharField(max_length=200)
    desc_short = models.TextField(blank=True)
    desc_long = models.TextField(blank=True)
    default = models.BooleanField(default=False, blank=True)

    class Meta:
        abstract = True

    def __str__(self):
        return '%s (%s)' % (self.title, self.language)


class ProductText(BaseTranslationTextModel):
    product = models.ForeignKey('ProductManager.Product', on_delete=models.CASCADE, related_name='product_texts')

    class Meta:
        db_table = 'fo_product_text'

image_types = {
    "jpg": "JPEG",
    "jpeg": "JPEG",
    "png": "PNG",
    "gif": "GIF",
    "tif": "TIFF",
    "tiff": "TIFF",
}

class ProductImage(models.Model):
    product = models.ForeignKey('ProductManager.Product', on_delete=models.CASCADE, related_name='product_images')
    display_order = models.PositiveSmallIntegerField(
       help_text="Order of display value e.g. 1, the lowest ranked image will be displayed first"
    )
    image = ImageField(storage=FormikaroS3Storage(), pregenerated_sizes=["small", "large", "medium"], )
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'fo_product_image'
        ordering = ['display_order']

    def __str__(self):
        return f"{self.product.base.name} product image"

    def delete(self, using=None, keep_parents=False):
        if self.image:
            self.image.delete(with_thumbnails=True)
        return super().delete(using, keep_parents)

    def save(self, *args, **kwargs):
        if self.image:
            picture = Image.open(self.image)
            (w, h) = picture.size
            ratio = 9/16
            if h/w >= 1:
                resize_image = picture.resize((int(math.floor(w)), int(math.floor(w*ratio))),Image.ANTIALIAS)
            else:
                resize_image = picture.resize((int(math.floor(h/ratio)), int(math.floor(h))))
            
            img_suffix = Path(self.image.file.name).name.split(".")[-1]
            img_filename = uuid.uuid4().hex + "." + img_suffix.lower()
            img_format = image_types[img_suffix.lower()]
            buffer = BytesIO()
            resize_image.save(buffer, format=img_format)
            buffer.seek(0)
            file_object = File(buffer)
            self.image.save(img_filename, file_object, save=False)
        
        super().save(*args, **kwargs)
       
class ProductImageText(BaseTranslationTextModel):
    product_image = models.ForeignKey(
        'ProductManager.ProductImage', on_delete=models.CASCADE, related_name='product_image_texts'
    )

    class Meta:
        db_table = 'fo_product_image_text'
