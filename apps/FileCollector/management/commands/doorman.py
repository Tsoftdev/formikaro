#!/usr/bin/env python3

#
# Copyright (c) 2020 Ioanes Sinderman / Filmagio Cine Produktion
#
# Version 0.44
# Date: 19. 5. 2021
#
# checks the integrity of OrderProducts and sets STATUS of the products accordingly
# also tries to find the right intakes
# 
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED
# TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR
# PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS
# BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
# CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
# SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
# CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.

from pathlib import Path
import os
import re
import sys

#django librarys
from django.conf import settings
from django.core.management.base import BaseCommand
from django.db.models import Q
from django.contrib.auth.models import User
from django.core.exceptions import ObjectDoesNotExist
from datetime import datetime
from apps.FileCollector.models import File, Intake, Client, Company, ProjectManager, Order, OrderProduct, ORDER_PENDING_STATUS, ORDER_ACTIVE_STATUS, ORDER_FAILED_STATUS, ORDER_COMPLETE_STATUS, ORDER_DELIVERED_STATUS, ORDER_PRODUCT_PENDING_STATUS, ORDER_PRODUCT_ACTIVE_STATUS, ORDER_PRODUCT_FAILED_STATUS, ORDER_PRODUCT_COMPLETE_STATUS, ORDER_PRODUCT_IDLE_STATUS, ORDER_PRODUCT_READY_STATUS, ORDER_PRODUCT_DELIVERED_STATUS
from apps.FormikoBot.models import Task




from apps.ProductManager.models import Product, ProductBase, ProductTextModel, Language, Resolution
from django.core.exceptions import ObjectDoesNotExist
import argparse
from notifications.signals import notify

BOT_LASTNAME = settings.BOT_LASTNAME
BOT_DOORMAN_USERNAME=settings.BOT_DOORMAN_USERNAME

#path where all the downloads will be put
INTAKE_FOLDER = settings.INTAKE_FOLDER  # '/home/worker/Projects/mount/intake'
INTAKE_FOLDER_UNASSIGNED = settings.INTAKE_FOLDER_UNASSIGNED
INTAKE_FOLDER_ORDER = settings.INTAKE_FOLDER_ORDER

#Time in seconds until the product.order.status will change to FAILED
INTAKE_TIMEOUT = settings.INTAKE_TIMEOUT

# / on linux \\ on windows
INTAKE_SLASH = '\\'

#needed for the verification/extraction of email
regex = re.compile(("([a-z0-9!#$%&'*+\/=?^_`{|}~-]+(?:\.[a-z0-9!#$%&'*+\/=?^_`"
                    "{|}~-]+)*(@|\sat\s)(?:[a-z0-9](?:[a-z0-9-]*[a-z0-9])?(\.|"
                    "\sdot\s))+[a-z0-9](?:[a-z0-9-]*[a-z0-9])?)"))

# this function tries to find an intake that mateches the order
# in case it finds one it links them together
# this function will only be called if an intake arrives BEFORE the order is fetched by the fovo api
def linkIntake(this_order):
    # so here's the magic to link the intake to the order. 
    # a similar piece of code is used in the filecollector for the inital try to link an incoming intake to an order
            
    sorting_message = ''
    this_client = this_order.client
    #so here's the magic to link the intake to the order. 
   
    # see if the intake has a shop_order_id
    try:
        this_intake = Intake.objects.filter(shop_order_id=this_order.shop_order_id).first()
        if this_intake:
            self.stdout.write("Found an intake through shop_order_id [%s]" % (this_order.shop_order_id))
            sorting_message += 'Found an order through shop_order_id [%s]\n' % (this_order.shop_order_id)
            
        #if the order is not linked through shop_order_id...
    except:
        if not this_order and not this_client:
            self.stdout.write("Didn't find any order matching shop_order_id [%s]" % (this_order.shop_order_id))
            sorting_message += 'Did not find any shop_order_id [' + str(this_order.shop_order_id) + ']\n'

    # if not try to find an intake that linked to the customer (this has been done by the code before in the main function!)

