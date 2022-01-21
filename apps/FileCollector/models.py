# Formikaro.Collector.Models
# Module 1
#
from django.conf import settings
from django.contrib.auth.models import User
from django.db import models
from django.db.models import Count, JSONField
from django.db.models.signals import post_save, pre_save, pre_save
from django.dispatch import receiver
from django.db.models import Max
from django.core.exceptions import ObjectDoesNotExist

from apps.FormikoBot.models import Asset
from apps.ProductManager.models import Product
from apps.ProductManager.models import Language, Resolution
from formikaro.utils import urlify

from notifications.signals import notify

from datetime import timedelta
from decouple import config
from pathlib import Path
from datetime import datetime
import re
import os
import fnmatch
import shutil

import logging

logger = logging.getLogger('formikaro.filecollector')

##this should be in signals.py
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.http import HttpResponse

#from .models import Company

###end signals.py
BOT_LASTNAME = settings.BOT_LASTNAME
BOT_PALOMA_USERNAME=settings.BOT_PALOMA_USERNAME


INTAKE_FOLDER = settings.INTAKE_FOLDER  # '/home/worker/Projects/mount/intake'
INTAKE_FOLDER_UNASSIGNED = settings.INTAKE_FOLDER_UNASSIGNED
INTAKE_FOLDER_ORDER = settings.INTAKE_FOLDER_ORDER

SHOP_FOLDER = settings.SHOP_FOLDER
SHOP_ORDER_FOLDER = settings.SHOP_ORDER_FOLDER
SHOP_ORDER_RENDER_FOLDER = settings.SHOP_ORDER_RENDER_FOLDER

SHOP_CLIENT_CI_FOLDER = settings.SHOP_CLIENT_CI_FOLDER

PROJECT_FOLDER = settings.PROJECT_FOLDER
# MODELS


# PERSON/CLIENT MODELS

GENDER_FEMALE = 'female'
GENDER_MALE = 'male'
GENDER_UNDEFINED = 'undefined'

class Person(models.Model):
    GENDER = (
        (GENDER_FEMALE, GENDER_FEMALE),
        (GENDER_MALE, GENDER_MALE),
        (GENDER_UNDEFINED, GENDER_UNDEFINED),
    )
    firstname = models.CharField(max_length=50, blank=True)
    lastname = models.CharField(max_length=50, blank=True)
    gender = models.CharField(max_length=15, choices=GENDER, default=GENDER_UNDEFINED)
    email = models.EmailField(max_length=255, blank=True)
    phone_number = models.CharField(max_length=255, blank=True)
    default_vimeo_passwd = models.CharField(max_length=100, default="pwd")
    is_bot = models.BooleanField(default=False)
    description = models.TextField(blank=True)
    created = models.DateField(auto_now_add=True)
    updated = models.DateField(auto_now=True)

    def get_full_name(self):
        """
        Return the first_name plus the last_name, with a space in between.
        """
        full_name = '%s %s' % (self.firstname, self.lastname)
        return full_name.strip() if full_name.strip() else self.email

    class Meta:
        abstract = True
        db_table = 'fo_person'  # added


# a UserRole is a position a user holds (ie dop, camera operator, ...)
class UserRole(models.Model):
    name = models.CharField(max_length=50)
    description = models.TextField(blank=True)
    created = models.DateField(auto_now_add=True)
    updated = models.DateField(auto_now=True)

    class Meta:
        db_table = 'fo_userrole'  # added

    def __str__(self):
        return '%s' % (self.name)

class ProjectManager(Person):
    user = models.OneToOneField(User, on_delete=models.CASCADE,  related_name='projectmanager')
    is_manager = models.BooleanField(default=False)

    def get_initials(self):
        xs = (self.get_full_name())
        name_list = xs.split()

        initials = ""

        for name in name_list:  # go through each name
            initials += name[0].upper()  # append the initial

        return initials

    def __str__(self):
        return '%s %s' % (self.firstname, self.lastname)


@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        if instance.last_name == BOT_LASTNAME:
            is_bot = True
        else:
            is_bot = False
        if instance.first_name != '' and instance.last_name != '':
            ProjectManager.objects.create(user=instance, firstname=instance.first_name, lastname=instance.last_name, is_bot=is_bot)


#this can cause problems with the loaddata script
# it's purpose is to synch user and projectmanager data
@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    if instance.projectmanager:
       if instance.first_name != '':
           instance.projectmanager.firstname = instance.first_name
       if instance.last_name != '':
           instance.projectmanager.lastname = instance.last_name
       instance.projectmanager.email = instance.email
       instance.projectmanager.save()



#
# COMPANY
#

