import datetime
import time
from django.conf import settings
from django.db import models
from django.db.models.signals import pre_save
from django.dispatch import receiver

#rom apps.FileCollector.models import Client

#import os.path as Path
from pathlib import Path
import re
import os
# Create your models here.
from apps.ProductManager.models import Product
#from apps.FileCollector.models import ProjectManager
from django.db.models import Count, JSONField
# Register your models here.

from formikaro.utils import urlify

SHOP_FOLDER = settings.SHOP_FOLDER
SHOP_CLIENT_CI_FOLDER = settings.SHOP_CLIENT_CI_FOLDER
SHOP_DEFAULT_ASSETS_FOLDER = settings.SHOP_DEFAULT_ASSETS_FOLDER
SHOP_DEFAULT_ASSETS_GLOBAL_FOLDER = settings.SHOP_DEFAULT_ASSETS_GLOBAL_FOLDER
INTRANET_SHOP_DRIVE = settings.INTRANET_SHOP_DRIVE

#
# ASSETS
#

class AssetType(models.Model):
    title = models.CharField(max_length=30) #internally used title
    name = models.CharField(max_length=10) #internally used title
    extension = models.CharField(max_length=5, null=True, blank=True) #if it's a file this is the expected extention. filename= asset.value + assettype.extention
    property = models.CharField(max_length=50, null=True, blank=True)  # used to connect to the AE property of the layer
    layerName = models.CharField(max_length=50, null=True, blank=True)  # used to connect to the AE property of the layer (if empty the name will be used instead) asset.layerName has priority over the AssetType
    description = models.TextField(null=True, blank=True) #internal description
    is_file = models.BooleanField(default=False) # flag if we expect the asset to be a file
    maxlength = models.IntegerField(blank=True,null=True) #in case it is a value
    created = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'fo_asset_type'


    
    def __str__(self):
        # return "%s Order" % self.client
        return '%s' % self.title
    

ASSET_SOURCE_EXT_AUTO = 'EXAU'
ASSET_SOURCE_EXT_MAN = 'EXMA'
ASSET_SOURCE_INT_AUTO = 'INAU'
ASSET_SOURCE_INT_MAN = 'INMA'


#@receiver(pre_save)
#def my_callback(sender, instance, *args, **kwargs):
#    instance.property =