# creating the doorman user
def create_doorman_user():

    doorman = User.objects.create_user(username=BOT_DOORMAN_USERNAME, email='doorman@formikaro.io', password='d00rm4n', first_name=BOT_DOORMAN_USERNAME, last_name=BOT_LASTNAME)
    doorman.save()
    return doorman


def check_doorman_pm():

    #doorman = User.objects.filter(username=BOT_DOORMAN_USERNAME)
    try:
        doorman_pm = ProjectManager.objects.get(firstname=BOT_DOORMAN_USERNAME)
    except:
        doorman = create_doorman_user()
        doorman_pm = ProjectManager.objects.get(firstname=BOT_DOORMAN_USERNAME)

    return doorman_pm

"""
DoorMan v0.44
this is the doorman function. It checks if there are open orders (status==pending). If yes it iterates all
related products and checks for:
    +) if status == pending
        if this this product needs files?
            and sets status = ACTIVE if they are here or status FAILD if they timed out (INTAKE_TIMEOUT)
    It also sets the order status to ACTIVE if all orderes products are READY or FAILED if at least one of them is FAILED
    
    Missing:
        -) check if the files in the intake really are usefull or at least match the material we need for the production
        -) check if the ordered product is active and if not let someone know
        -) incorporate a standardizes function for all the logging done into the db
"""
class Command(BaseCommand):
    help='Does what doormen do: check who\'s coming in, how to help and keep everything'

    def add_arguments(self, parser):
         parser.add_argument('--order', action='append', type=int)

    def DoorMan(self, orderId=''):
        print (">This is the DoorMan speaking, let's see what we have to do today...")

        #testing notifications START
        doorman_user = check_doorman_pm()
        #doorman_user = User.objects.get(username=BOT_DOORMAN_USERNAME)
        recepients = User.objects.all()

        notify.send(doorman_user, recipient=recepients, verb='did my job down there', description='This is a test notification of the doorman command', level='success')

        exit()
        #testing notifications END


        if orderId:
            orders = Order.objects.all().filter(id=orderId)
        else:
            orders = Order.objects.all().filter(status=ORDER_PENDING_STATUS)

        if orders:
            self.stdout.write('[INFO]\tIntake timeout: %s' % INTAKE_TIMEOUT )
            self.stdout.write('>Here\'s a list of the open orders: ')
            self.stdout.write('===================================================\n')

            for order in orders:
                self.stdout.write(">Order:\t%s\t|\tClient: %s " % (order.id, order.client))
                ordered_products = OrderProduct.objects.all().filter(order=order.id)
                numProductsReady = 0
                numProducts = 0
                FailedFlag = False
                for product in ordered_products:
                    numProducts = numProducts + 1
                    self.stdout.write(">----------------------------")
                    self.stdout.write(">Product: %s\t| FSIN: [%s]\t| Status: %s" % (product.id, product.product.fsin, product.status))

                    if product.status == ORDER_PRODUCT_PENDING_STATUS:
                    #so if the status is pending we will check if all requirements are met to set it ACTIVE (or FAILED of something is wrong)

                        #here we will check the integrity
                        if product.product.base.needs_intake:
                            self.stdout.write(">Product %s needs files. Let's see if we find them..." % product.product.fsin)

                            #ok we need files.. let's see if we find them
                            try:
                                intake = Intake.objects.get(order=order.id)

                                self.stdout.write(">Found this intake:\tID %s" % intake.id)
                                #here we would check if the intake matches the product requirements (this will be implemented in the future)
                                #for now we are just happy that there is an intake at all

                                #so this product is ready for the next step...
                                self.stdout.write(">Product %s has a matching intake. So we'll set status from %s to:\t\t%s" % (product.product.fsin, product.status, ORDER_PRODUCT_READY_STATUS))
                                #product.change_log += '[%s] DoorMan set status READY because Intake was found (%s)\n' % (datetime.now(), intake.id)
                                product.write_log('DoorMan changed status from %s to %s because Intake was found (%s)' % (product.status, ORDER_PRODUCT_READY_STATUS, intake.id))
                                product.status = ORDER_PRODUCT_READY_STATUS
                                product.save()
                                numProductsReady = numProductsReady + 1

                            except ObjectDoesNotExist as den:
                                self.stdout.write(">Didn't find a linked intake to this order. So we'll check if there is any intake linked to the client")

                                #try to find an intake that matches the criteria for this order and link it to it
                                linkIntake(order)

                                this_intake = Intake.objects.filter(Q(client=order.client.id)  & Q(order__isnull=True)).first()


                                if this_intake:
                                    this_intake.order = order
                                    this_intake.save()
                                    #so this product is ready for the next step...
                                    self.stdout.write(">Product %s has a matching intake. So we'll set status from %s to:\t\t%s" % (product.product.fsin, product.status, ORDER_PRODUCT_READY_STATUS))
                                    product.write_log('DoorMan set status READY because Intake was found (%s)\n' % this_intake.id)
                                    #product.change_log += '[%s] DoorMan set status READY because Intake was found (%s)\n' % (datetime.now(), intake.id)
                                    product.status = ORDER_PRODUCT_READY_STATUS
                                    product.save()
                                    numProductsReady = numProductsReady + 1
                                    self.stdout.write(">Found an intake and linked it to this order (%s)" % this_intake)
                                else:
                                    self.stdout.write(">No intake found. So we'll keep waiting")
                                #the order has been pending to long.. we consider it failed

                                #let's see how much times has passed
                                order_time =datetime.timestamp(order.created)
                                now_time = datetime.timestamp(datetime.now())
                                self.stdout.write("Order placed:\t%s" % order.created )
                                self.stdout.write("Now:\t\t%s" % now_time )
                                #time_passed =  datetime.now() - datetime.timestamp(order.created)
                                time_passed = now_time - order_time
                                time_passed_minutes = int(time_passed/60)
                                self.stdout.write("Time passed:\t%s minutes (or %s seconds)" % (time_passed_minutes, time_passed))

                                if int(time_passed) > int(INTAKE_TIMEOUT):
                                    self.stdout.write("Too much time (%s minutes) has passed without getting the intake. Setting status to FAILED!\nif this seems to short please adjust INTAKE_TIMEOUT (currently set to %s seconds) " % (time_passed_minutes, INTAKE_TIMEOUT))
                                    #product.change_log += '[%s] DoorMan set status FAILED because INTAKE_TIMEOUT was reached\n' % datetime.now()
                                    product.write_log('DoorMan set status %s because INTAKE_TIMEOUT was reached\n' % ORDER_PRODUCT_FAILED_STATUS)
                                    product.status = ORDER_PRODUCT_FAILED_STATUS
                                    product.save()
                                    FailedFlag = True
                                else:
                                    time_passed_minutes = int(time_passed/60)
                                    self.stdout.write("Only (%s minutes) have passed without getting the intake. So here we wait." % (time_passed_minutes))


                            #ok we didn't find them let's see how long this order is already in this state..

                        else:
                            #ok we don't need an intake, but what about assets?
                            #check if assets are needed:
                            if product.product.base.assets.all():
                                self.stdout.write(">ProductBase \"%s\" [%s] needs the following asset(s):" % (product.product.base.name, product.product.base.fsin_base))

                                assets_offline = False # flag if we find a missing asset, checked after the loop
                                for asset in product.product.base.assets.all():
                                    file_status ='offline'
                                    assets_offline = True

                                    # create tasks if necessary
                                    # THIS NOW LIVES IN THE ASSEMBLER
                                    #if asset.tasks:
                                    #   doorman = check_doorman_pm()
                                    #   for task in asset.tasks.all():
                                    #       self.stdout.write("FOUND TASK! [%s]" % task)
                                                #new_task = Task.objects.create(name=task.name,creator=doorman, status='OPEN')
                                                #product.write_log(
                                                #    'Doorman added task %s to this product ' % new_task

                                    if asset.assettype.is_file:
                                        asset_link = asset.get_filename(True, product)

                                        if asset_link:
                                            asset_link = Path(asset_link)

                                            if asset_link.is_file():
                                                file_status = 'online'
                                                assets_offline = False

                                        #elif asset.assettype.name == 'JSON':
                                        # here we check if the orderproduct has json set
                                        #    if product.json:
                                        #        file_status = 'online'
                                        #    else:
                                        #        self.stdout.write("JSON NOT FOUND!")
                                        #        assets_offline = True
                                        #else:
                                        #    assets_offline = True

                                        self.stdout.write(" %s [%s] (%s)\t\t%s\n\t\t\t\t\t\t\t\t%s" % (asset.name, asset.id, asset.assettype, asset_link, file_status))
                                    else:
                                        self.stdout.write("Asset [%s][%s] seems to exits" % (asset.name, asset.value))
                                        assets_offline = False

                                #if we are missing any asset for production set status to FAILED
                                if assets_offline:
                                    product.write_log('ProductBase %s [%s] needs assets for production that were not found. Change status from %s to: %s' % (product.product.base.name, product.product.base.fsin_base, product.status, ORDER_PRODUCT_FAILED_STATUS), False) #False to save as we are going to save as the next step anyway
                                    product.status = ORDER_PRODUCT_FAILED_STATUS
                                    product.save()
                                    FailedFlag = True
                                else:
                                    #we have all assets and are ready for production
                                    numProductsReady = numProductsReady + 1
                                    self.stdout.write(">Product %s has all assets online. So we'll change status from %s to:\t%s" % (product.product.fsin, product.status, ORDER_PRODUCT_READY_STATUS))

                                    product.write_log('Product %s has all assets online. So we\'ll set status from %s to %s' % (product.product.fsin, product.status, ORDER_PRODUCT_READY_STATUS), False) #False to save as we are going to save as the next step anyway
                                    product.status = ORDER_PRODUCT_READY_STATUS
                                    product.save()

                            else:
                            #so we need neither intake nor assets, than we are ready..
                                self.stdout.write(">Product %s needs no files/assets. So we'll set status from %s to:\t%s" % (product.product.fsin, product.status, ORDER_PRODUCT_READY_STATUS))
                                numProductsReady = numProductsReady + 1

                                #log our action to the OrderProduct and save
                                #product.change_log += '[%s] DoorMan set status READY because no files or assets are necessary for prodution\n' % datetime.now()
                                product.write_log('DoorMan changes status from %s to %s because no files or assets are necessary for prodution' % (product.status, ORDER_PRODUCT_READY_STATUS))
                                product.status = ORDER_PRODUCT_READY_STATUS
                                product.save()

                    elif product.status != ORDER_PRODUCT_FAILED_STATUS:
                        #if this product's status is anything but PENDING or FAILED
                        #let's count this one as a ready product
                        numProductsReady = numProductsReady + 1
                    elif product.status == ORDER_PRODUCT_FAILED_STATUS:
                        FailedFlag = True

                #ok now that we have checked all products we will see if we have to change the order status
                self.stdout.write("\nSummary\t %s of %s products are ready ...." % (numProductsReady, numProducts))
                if numProductsReady == numProducts:
                    self.stdout.write("...so we set the order status to\t\t\t\t\t\t\tACTIVE")
                    order.write_log('DoorMan changes status from %s to %s because all OrderProducts are ready for production' % (order.status, ORDER_ACTIVE_STATUS), False)
                    order.status = ORDER_ACTIVE_STATUS
                    order.save()
                elif FailedFlag:
                    self.stdout.write("...so we set the order status to\t\t\t\t\t\t\tFAILED")
                    order.status = ORDER_FAILED_STATUS
                    order.write_log('DoorMan set status to %s because some OrderProducts failed' % ORDER_FAILED_STATUS)
                    order.save()

                self.stdout.write(">----------------------------\n")
        else:
            self.stdout.write(">There are no pending orders. Back to chillin' ")

    def handle(self, **options):
        if options['order']:
            order_id = options['order'][0]
        else:
            order_id = False
        #self.stdout.write("Xprocess: ", order_id)
        self.DoorMan(order_id)
        #check_doorman_user()