class Company(models.Model):
    name = models.CharField(max_length=256, unique=True)
    street = models.CharField(max_length=256, blank=True)
    zip_code = models.CharField(max_length=256, blank=True)
    place = models.CharField(max_length=256, blank=True)
    country = models.CharField(max_length=256, blank=True)
    website = models.TextField(blank=True)
    abbreviation = models.CharField(max_length=5, blank=True)
    phone_number = models.CharField(max_length=255, blank=True)
    email = models.EmailField(blank=True)
    description = models.TextField(blank=True)
    vat_number = models.CharField(max_length=15, blank=True)
    assets = models.ManyToManyField(Asset, related_name='company_assets', blank=True)
    language = models.ForeignKey(Language, on_delete=models.SET_NULL, blank=True, null=True)
    created = models.DateField(auto_now_add=True)
    updated = models.DateField(auto_now=True)

    class Meta:
        db_table = 'fo_company'
        verbose_name_plural = 'Companies'
        
    def get_name(self):
        name = urlify(self.name)
        return name
        
    # this needs to be an extra function if you are looking for just the rightly formated id in order to search 
    # the folder
    def _get_folder_id(self, idOnly=False):
        if idOnly:
            folder = urlify("{0:0=4d}".format(self.id))
        else:
            folder = urlify("{0:0=4d}".format(self.id) + ' ' + str(self.name))
        return folder
    
    def get_real_folder(self, absolute=False):
        folder = ''
        company_pattern = '*' + self._get_folder_id(True) + '*'
        d = Path(SHOP_FOLDER) / SHOP_CLIENT_CI_FOLDER
        
        if not os.path.isdir(d):
            return ''
        
        dir_list = [os.path.join(d, o) for o in os.listdir(d) 
                                            if os.path.isdir(os.path.join(d,o))]
        #print("\tAvailable directories:\t\t%s" % dir_list)
        
        logger.debug('\tLooking for:\t\t\t%s' % company_pattern)
        #x =  dir_list.index(client_id_formatted + '*')
        match = fnmatch.filter(dir_list, company_pattern)
        if match:
            logger.debug('[CHECK]\tCompany sub folder found!\t\t%s' % (match))
            
            if  len(match) > 1:
                logger.error('[ERROR]More than one folder with the same id (%s) found!' % self.id)
                
            folder = match[0]
            
            logger.debug('\t\t\t\t\t%s' % folder)
        else:
            
            logger.error('[ERROR] Company folder doesn\'t exist! [%s]' % folder)
            folder = ''
        
        if absolute and folder:
            folder = d / folder
            
        return folder
    
    # returns the name of the company in the client ci folder on the drive
    def get_folder(self, absolute=False):
        folder = self._get_folder_id()
        
        if absolute:
            company_folder = Path(SHOP_FOLDER) / SHOP_CLIENT_CI_FOLDER 
        else:
            company_folder = ''
        
        folder = str(Path(company_folder) / folder)
        
        return folder

    def __str__(self):
        return self.name

#
# CREW
#

class Crew(models.Model):
    person = models.ForeignKey(ProjectManager, on_delete=models.SET_NULL, null=True, related_name='crew_person')
    role = models.ForeignKey(UserRole, on_delete=models.SET_NULL, blank=True, null=True)
    remark = models.CharField(max_length=150, blank=True)
    class Meta:
        db_table = 'fo_crew'
        
#
# CLIENT
#
class Client(Person):
    abbreviation = models.CharField(max_length=5, blank=True)
    company = models.ForeignKey(Company, on_delete=models.SET_NULL, null=True, related_name='company_clients')
    language = models.ForeignKey(Language, on_delete=models.SET_NULL, blank=True, null=True)
    assets = models.ManyToManyField(Asset, blank=True, related_name='client_assets')
    shop_customer_id = models.IntegerField(blank=True, null=True)
    shop_username = models.CharField(max_length=255, blank=True)

    class Meta:
        db_table = 'fo_client'
    
    def get_fullname(self):
        full_name = self.firstname + ' ' + str(self.lastname).upper()
        return full_name
    # this is used for output and inofficial file nameng
    def get_name(self, url=True):
        if url:
            full_name = urlify(self.firstname + ' ' + str(self.lastname).upper())
        else:
            full_name = self.firstname + ' ' + str(self.lastname).upper()
        return full_name

    # this needs to be an extra function if you are looking for just the rightly formated id in order to search 
    # the folder
    def _get_folder_id(self, idOnly=False):
        if idOnly:
            folder = urlify("{0:0=4d}".format(self.id))
        else:
            folder = client_sub_folder = urlify("{0:0=4d}".format(self.id) + '_' + str(self.firstname) + ' ' + str(self.lastname).upper())
        return folder    
    
    # this function looks up if the proposed folder exists and if not searches for the folder matching the ID in the 0000 format.
    # it works recursifly also checking the get_real_folder function of the company it pertains
    def get_real_folder(self, absolute=False):
        client_pattern = '*' + self._get_folder_id(True) + '*'
        #d = Path(SHOP_FOLDER) / SHOP_CLIENT_CI_FOLDER / self.get_real_folder
        d = self.company.get_real_folder(True)
        
        if not os.path.isdir(d):
            return ''
        
        dir_list = [os.path.join(d, o) for o in os.listdir(d) 
                                            if os.path.isdir(os.path.join(d,o))]
        #print("\tAvailable directories:\t\t%s" % dir_list)
        #print("\tLooking for:\t\t\t%s" % client_pattern )
        #x =  dir_list.index(client_id_formatted + '*')
        match = fnmatch.filter(dir_list, client_pattern)
        if match:
            logger.debug('[CHECK]\tClient sub folder found!\t\t%s (%s)' % (match, len(match)))
            if  len(match) > 1:
                logger.error('[ERROR]\t More than one client folder with the same id found!')
                
            folder = match[0]
            logger.debug('\t\t\t\t\t%s' % folder)
        else:
            logger.error('Client sub doesn\'t exit :/')
            folder = ''
        
        if absolute and folder:
            folder = d / folder
            
        return folder
    
    # returns the name of the client ci folder on the drive
    def get_folder(self, absolute=False):
        #folder = "{0:0=4d}".format(self.id) + '_' + str(self.company.name)
        
        client_sub_folder = self._get_folder_id() #urlify("{0:0=4d}".format(self.id) + '_' + str(self.firstname) + ' ' + str(self.lastname).upper())
        
        company_sub_folder = self.company.get_folder()
        
        if absolute:
            client_folder = Path(SHOP_FOLDER) / SHOP_CLIENT_CI_FOLDER 
        else:
            client_folder = ''
        
        folder = Path(client_folder) / company_sub_folder / client_sub_folder
        
        return folder

    def __str__(self):
        return "%s %s" % (self.firstname, self.lastname)