# this are the general asset types that are available
class Asset(models.Model):
    SOURCE = (
        (ASSET_SOURCE_EXT_AUTO, 'External auto'),
        (ASSET_SOURCE_EXT_MAN, 'External manual'),
        (ASSET_SOURCE_INT_AUTO, 'Internal auto'),
        (ASSET_SOURCE_INT_MAN, 'Internal manual'),
    )

    name = models.CharField(max_length=30) # internally used name
    value = models.CharField(max_length=1000, null=True,blank=True) # the value of this asset, this can be a file name in case assettype.is_file = True
    json =  JSONField(default=list,blank=True, null=True)
    assettype = models.ForeignKey(AssetType, on_delete=models.PROTECT)
    layerName = models.CharField(max_length=50, null=True,
                                 blank=True)  # used to connect to the AE property of the layer (if empty the name will be used instead) asset.layerName has priority over the AssetType
    property = models.CharField(max_length=50, null=True, blank=True)  # used to connect to the AE property of the layer  asset.property has priority over the AssetType
    tasks = models.ManyToManyField('FormikoBot.Task', related_name='assets', blank=True)
    source= models.CharField(max_length=15, choices=SOURCE, default='EXAU')
    maxlength = models.IntegerField(blank=True,null=True) #this will be used when assettype.maxlength is not set
    description = models.TextField(null=True, blank=True)
   
    company_owner = models.ForeignKey(
        'FileCollector.Company', on_delete=models.SET_NULL, blank=True, null=True, related_name='company_owned_assets'
    )
    client_owner = models.ForeignKey(
        'FileCollector.Client', on_delete=models.SET_NULL, blank=True, null=True, related_name='client_owned_assets'
    )
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'fo_asset'
        ordering = ['-pk']
    
    def __str__(self):
        return '{_name} - {_id}'.format(_name=self.name, _id=self.id)
    
    # checks if the asset exists on the drive for the given client
    # returns true if 1, 0 if no and 3 if it may be another file
    def exists_client(self, client):
        if not self.assettype.is_file:
            return 0
        
        asset_path = self.get_client_folder(True, client, False)
        #print("ASSETPATH: %s" % asset_path)
        if os.path.isfile(asset_path):
            retval = 1
        else:
            retval = 0
        
        return retval

    def get_maxlength(self):
        if self.maxlength:
            return self.maxlength
        else:
            if self.assettype.maxlength > 0:
                return self.assettype.maxlength
            else:
                return 0
    
    # checks if the asset exists on the drive for the given client
    # returns true if 1, 0 if no and 3 if it may be another file
    def exists_company(self, Company):
        if not self.assettype.is_file:
            return 1
            
        asset_path = self.get_company_folder(True, Company, False)
        
        if os.path.isfile(asset_path):
            retval = 1
        else:
            retval = 0
        
        return retval

    def get_extension(self):
        if self.assettype.extension:
            return self.assettype.extension
        else:
            return False

    def get_property(self):
        if self.property:
            return self.property
        else:
            return self.assettype.property

    def get_layername(self):
        #print("LAYERNAME [%s]" % self.layerName)
        #print("LAYERNAME TYPE [%s]" % self.assettype.layerName)
        if self.layerName:
            return self.layerName
        else:
            return self.assettype.layerName

    def get_client_value(self, Client=None):
        if not Client:
            return False
        #this_asset = Client.assets.get(name=self.name)[:1]
        this_asset = Client.assets.filter(name=self.name).first()
        value = this_asset.value
        return value
    
    def get_company_value(self, Company=None):
        if not Company:
            return False
        this_asset = Company.assets.filter(name=self.name).first()
        value = this_asset.value
        return value
    
     #delivers the folder in which the asset is stored if it belongs to a company
    def get_company_folder(self, absolute=False, Company=None, intra_link=False):
        if not self.assettype.is_file:
            return False
    
        if not Company:
            return False
        
        folder = ''
        
        if absolute and intra_link:
            folder = Path(INTRANET_SHOP_DRIVE) / SHOP_CLIENT_CI_FOLDER  #this is for the intra net 
        elif absolute and not intra_link:
            folder = Path(SHOP_FOLDER) / SHOP_CLIENT_CI_FOLDER 
            
        folder = folder / Company.get_folder(False) / self.get_filename()
        
        return folder
        
    
    
    #delivers the folder in which the asset is stored
    def get_client_folder(self, absolute=False, Client=None, intra_link=False):
        if not self.assettype.is_file:
            return False;

        folder = ''
        
        if absolute and intra_link:
            folder = Path(INTRANET_SHOP_DRIVE) / SHOP_CLIENT_CI_FOLDER  #this is for the intra net 
        elif absolute and not intra_link:
            folder = Path(SHOP_FOLDER) / SHOP_CLIENT_CI_FOLDER 
        
        #if it's a company owned asset not belonging to a client it goes into a subfolder
        if self.company_owner and not self.client_owner:
            folder = Path(folder) / self.company_owner.get_folder()
        elif self.client_owner:
            folder = Path(folder) / self.client_owner.get_folder()
        else:
            if Client:
                folder = Path(folder) / Client.get_folder()
        
        # if now owners are defined we assume that this is a global asset and look at the owner 
        # see if this asset is needed in the given order
        
        #if Client and not self.company_owner:
            #print("This is the client of this asset: ", OrderProduct.order.client)
        #    folder = Path(folder) / Client.get_folder(False)
            
        # we have to check is an asset is available to the company. if yes then it's in the company root 
        
        #if self in Client.company.assets.all():       
            #folder = 's'
        #if Entry.objects.filter(id=e.id).exists():
            
        #else:
            #if no orderproduct is given we assume that this is a global asset which is stored in the global assets folder
        #    folder = Path(folder) / SHOP_DEFAULT_ASSETS_GLOBAL_FOLDER
            
        folder = Path(folder) /  self.get_filename()
        
        return folder
    
    #delivers the folder in which the asset is stored
    def get_folder(self, absolute=False, OrderProduct=None):
        if not self.assettype.is_file:
            return False;

        folder = ''
        
        if absolute:
            folder = Path(SHOP_FOLDER) / SHOP_CLIENT_CI_FOLDER 
        
        #if it's a company owned asset not belonging to a client it goes into a subfolder
        if self.company_owner and not self.client_owner:
            folder = Path(folder) / self.company_owner.get_folder()
        elif self.client_owner:
            folder = Path(folder) / self.client_owner.get_folder()
        
        # if now owners are defined we assume that this is a global asset and look at the owner 
        # see if this asset is needed in the given order
        if OrderProduct:
            if OrderProduct.order.client:
                #print("This is the client of this asset: ", OrderProduct.order.client)
                #folder = OrderProduct.order.client.get_folder(True)
                folder = OrderProduct.order.client.get_folder(absolute)
        else:
            #if no orderproduct is given we assume that this is a global asset which is stored in the global assets folder
            folder = Path(folder) / SHOP_DEFAULT_ASSETS_GLOBAL_FOLDER
            
        #file_name = self.value
        #folder = Path(folder) / file_name
        return folder

    #def get_filename(self):
    #    print("THIS FILENAME: %s" % self.assettype.is_file ) #DEBUG
    #    if not self.assettype.is_file:
    #        return False
    #    filename = str(self.value + '.' + self.assettype.extension)
    #    return filename

    def get_filename(self, absolute=False, OrderProduct=None):
        if not self.assettype.is_file:
            return False;
        
        folder = self.get_folder(absolute, OrderProduct)
        
        filename = str(self.value) + '.' + str(self.assettype.extension)
        
        if absolute:
            filename = Path(folder) / filename
            
        return filename
        


