from django.db import models
from django.db.models import Max

# Create your models here.

class Resolution(models.Model):
    width = models.IntegerField(default='1280')      
    height = models.IntegerField(default='720')  
    quality = models.IntegerField(default='2')
    name = models.CharField(max_length=25)
    description = models.TextField()
    
    class Meta:
        db_table = 'fo_resolution'
        
    def __str__(self):
        return '%s (%s x %s ),%s, [q:%s]' % (self.description, self.width, self.height, self.name, self.quality)
    
class Language(models.Model):
    abbreviation = models.CharField(max_length=10, unique=True)  
    name = models.CharField(max_length=256)
    system_language = models.BooleanField(default=None)

    class Meta:
        db_table = 'fo_language'
        
    def __str__(self):
        return '%s (%s)' % (self.abbreviation, self.name)

class ProductText(models.Model):
    language = models.ForeignKey(Language, on_delete=models.PROTECT)
    title = models.CharField(max_length=200)
    desc_short = models.TextField()
    desc_long = models.TextField()
    
    def __str__(self):
        return '%s (%s)' % (self.title, self.language)
    
    class Meta:
        db_table = 'fo_product_text'


##PRODUCT MODELS
class Product(models.Model):
    MODE = (
            ('AE', 'After Effects'),
            ('PR', 'Premiere'),
            ('FO', 'FormikoBot'),
            )
   
    fsin = models.CharField(max_length=30, unique=True, null=True, blank=True)
    is_active = models.BooleanField(default=False)
    price = models.IntegerField(default='0')
    product_name = models.CharField(max_length=60)
    product_mode = models.CharField(max_length=8, choices=MODE, default='AE')
    product_type = models.CharField(max_length=6, default='')
    product_version = models.IntegerField(default='1')  
    comment = models.TextField()
    preview = models.CharField(max_length=200)
    language = models.ForeignKey(Language, on_delete=models.PROTECT)
    resolution = models.ForeignKey(Resolution, on_delete=models.PROTECT)
    product_text = models.ForeignKey(ProductText, on_delete=models.PROTECT)
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)
 
    class Meta:
        db_table = 'fo_product'

    def rem_vowel(self, string): 
        vowels = ('a', 'e', 'i', 'o', 'u')  
        for x in string.lower(): 
            if x in vowels: 
                string = string.replace(x, "") 
        return string
    

    #this will generate a completely new FSIN for the product by
    #first calling generate_fsin and then check if the fsin already exists, if yes get the highest possible new version of it
    def get_new_fsin(self):
        newFsin = self.generate_fsin()
        
        #check if the proposed new FSIN already exists
        if Product.objects.filter(fsin=newFsin).exists():
            highestVersion = Product.objects.filter(fsin=newFsin).aggregate(Max('product_version'))
            highestVersion = highestVersion['product_version__max']+1
            newFsin=self.generate_fsin(highestVersion)
            #we also have to increment this products version as
            #it's now increased and we are going to save it
            self.product_version = highestVersion

        return newFsin

    #this function generates a new standardizes FSIN for the product
    #based on the products properties. In case the version parameter is
    #given a FSIN incorporating this version will be created
    def generate_fsin(self, version=0):
        token_1 = self.product_name.replace(" ", "")
        #shorten the product name to meet the 8-digit requirement
        if len(token_1) > 8:
            #remove vowels to make it shorter
            token_1 = self.rem_vowel(token_1)
            token_1 = token_1[:8]
            
        #if no version parameter has been given this means we need a new 
        #FSIN with a higher version number
        if version == 0:
            version = self.product_version

        newFsin = token_1 + str(self.product_type) + str(version) + self.resolution.name
        newFsin = newFsin.upper()
        
        return newFsin
    
    #this overrides the save function for this object because we want
    #to make sure a product is given the right FSIN (SKU) number 
    def save(self, *args, **kwargs):
        #if not self.fsin:
        #    self.fsin = self.get_new_fsin()
        super().save(*args, **kwargs)
    
    def __str__(self):
        return self.product_name
        #return '%s (%s) B:%s' % (newFsin, self.fsin, Product.objects.filter(fsin=newFsin).exists())
        #highestVersion = Product.objects.filter(fsin=self.fsin).aggregate(Max('product_version'))
        #highestVersion = highestVersion['product_version__max']+1
        #newFsin=self.generate_fsin(highestVersion)
        #return "%s v: %s high: %s F: %s " % (self.product_name, self.product_version, highestVersion, self.fsin)
       

    
    