ORDER_PENDING_STATUS = 'PENDING'
ORDER_ACTIVE_STATUS = 'ACTIVE'
ORDER_READY_STATUS = 'READY'
ORDER_FAILED_STATUS = 'FAILED'
ORDER_COMPLETE_STATUS = 'COMPLETE'
ORDER_DELIVERED_STATUS = 'DELIVERED'

ORDER_ORIGIN_FSP_CODE = 'FSP'
ORDER_ORIGIN_FSP_CODE_TEXT = 'SHOP'
ORDER_ORIGIN_MANUAL_CODE = 'MAN'
ORDER_ORIGIN_MANUAL_CODE_TEXT = 'MANUAL'


# ORDER MODELS

#this folder index is used by the orders to circumvent the django auto increment issue when
# the api tries to create new orders but fail. django then increments the id even though no
# entry has been made. the FolderIndex is only incremented when an Order object has been saved to 
# the database. and because the fid is used for folder naming it is essential to keep it under 
# strict control 
class FolderIndex(models.Model):
    fid = models.IntegerField(blank=True, null=True)
    
    def get_next_fid(self):
        #new_fid = FolderIndex()
        max_fid = FolderIndex.objects.aggregate(Max('fid'))
        if max_fid['fid__max']:
            fid = int(max_fid['fid__max']) + 1
        else:
            fid = 1
        return fid
    
    def __int__(self):
        if self.fid:
            fid = self.fid
        else:
            fid = 0
        return fid
    


class Order(models.Model):
    STATUS = (
        (ORDER_PENDING_STATUS, ORDER_PENDING_STATUS),
        (ORDER_ACTIVE_STATUS, ORDER_ACTIVE_STATUS),
        (ORDER_READY_STATUS, ORDER_READY_STATUS),
        (ORDER_FAILED_STATUS, ORDER_FAILED_STATUS),
        (ORDER_COMPLETE_STATUS, ORDER_COMPLETE_STATUS),
        (ORDER_DELIVERED_STATUS, ORDER_DELIVERED_STATUS)
    )
    ORIGIN = (
        (ORDER_ORIGIN_FSP_CODE, ORDER_ORIGIN_FSP_CODE),
        (ORDER_ORIGIN_MANUAL_CODE, ORDER_ORIGIN_MANUAL_CODE_TEXT),
    )
    # fsin = models.CharField(max_length=30)
    fid = models.IntegerField(blank=True, null=True)
    client = models.ForeignKey(Client, on_delete=models.SET_NULL, null=True, related_name='orders')
    origin = models.CharField(max_length=8, choices=ORIGIN, default='FSP')
    status = models.CharField(max_length=15, choices=STATUS, default='PENDING')
    shop_order_id = models.IntegerField(blank=True, null=True, db_column='SHOP_ORDER_ID')
    shop_unique_token = models.CharField(blank=True, max_length=255, db_column='SHOP_UNIQUE_TOKEN')
    billing_address = models.JSONField(blank=True, null=True)
    payment_reference_number = models.CharField(max_length=255, blank=True, null=True)
    placed = models.DateTimeField(null=True, blank=True)
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)
    change_log = models.TextField(blank=True)

    class Meta:
        db_table = 'fo_order'

    # this function references the given email address to open intakes and if there are any connects to them
    # NOT TESTED!
    def assign_intake(self, emailAddress=''):
        if not emailAddress:
            return False

        try:
            self.client = Client.objects.filter(email=emailAddress)[1]
            return self.client
        except ObjectDoesNotExist as den:
            this_order = None
            return False

        
    def __int__(self):
        if self.fid:
            fid = self.fid
        else:
            fid = 0
        return fid

    def __str__(self):
        # return "%s Order" % self.client
        return '%s (%s)' % (self.client, self.id)

    # log function for internal monitoring

    def write_log(self, message='',save=True):
        if not message:
            message = 'called but message missing'
        self.change_log += '[%s] %s\n' % (datetime.now(), message)
        if save:
            self.save()

        return True
    
    def save(self, *args, **kwargs):
        if not self.fid:
            #self.fid = Order.objects.aggregate(max_id=Max("fid")).get("max_id",0)+ 1
            #not working
            #self.fid = int(FolderIndex.objects.filter().order_by("-fid")[0]) + 1
            new_fid = FolderIndex()
            fid = new_fid.get_next_fid()
            self.fid = fid
            new_fid.fid = fid
            new_fid.save()
            
        super().save(*args, **kwargs)  # Call the "real" save() method.