class AssetPreset(Asset):
    title = models.CharField(max_length=30) #internally used title
    pres_description = models.TextField(null=True, blank=True) #internal description 
    #assettype = models.ForeignKey(AssetType, on_delete=models.PROTECT)
    pres_created = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'fo_asset_preset'
        ordering = ['title', 'name', 'value']
    
    def __str__(self):
        # return "%s Order" % self.client
        return '%s' % self.title

class TaskType(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField(null=True, blank=True)  # internal description
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'fo_tasktype'

    def __str__(self):
        return '%s' % (self.name)

TASK_STATUS_OPEN = 'OP'
TASK_STATUS_ACTIVE = 'AC'
TASK_STATUS_FAILED = 'FD'
TASK_STATUS_COMPLETE = 'CM'
TASK_STATUS_OPEN_NAME = 'OPEN'
TASK_STATUS_ACTIVE_NAME = 'ACTIVE'
TASK_STATUS_FAILED_NAME = 'FAILED'
TASK_STATUS_COMPLETE_NAME = 'COMPLETE'


class Task(models.Model):
    MODE = (
        ('MAN', 'MANUAL'),
        ('BOT', 'FormikoBot'),

    )

    STATUS = (
        (TASK_STATUS_OPEN, TASK_STATUS_OPEN_NAME),
        (TASK_STATUS_ACTIVE, TASK_STATUS_ACTIVE_NAME),
        (TASK_STATUS_FAILED, TASK_STATUS_FAILED_NAME),
        (TASK_STATUS_COMPLETE, TASK_STATUS_COMPLETE_NAME),

    )
    name= models.CharField(max_length=100)
    description = models.TextField(null=True, blank=True) #internal 
    creator = models.ForeignKey(
        'FileCollector.Projectmanager', on_delete=models.SET_NULL, blank=True, null=True, related_name='created_tasks'
    )
    user = models.ForeignKey(
        'FileCollector.Projectmanager', on_delete=models.SET_NULL, blank=True, null=True, related_name='tasks'
    )
    starttime = models.DateTimeField(blank=True, null=True) # the time the task is supposed to start
    deadline = models.DateTimeField(blank=True, null=True)  # the deadline when the task should finish
    endtime = models.DateTimeField(blank=True, null=True) #actual time the task ended - set when status = complete/failed
    runtime = models.IntegerField(blank=True,null=True)
    mode = models.CharField(max_length=8, choices=MODE, default='MAN')
    unitprice = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    status = models.CharField(max_length=8, choices=STATUS, default=TASK_STATUS_OPEN)
    priority = models.PositiveSmallIntegerField(default=0)
    type = models.ForeignKey(TaskType, on_delete=models.SET_NULL, blank=True, null=True, related_name='type_tasks')
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'fo_task'

    def __str__(self):
            # return "%s Order" % self.client
            return '%s (%s)' % (self.name, self.id)

    def get_formated_runtime(self):

        if not self.runtime:
            return '-'

        n = int(self.runtime)
        minutes = n // 60  # Truncating integer division
        seconds = n % 60  # Modulo removes the upper digits

        if minutes:
             runtime_format = ('%s mins %s secs (%s)' % (minutes, seconds, self.runtime))
        else:
            runtime_format = ('%s secs' % (seconds))
        return runtime_format

    def get_priority_val(self):
        now_date = datetime.datetime.utcnow()
        if self.starttime:
            time_diff = time.mktime(now_date.timetuple()) - time.mktime(self.starttime.timetuple())
        else:
            time_diff = 0
        
        priority_val = 'bg-light'
        if (self.priority == 0 or time_diff <= 24 * 3600) and time_diff != 0:
            priority_val = 'bg-info'
        if self.priority == 5 or (time_diff > 24 * 3600 and time_diff <= 72 * 3600):
            priority_val = 'bg-purple'
        if self.priority == 10 or time_diff > 72 * 3600:
            priority_val = 'bg-danger'
        return priority_val

class TaskPreset(Task):
    title = models.CharField(max_length=30) #internally used title
    pres_description = models.TextField(null=True, blank=True) #internal description 
    #assettype = models.ForeignKey(AssetType, on_delete=models.PROTECT)
    pres_created = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'fo_task_preset'
        ordering = ['title', 'name']
    
    def __str__(self):
        # return "%s Order" % self.client
        return '%s' % self.title
     
    
class WorkStep(models.Model):
    MODE = (
        ('MAN', 'MANUAL'),
        ('FO', 'FormikoBot'),

    )

    name= models.CharField(max_length=15)
    desc=models.CharField(max_length=100)
    json =  JSONField(default=list,blank=True, null=True)
    description = models.TextField(blank=True)
    mode = models.CharField(max_length=8, choices=MODE, default='MAN')

    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'fo_workstep'

    def __str__(self):
        # return "%s Order" % self.client
        return '%s' % self.name
    

#class WorkList(models.Model)

    