ORDER_PRODUCT_PENDING_STATUS = 'PENDING'
ORDER_PRODUCT_ACTIVE_STATUS = 'ACTIVE'
ORDER_PRODUCT_RENDER_STATUS = 'RENDER'
ORDER_PRODUCT_FAILED_STATUS = 'FAILED'
ORDER_PRODUCT_COMPLETE_STATUS = 'COMPLETE'
ORDER_PRODUCT_IDLE_STATUS = 'IDLE'
ORDER_PRODUCT_READY_STATUS = 'READY'
ORDER_PRODUCT_DELIVERED_STATUS = 'DELIVERED'


class OrderProduct(models.Model):
    STATUS = (
        (ORDER_PRODUCT_PENDING_STATUS, ORDER_PRODUCT_PENDING_STATUS),
        (ORDER_PRODUCT_ACTIVE_STATUS, ORDER_PRODUCT_ACTIVE_STATUS),
        (ORDER_PRODUCT_RENDER_STATUS, ORDER_PRODUCT_RENDER_STATUS),
        (ORDER_PRODUCT_FAILED_STATUS, ORDER_PRODUCT_FAILED_STATUS),
        (ORDER_PRODUCT_COMPLETE_STATUS, ORDER_PRODUCT_COMPLETE_STATUS),
        (ORDER_PRODUCT_IDLE_STATUS, ORDER_PRODUCT_IDLE_STATUS),
        (ORDER_PRODUCT_READY_STATUS, ORDER_PRODUCT_READY_STATUS),
        (ORDER_PRODUCT_DELIVERED_STATUS, ORDER_PRODUCT_DELIVERED_STATUS)
    )
    order = models.ForeignKey(Order, related_name='order_products', on_delete=models.CASCADE)
    orderItemId = models.DecimalField(max_digits=10, decimal_places=0, default=0) # this is the id used by the shop
    unitprice = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    discount = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    assets = models.ManyToManyField('FormikoBot.Asset', related_name='order_product_assets', blank=True)
    product = models.ForeignKey(Product, on_delete=models.CASCADE, default='')
    status = models.CharField(max_length=15, choices=STATUS, default='PENDING')
    json = models.JSONField(blank=True, null=True)
    change_log = models.TextField(blank=True)

    class Meta:
        db_table = 'fo_order_products'
    
    #checks if the folder has been created
    def order_folder_created(self):
        folder = self.get_folder(True)
        
        if os.path.isdir(folder):
            retval = True
        else:
            retval = False
        
        return retval

    # returns the production folder on the system
    def get_folder(self, absolute=False):
        folder = "{0:0=6d}".format(self.order.id) + '_'+"{0:0=6d}".format(self.id) + '_' + str(self.order.client.company.abbreviation) + '_' + self.product.fsin
        
        if absolute:
            folder = Path(SHOP_FOLDER) / SHOP_ORDER_FOLDER / folder

        return folder

    # delete folder 
    def remove_folder(self):
        if self.order_folder_created():
            shutil.rmtree(self.get_folder(absolute=True))

    def get_video_file(self):

        _folder = self.get_folder(absolute=True) / settings.SHOP_ORDER_RENDER_OUTPUT_FOLDER
        video_file_path = '{folder}/{filename}.mp4'.format(folder=_folder, filename=self.get_folder(absolute=False))
        return video_file_path

    # log function for internal monitoring
    def write_log(self, message='', save=True):
        if not message:
            message = 'called but message missing'
        self.change_log += '[%s] %s\n' % (datetime.now(), message)
        if save:
            self.save()
        return True

    def __str__(self):
        return 'Product {} for Order Id: {}'.format(self.product.base.name, self.order.id)


PROJECT_ESTIMATE_STATUS = 'ESTIMATE'
PROJECT_ACTIVE_STATUS = 'ACTIVE'
PROJECT_ONHOLD_STATUS = 'ONHOLD'
PROJECT_CLIENT_STATUS = 'CLIENT'
PROJECT_FAILED_STATUS = 'FAILED'
PROJECT_COMPLETE_STATUS = 'COMPLETE'
PROJECT_DELIVERED_STATUS = 'DELIVERED'
PROJECT_PAID_STATUS = 'PAID'


STATUS = (
    (PROJECT_ESTIMATE_STATUS, PROJECT_ESTIMATE_STATUS),
    (PROJECT_ACTIVE_STATUS, PROJECT_ACTIVE_STATUS),
    (PROJECT_ONHOLD_STATUS, PROJECT_ONHOLD_STATUS),
    (PROJECT_CLIENT_STATUS, PROJECT_CLIENT_STATUS),
    (PROJECT_FAILED_STATUS, PROJECT_FAILED_STATUS),
    (PROJECT_COMPLETE_STATUS, PROJECT_COMPLETE_STATUS),
    (PROJECT_DELIVERED_STATUS, PROJECT_DELIVERED_STATUS),
    (PROJECT_PAID_STATUS, PROJECT_PAID_STATUS),
)


# PROJECT MODELS
class Project(models.Model):
    client = models.ForeignKey(Client, on_delete=models.SET_NULL, null=True, blank=True)
    company = models.ForeignKey(Company, on_delete=models.SET_NULL, null=True, blank=True)
    default_vimeo_passwd = models.CharField(max_length=100, default="pwd")
    projectmanager = models.ManyToManyField(ProjectManager)
    name = models.CharField(max_length=256, unique=True)
    folderid = models.IntegerField(null=True, blank=True)
    estimateid = models.IntegerField(null=True, blank=True)
    abbreviation = models.CharField(max_length=10, unique=True)
    change_log = models.TextField(null=True, blank=True)
    video_target_width = models.IntegerField(default='1280') # will be removed soon (now handled via project_videos: resolution
    video_target_height = models.IntegerField(default='720')  # will be removed soon (now handled via project_videos: resolution
    video_target_size = models.IntegerField(default='2')  # will be removed soon (now handled via project_videos: resolution
    video_target_duration = models.DurationField(default=timedelta(seconds=1))   # will be removed soon (now handled via project_videos: resolution
    deadline = models.DateTimeField(blank=True, null=True)
    feedbackloops = models.IntegerField(default='2')
    shootingdays = models.DecimalField(max_digits=6, decimal_places=1, default='0')
    #unitprice = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    #discount = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    budget = models.DecimalField(max_digits=6, decimal_places=2, default='0')
    paid = models.DecimalField(max_digits=6, decimal_places=2, default='0')
    status = models.CharField(max_length=50, choices=STATUS, default='PENDING')
    tasks = models.ManyToManyField('FormikoBot.Task', related_name='tasks', blank=True)
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'fo_project'

    def find_folder(self, folder_path, folder_pattern):
        project_path = ''
        if not os.path.isdir(folder_path):
            return False
            # self.stdout.write(self.style.WARNING('[CHECK]\tClient CI path exits!'))
        else:
            # let's see if we find the ID

            d = folder_path
            # d = '.'
            dir_list = [os.path.join(d, o) for o in os.listdir(d)
                        if os.path.isdir(os.path.join(d, o))]
            # self.stdout.write("\tAvailable directories:\t\t%s" % dir_list)
            #self.stdout.write("\tLooking for:\t\t\t%s" % project_pattern)
            # x =  dir_list.index(client_id_formatted + '*')
            match = fnmatch.filter(dir_list, folder_pattern)
            if match:
                #self.stdout.write("[CHECK]\tProject folder found!\t\t%s" % match)
                project_path = Path(folder_path) / match[0]
                #self.stdout.write("\t\t\t\t\t%s" % project_path)
            #else:
                #self.stdout.write(self.style.ERROR('[ERROR] Project folder doesnt exit!'))
        return project_path

    def get_folder(self, absolute=False):

        return self.find_folder()

        #folder = "{0:0=4d}".format(self.folderid) #+ '_' + str(self.sender)

        #if absolute: #not yet implemented
            # self.stdout.write("\tLooking for:\t\t\t%s" % project_pattern)
            # x =  dir_list.index(client_id_formatted + '*')
        match = fnmatch.filter(dir_list, folder_pattern)
        if match:
                # self.stdout.write("[CHECK]\tProject folder found!\t\t%s" % match)
            folder_path = Path(folder_path) / match[0]
                # self.stdout.write("\t\t\t\t\t%s" % project_path)
            # else:
            # self.stdout.write(self.style.ERROR('[ERROR] Project folder doesnt exit!'))
        return folder_path

    def get_footage_folder(self, absolute=False):
        project_pattern = '*' + '*Footage*'
        return self.find_folder(self.get_folder(), project_pattern)

    def get_folder(self, absolute=False):

        project_pattern = '*' + "{0:0=4d}".format(self.folderid) + '*'
        return self.find_folder(PROJECT_FOLDER,project_pattern)

        # folder = "{0:0=4d}".format(self.folderid) #+ '_' + str(self.sender)

        # if absolute: #not yet implemented
        #    folder =  Path(PROJECT_FOLDER) / folder

        return Path(folder)

    def __str__(self):
        return '%s (%s)' % (self.name, self.client)

# journal is the line item for the CRM
# a journal can be attatched to a client and be related to a project as well
#class Journal(models.Model):
 #   name = models.CharField(max_length=255)
 #   client = models.ForeignKey(Client, on_delete=models.SET_NULL, null=True, blank=True)
 #   project = models.ForeignKey(Project, on_delete=models.SET_NULL, blank=True, null=True, related_name="journals")
 #   created = models.DateTimeField(auto_now_add=True)
 #   updated = models.DateTimeField(auto_now=True)

 #   class Meta:
 #       ordering = ['-created']
 #       db_table = 'fo_journal'

  #  def __str__(self):
  #      return '%s, (%s)' % (self.name, self.client)



# VIDEO MODELS
VIDEO_PENDING_UPLOAD = 'PENDING'
VIDEO_UPLOADING_NOW = 'UPLOADING'
VIDEO_UPLOADING_COMPLETE = 'COMPLETE'
VIDEO_UPLOADING_FAILED = 'FAILED'
VIDEO_RENDERING = 'RENDERING'
VIDEO_RENDERING_COMPLETED = 'RENDERING COMPLETE'
VIDEO_RENDERING_FAILED = 'RENDERING FAILED'



class Video(models.Model):
    STATUS = (
        (VIDEO_PENDING_UPLOAD, VIDEO_PENDING_UPLOAD),
        (VIDEO_UPLOADING_NOW, VIDEO_UPLOADING_NOW),
        (VIDEO_UPLOADING_COMPLETE, VIDEO_UPLOADING_COMPLETE),
        (VIDEO_UPLOADING_FAILED, VIDEO_UPLOADING_FAILED),
        (VIDEO_RENDERING, VIDEO_RENDERING),
        (VIDEO_RENDERING_COMPLETED, VIDEO_RENDERING_COMPLETED),
        (VIDEO_RENDERING_FAILED, VIDEO_RENDERING_FAILED)
    )
    project = models.ForeignKey(Project, on_delete=models.SET_NULL, blank=True, null=True, related_name="videos")
    order_product = models.ForeignKey(OrderProduct, on_delete=models.SET_NULL, null=True, blank=True, related_name='order_videos')
    vimeo_id = models.CharField(max_length=255, blank=True)
    vimeo_passwd = models.CharField(max_length=100, blank=True)
    url = models.TextField(blank=True)
    url_review = models.TextField(blank=True)
    url_download = models.TextField(blank=True)
    status = models.CharField(max_length=50, choices=STATUS, default='PENDING')
    size = models.IntegerField(blank=True, default=0)
    rendering_time = models.IntegerField(blank=True, default=0)
    renderer_job_id = models.CharField(max_length=255, blank=True)
    unique_fn = models.CharField(max_length=255, blank=True)
    version = models.CharField(blank=True, max_length=255)
    episode = models.SmallIntegerField(blank=True, null=True)
    description = models.TextField(blank=True)
    resolution = models.ForeignKey(Resolution, on_delete=models.SET_NULL, blank=True, null=True, related_name="video_resolution")
    duration = models.IntegerField(blank=True, default=0)
    bitrate = models.BigIntegerField(blank=True, default=0) #new
    fps = models.IntegerField(blank=True, default=0)  # new
    codec_name =  models.CharField(max_length=20, blank=True) # new
    codec_long_name = models.CharField(max_length=100, blank=True) #new
    pix_fmt = models.CharField(max_length=20, blank=True) #new
    ffprobe_result = JSONField(null=True, blank=True)
    language = models.ForeignKey(Language, on_delete=models.SET_NULL, related_name='video_languages', blank=True, null=True) # the spoken language of the video
    sub_language = models.ForeignKey(Language, on_delete=models.SET_NULL, related_name='subtitle_languages', blank=True, null=True)  # if empty no subtitle
    response_upload = JSONField(null=True, blank=True)
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created']
        db_table = 'fo_video'

    def __str__(self):
        return '%s, %s,%s,%s,%s' % (
            self.vimeo_id, self.vimeo_passwd, self.url, self.status, self.unique_fn)


#@receiver(post_save, sender=Video)
def send_video_notification(sender, ** kwargs):

    # notify users
    video = kwargs.get('instance')
    paloma_user = User.objects.get(username=BOT_PALOMA_USERNAME)
    recepients = User.objects.all()
    verb_text = False

    if video.status == VIDEO_UPLOADING_COMPLETE:
        verb_text = 'upload of video <b>%s</b> complete ' % video.unique_fn
        level = 'success'
    elif video.status == VIDEO_UPLOADING_NOW:
        verb_text = 'uploading video <b>%s</b> complete ' % video.unique_fn
        level = 'success'
    elif video.status == VIDEO_UPLOADING_FAILED:
        verb_text = 'upload of video <b>%s</b> failed! ' % video.unique_fn
        level = 'error'
    elif video.status == VIDEO_RENDERING_COMPLETED:
        verb_text = 'rendering of video <b>%s</b> complete ' % video.unique_fn
        level = 'success'
    elif video.status == VIDEO_RENDERING_FAILED:
        verb_text = 'rendering of video <b>%s</b> failed! ' % video.unique_fn
        level = 'error'

    if verb_text:
        notify.send(paloma_user, recipient=recepients, verb=verb_text, description='', level=level, action_object=video, taget=video)

post_save.connect(send_video_notification, sender=Video)

class ProjectVideo(models.Model):
    name = models.CharField(max_length=50)
    project = models.ForeignKey(Project, related_name='project_videos', on_delete=models.CASCADE)
    unitprice = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True) # if null, than it's part of the project's budget
    discount = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    resolution = models.ForeignKey(Resolution, on_delete=models.SET_NULL, blank=True, null=True, related_name="projectvideo_resolution")
    episode = models.SmallIntegerField(blank=True, null=True)
    videos = models.ManyToManyField(Video, related_name="project_videos", blank=True)
    duration = models.IntegerField(default='0')  # expected runtime in seconds
    language = models.ForeignKey(Language, on_delete=models.SET_NULL, related_name='prokectvideo_languages', blank=True,
                                 null=True)  # the spoken language of the video (not in use yet)
    sub_language = models.ForeignKey(Language, on_delete=models.SET_NULL, related_name='projectvideo_subtitle_languages', blank=True,
                                     null=True)  # if empty no subtitle

    feedbackloops = models.IntegerField(default='2')
    change_log = models.TextField(blank=True)
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'fo_project_videos'
        ordering = ['-created']

    def __str__(self):
        return '%s (%s)' % (
            self.name, self.project)

    def getCorrectFilename(self, filename=''):
        if self.project:
            if not filename:
                filename = self.name
            complete_filename = f'{self.project.company.abbreviation}_{self.project.abbreviation}_{filename}'
            if self.episode:
                complete_filename += '_EP_' + str(self.episode)
            if self.sub_language:
                complete_filename += '_SUB_' + (self.sub_language.abbreviation).upper()

            complete_filename += '_DRAFT_x.mp4'

            return complete_filename

class VimeoResponse(models.Model):
    video = models.OneToOneField(
        Video,
        related_name='vimeo_responses',
        on_delete=models.CASCADE,
    )
    endpoint = models.URLField(max_length=255)
    response_text = JSONField(null=True)

    class Meta:
        db_table = 'fo_vimeoresponse'


# INTAKE MODELS
class Intake(models.Model):
    sender = models.EmailField()
    order = models.ForeignKey(Order, on_delete=models.CASCADE, null=True, blank=True, related_name='orders')
    client = models.ForeignKey(Client, on_delete=models.SET_NULL, null=True, blank=True, related_name='clients')
    project = models.ForeignKey(Project, on_delete=models.SET_NULL, null=True, blank=True, related_name='intakes')
    change_log = models.TextField()
    shop_order_id = models.IntegerField(blank=True, null=True, db_column='SHOP_ORDER_ID')
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'fo_intake'

    def __str__(self):
        return self.sender

    def has_videos(self):
        return 'na'

    def write_log(self, message='', save=True):
        if not message:
            message = 'called but message missing'
        self.change_log += '[%s] %s\n' % (datetime.now(), message)
        if save:
            self.save()
        return True

    def get_client(self):
        try:
            this_client = Client.objects.filter(email=self.sender)[0]
            return this_client
        except:
            return False

        
    # gets the path in which the order has been stored
    # it also sets client or company if some matching info is found in orders
    def get_path(self):

        if not self.sender:
            return False
        
        this_client = None
        this_order = None
        
        #this code below was used before intakes were stored in the [ID]_NAME format:

        # let's see if the sender email is matching any known client..
        #try:
        #    this_client = Client.objects.filter(email=self.sender)[0]
        #    self.client = this_client
        #except ObjectDoesNotExist as den:
        #    this_order = None
            # if we don't find a client with this email address, we are going to store the intake
            # in our default UNASSIGNED folder in a subdirectory with this address
        #    designated_folder = Path(INTAKE_FOLDER_UNASSIGNED) / self.sender
        #except:
        #    designated_folder = Path(INTAKE_FOLDER_UNASSIGNED) / self.sender

        #    print("Check for client: %s [%s]" % (self.sender, this_client))
        #if this_client:
            # so we found a client yeah!
        #    print("We found a client matching the sending email (%s)" % self.sender)
            
        #    print("Company: %s " % this_client.company)
        #    designated_folder = str(this_client.company) + '_' + str('%03d' % this_client.company.id)

            # let's see now if there is an open order
         #   try:
                # we link this to the first order we can find
          #      this_order = Order.objects.filter(client=this_client.id)[0]
        #    except ObjectDoesNotExist as den:
         #       print(
          #          "We didn't find any order matching this upload so the subfolder will be %s" % INTAKE_FOLDER_UNASSIGNED)
                # designated_folder =  this_order.get_INTAKE_FOLDER()
           #     designated_folder = Path(designated_folder) / INTAKE_FOLDER_UNASSIGNED / self.sender
            #except:
             #   print("We didn't find any order matching this upload.")

            #if this_order:
            #    print("We found an order: %s" % (this_order.id))
            #    designated_folder = Path(designated_folder) / Path(INTAKE_FOLDER_ORDER + str(this_order.id))
            #    print("so we will place all files in the company folder: ", designated_folder)
             #   order_id = this_order.id
            #    self.order = this_order
            #else:
             #   order_id = None
              #  designated_folder = Path(designated_folder) / INTAKE_FOLDER_UNASSIGNED / self.sender
        #return Path(INTAKE_FOLDER) / designated_folder
        folder = "{0:0=5d}".format(self.id) + '_' + str(self.sender)
        
        return Path(INTAKE_FOLDER) / folder

        # gets the path in which the order has been stored
        # it also sets client or company if some matching info is found in orders

    def get_folder(self, absolute=False):

        if not self.sender:
            return False

        folder = "{0:0=5d}".format(self.id) + '_' + str(self.sender)

        if absolute:
            folder =  Path(INTAKE_FOLDER) / folder

        return Path(folder)

    def file_count(self):
        # return File.objects.annotate(Count('intake'))
        myFiles = File.objects.annotate(number_of_files=Count('intake'))
        return myFiles[0].number_of_files


class File(models.Model):
    intake = models.ForeignKey(Intake, on_delete=models.CASCADE, null=True, related_name='files')
    filename = models.CharField(max_length=255)
    filepath = models.CharField(max_length=1024)
    filetype = models.CharField(max_length=6)
    size = models.BigIntegerField()
    remark = models.TextField(blank=True)
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'fo_files'

    def get_path(self):
        return Path(self.intake.get_path()) / self.filename

    def __str__(self):
        return self.filename

#
# SIGNALS
#

#@receiver(post_save, sender=Company)
def check_company_folder(sender, **kwargs):
    company = kwargs.get('instance')
    
    correct_folder = company.get_folder(True)
    #if the correctly named folder doesn't exists...
    logger.debug('Checking if correct folder exists [%s]' % correct_folder)
    if not os.path.isdir(correct_folder):
        
        #we check if there is a folder with the correct id but the wrong name
        real_folder = company.get_real_folder(True)
        
        #if there is no folder at all we create one
        if not os.path.isdir(real_folder):
            logger.debug('Folder not existing. Trying to create one [%s]' % correct_folder)
            try:
                os.mkdir(correct_folder)
            except:
                logger.error('[ERROR] Could not create [%s]' % correct_folder)
        else:
            #this means we have a real folder but the wrong name.. so we'll conform it to the correct name
            logger.debug('Folder [%s] existing but will be named correctly: [%s]' % (real_folder, correct_folder))
            try:
                os.rename(real_folder, correct_folder)
            except:
                logger.error('[ERROR] Could not rename folder [%s] to [%s]' % (real_folder, correct_folder))
    
    #else: the correctly named folder exists so we lean back happily and do nothing
            
    


def check_client_folder(sender, **kwargs):
    client = kwargs.get('instance')
    
    correct_folder = client.get_folder(True)
    #if the correctly named folder doesn't exists...
    logger.debug('Checking if correct client folder exists [%s]' % correct_folder)
    if not os.path.isdir(correct_folder):
        
        #we check if there is a folder with the correct id but the wrong name
        real_folder = client.get_real_folder(True)
        
        #if there is no folder at all we create one
        if not os.path.isdir(real_folder):
            logger.debug('Folder not existing. Trying to create one [%s]' % correct_folder)
            try:
                os.mkdir(correct_folder)
            except Exception as exc:
                logger.error(exc)
                logger.error('[ERROR] Could not create [%s]' % correct_folder)
        else:
            #this means we have a real folder but the wrong name.. so we'll conform it to the correct name
            logger.debug('Folder [%s] existing but will be named correctly: [%s]' % (real_folder, correct_folder))
            try:
                os.rename(real_folder, correct_folder)
            except:
                logger.error('[ERROR] Could not rename folder [%s] to [%s]' % (real_folder, correct_folder))
    
    #else: the correctly named folder exists so we lean back happily and do nothing
            
    
post_save.connect(check_company_folder, sender=Company)
post_save.connect(check_client_folder, sender=Client)

    

