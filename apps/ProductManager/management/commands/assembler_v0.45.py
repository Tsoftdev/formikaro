#!/usr/bin/env python3

#
# Copyright (c) 2021 Ioanes Sinderman / Filmagio Cine Produktion
#
# Version 0.45
# Date: 27.4.2021
# 
# This commands gets an order_id and creates all it's products in the pre defined order folder
# As of version 0.40 it also accepts an order_product_id
#
# If an order is created the function does:
#   +) create new folder in the predefined ORDER folder [order_id]_[FSIN]
#   +) collect assets (of productbase + product) and puts them into predefined ORDER/ASSETS
#   +) collects intakes (if products needs_files is True) and puts them into the predefined FOOTAGE folder
#   +) copies only the workfile (pr/ae) of the product into the ORDER folder
#   +) if everything is ok, set order status to ACTIVE and product status to IDLE
#
#   /) intake collecting not very much testes
#
# MISSING FEATURES:
# -----------------
#   -) check if order already exists
#   -) check for all products to create if status == READY
#   -) handle warning if files are overwritten
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
import json
import fnmatch
#import _winapi #only works on windows
import shutil  

#django librarys
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.core.exceptions import ObjectDoesNotExist
from datetime import datetime
from apps.FileCollector.models import File, Intake, Client, Company, Order, OrderProduct, ORDER_PENDING_STATUS, ORDER_ACTIVE_STATUS, ORDER_FAILED_STATUS, ORDER_COMPLETE_STATUS, ORDER_DELIVERED_STATUS, ORDER_PRODUCT_PENDING_STATUS, ORDER_PRODUCT_ACTIVE_STATUS, ORDER_PRODUCT_FAILED_STATUS, ORDER_PRODUCT_COMPLETE_STATUS, ORDER_PRODUCT_IDLE_STATUS, ORDER_PRODUCT_READY_STATUS, ORDER_PRODUCT_DELIVERED_STATUS
from apps.FormikoBot.models import Asset
from apps.ProductManager.models import Product, ProductBase, ProductTextModel, Language, Resolution
from django.core.exceptions import ObjectDoesNotExist

#path where all the downloads will be put
SHOP_FOLDER = settings.SHOP_FOLDER #'/home/worker/Projects/mount/intake'
SHOP_SHELF_FOLDER = settings.SHOP_SHELF_FOLDER
SHOP_DEFAULT_ASSETS_FOLDER = settings.SHOP_DEFAULT_ASSETS_FOLDER
SHOP_ORDER_FOLDER = settings.SHOP_ORDER_FOLDER
SHOP_CLIENT_CI_FOLDER = settings.SHOP_CLIENT_CI_FOLDER
SHOP_DEFAULT_FOOTAGE_FOLDER = settings.SHOP_DEFAULT_FOOTAGE_FOLDER
SHOP_ORDER_RENDER_OUTPUT_FOLDER = settings.SHOP_ORDER_RENDER_OUTPUT_FOLDER

# this will take the custom_json for this product and append all general information like colors and fonts to it
def write_json_file(custom_json, immaterial_json, json_file):
    
    #check if there is a custom_json. if not leave it empty
    try:
        json.loads(custom_json)
    except:
        custom_json = {}
    
    combined_json = {**custom_json, **immaterial_json}
    #print("immaterial JSON: %s " % combined_json )
    
    with open(json_file, 'w') as outfile:
        json.dump(combined_json, outfile)
        
# small search function for the dictionarys
def search(values, searchFor):
    for k in values:
        for v in values[k]:
            if searchFor in v:
                return k
    return None

        
# this function is tailored to read the output of the shop api (FOVO) and convert it into a simple text array TEXT_1, TEXT_2,..

def processShopJSON(shop_json):
    
    if not shop_json:
        return False

    this_json = {}
    #raw_json = str(shop_json)
    #raw_json = raw_json.replace("\'", "\"")
    #raw_json = raw_json.replace("null", "\"null\"") # this is a hack! the api should deliver json conform values instead 
    #raw_json = raw_json.replace("None", "\"None\"")
    
    # self.stdout.write("JSON;", raw_json)
    #print("DEBUG INSIDE")
    #this_jsons = json.loads(raw_json)

    
    try:
        #this_json = {}
        #raw_json = str(shop_json)
        #raw_json = raw_json.replace("\'", "\"")
        #raw_json = raw_json.replace("null", "\"null\"") # this is a hack! the api should deliver json conform values instead 
        #raw_json = raw_json.replace("None", "\"None\"")
        
        # self.stdout.write("JSON;", raw_json)
        #print("DEBUG INSIDE")
        this_jsons = shop_json #json.loads(raw_json)
        
        custom_json = {}
        k = 0
        
        #print("[JSON!] Going for JSON")
        for i in range(len(this_jsons)):
            
            label = this_jsons[i]['label'].upper()

            #print("\tYYY %s\t%s" % (i, label)) #debug
            #self.stdout.write("\t\tlabel: %s" % label)
            
            if label.find('RESOLUTION') == -1 and label.find('AUFLÖSUNG') == -1:
                
                key = "TEXT_" + str(k+1)
                #print("\t\t[JSON] LABEL [%s] KEY [%s]" % (label, key))
                custom_json[key] = {}
                
                #custom_json[k][key] = 
                #here should be also the check for lenght, format and code we don't want in our aftereffect to be injected
                custom_json[key] = this_jsons[i]['value']
                k = k + 1
                #self.stdout.write("\t\tJSON label: %s  value %s " % (this_jsons[i]['label'], this_jsons[i]['value']))
            #else:
                #print("JSON SHOP: %s %s" %  (this_jsons, len(this_jsons)))
    except:
        return False
    #    print("Except %s" % e)
    #    return False
    
    return custom_json

class Command(BaseCommand):
    help = 'Copies and assemles all folders/subfolders necessary to start production of an order (and all containing products)'

    def add_arguments(self, parser):
        
        group = parser.add_mutually_exclusive_group()
        group.add_argument('-o', '--order_id', type=str, help="Order ID to be created/checked")
        group.add_argument('-op', '--order_product_id', type=str, help="The ID of the OrderProduct to create/check")
        
        # Named (optional) arguments
        parser.add_argument(
            '--create',
            action='store_true',
            help='This creates the folder structure for the base',
        )
        
    #internal recursive funtion to copy project data
    #if symlink=True only symlinks will be created instead of a hard copy (NOTE: NOT FUNCTIONAL YET!)
    def _dup_folder(self, source, dest,symlink=False):
            
        if os.path.isdir(source):
            #check if already exits
            if not os.path.isdir(dest):
                os.mkdir(dest)
                self.stdout.write("mkdir %s" % dest)
            
        self.stdout.write("Source\t%s" % source)
        for item in os.listdir(source):
            s = os.path.join(source, item)
            d = os.path.join(dest, item)

            #d = d.replace(fsin, fsinnew)
            if os.path.isdir(s):
                #this is a directory make a recursive call
                self.stdout.write("is dir %s" % s)
                self._dup_folder(s, d)
            else:
                #copy file
                if symlink:
                    #os.symlink(s, d) # create symlink
                    #os.system('mklink %s %s' %(d, s)) # not working
                    shutil.copyfile(s,d) # create hard copy
                    #_winapi.CreateJunction(s, d)
                else:
                    shutil.copyfile(s,d) # create hard copy
                self.stdout.write("copy\t %s %s" % (s, d))
            #self.stdout.write(".", end='')

    # This functions receives a QuerySet and checks or creates the OrderdProduct according to the createFlad
    def assembleOrderProduct(self, product, createFlag):
        if not product:
            return False
        
        #init
        intakes = None
        json_file = ''
        custom_json = ''
        this_order = product.order
        #
        # Assemble the needed folders
        #
        if not product.product.check_online():
            self.stdout.write("[ERROR] Product offline.\nShould be this folder %s and this project file %s" % (product.product.get_folder(), product.product.get_project_file_name()))
            return False
        
        product_folder = product.product.get_folder() #this is the shelf folder of the product
        full_base_path = Path(SHOP_FOLDER) / SHOP_SHELF_FOLDER  / product.product.base.get_folder() 
        order_folder = product.product.get_folder()
        full_product_path = Path(SHOP_FOLDER) / SHOP_SHELF_FOLDER  / product.product.base.get_folder() / order_folder
        order_target_path = Path(SHOP_FOLDER) / SHOP_ORDER_FOLDER / product.get_folder()

        self.stdout.write(">Checking of product folder [%s] exists in\t%s\t\n" % (product_folder, SHOP_SHELF_FOLDER))
        self.stdout.write("\t\t\tfull path:\t%s" % full_product_path)
        self.stdout.write(">This will be the order target path:\t%s" % order_target_path)

        #
        # Asset folders
        # 
        base_asset_folder = full_base_path / SHOP_DEFAULT_ASSETS_FOLDER
        target_asset_folder = order_target_path / SHOP_DEFAULT_ASSETS_FOLDER

        product_asset_folder = full_product_path / SHOP_DEFAULT_ASSETS_FOLDER
        target_product_asset_folder = order_target_path / SHOP_DEFAULT_ASSETS_FOLDER

        product_file = full_product_path / product.product.get_project_file_name(True)

        #
        # Debug output
        #
        self.stdout.write("\n>ASSET Folders (ProductBase)\t\t%s" % base_asset_folder )
        self.stdout.write("\t->TO:\t\t\t\t%s" % target_asset_folder)
        self.stdout.write(">ASSET Folders (Product)\t\t%s" % product_asset_folder )
        self.stdout.write("\t->TO:\t\t\t\t%s" % target_product_asset_folder)
        self.stdout.write("\tPRODUCT FILE:\t\t\t%s" % product_file)

        self.stdout.write(">Available Client Assets: ")
        clients_ci_path = Path(SHOP_FOLDER) / Path(SHOP_CLIENT_CI_FOLDER) 
        client_ci_path = clients_ci_path / product.order.client.get_folder()
        self.stdout.write("\tPath:\t\t\t\t%s" % client_ci_path)

        #
        # Checks
        #

        #check if product path exists
        if os.path.isdir(full_product_path):
            self.stdout.write("Product Folder exists")
        else:
            self.stdout.write(self.style.ERROR('[ERROR] product folder: %s does not exit!' % full_product_path))
            if createFlag:
                self.stdout.write("Cannot continue. Please make sure products exist before retrying")
                return False

        #check if actual product file exists
        if os.path.isfile(product_file):
            self.stdout.write("Product file exits [%s]" % product_file)
        else:
            self.stdout.write(self.style.ERROR('[ERROR] product file: %s does not exit!' % product_file))
            if createFlag:
                self.stdout.write("Cannot continue. Please make sure products file exist before retrying")
                return False

        #let's check if the client ci path exists
        if os.path.isdir(client_ci_path):
            self.stdout.write(self.style.WARNING('>[CHECK]\tClient CI path exits!'))
        else:
            #let's see if we find the ID
            client_pattern = '*' + "{0:0=4d}".format(product.order.client.id) + '*'
            d = clients_ci_path
            #d = '.'
            dir_list = [os.path.join(d, o) for o in os.listdir(d) 
                                if os.path.isdir(os.path.join(d,o))]
            # self.stdout.write("\tAvailable directories:\t\t%s" % dir_list)
            self.stdout.write("\tLooking for:\t\t\t%s" % client_pattern )
            #x =  dir_list.index(client_id_formatted + '*')
            match = fnmatch.filter(dir_list, client_pattern)
            if match:
                    self.stdout.write(">[CHK]\tClient CI folder found!\t\t%s" % match)
                    client_ci_path = clients_ci_path / match[0]
                    self.stdout.write("\t\t\t\t\t%s" % client_ci_path)
            else:
                    self.stdout.write(">Client CI doesn't exit :/")


        #this part should only cover the copy part as the doorman will make the connection
        #between orders and intakes. if an intake is needed for a product we cannot start production without it
        if product.product.base.needs_intake:
            self.stdout.write(">This product needs files. So we will look for an intake")
            try:
                intakes = Intake.objects.filter(order=product.order)
                self.stdout.write(">[CHECK]\tFound intake for order[%s]!" % product.order)

            except ObjectDoesNotExist:
                self.stdout.write(self.style.ERROR('>[ERROR]\tCould not find intake!'))
                if createFlag:
                    self.stdout.write(
                        "Cannot continue without an intake!")
                    return False

        else:
            self.stdout.write(">This product doesn't need an intake.")

        #
        # ASSET CHECK
        #

        client_asset = {}
        company_asset = {}
        order_product_asset = {}
        copy_list = []
        immaterial_json = {}

        #get a list of all assets the user has available
        for asset in this_order.client.assets.all():
            client_asset[asset.name] = asset.value
            
        for asset in this_order.client.company.assets.all():
            company_asset[asset.name] = asset.value
            
        for asset in product.assets.all():
            order_product_asset[asset.name] = asset.value
            
        #here we write some default values into the json to be used in our products such as name, company, url
        #
        #MISSING
        #

        immaterial_json['URL'] = product.order.client.company.website
        immaterial_json['COMPANY_NAME'] = product.order.client.company.name
        immaterial_json['CLIENT_FIRSTNAME'] = product.order.client.firstname
        immaterial_json['CLIENT_LASTNAME'] = product.order.client.lastname
        
        self.stdout.write("IMMATERIAL_JSON: %s " % immaterial_json)
        self.stdout.write("These are the assets available to this client: %s" % client_asset.items())
        self.stdout.write("These are the assets available to his/her company: %s" % company_asset.items())

        #check if the assets are there.
        # We do this by 1) checking if the asset is already attatched to the OrderProduct 2) checking the client, 3) checking the company 
        
        if product.product.base.assets.all():
            self.stdout.write("Assets needed: ")
            asset_missing = False #flag if we miss one asset

            for asset in product.product.base.assets.all():
                self.stdout.write("\t%s (%s) %s" % (asset.name, asset.assettype, asset.get_filename()))
                # 
                # Checking OrderProduct 
                #

                # TO DO:
                # Get QuerySet from OrderProduct, cross reference and ONLY (!) start looking for assets if the OrderProduct doesn't have them.
                # Then

                if asset.name in order_product_asset:
                    # if it's a file let's see who's the owner
                    if asset.assettype.is_file:
                        print("\t\t\tCHECK FILE! %s %s %s" % (asset.id, asset.client_owner, asset.company_owner))
                        if asset.client_owner:
                            print("CHECK FILE CLIENT!")
                            if asset.exists_client(this_order.client):
                                copy_list.append(asset.get_client_folder(True, this_order.client))  # add to copy list
                                self.stdout.write("[CHECK]\tThe asset %s is available" % asset.name)
                            else:
                                self.stdout.write(self.style.ERROR('[ERROR]\tThe client asset %s is offline!' % asset.name))
                                asset_missing = True
                        elif asset.company_owner:
                            if asset.exists_company(this_order.client.company):
                                copy_list.append(asset.get_company_folder(True,this_order.client.company)) # add to copy list if it's a file
                            else:
                                self.stdout.write(self.style.ERROR('[ERROR]\tThe company asset %s is offline!' % asset.name))
                                asset_missing = True

                    else:
                        immaterial_json[asset.name] = order_product_asset[asset.name]
                        self.stdout.write("[CHECK]\tThe asset %s (%s) is available" % (asset.name, asset.value))
                else:

                    # 
                    # Checking Client 
                    #
                    if asset.name in client_asset:
                        #this is the hot production phase so we really need to make sure this asset exists before continuing:

                        if asset.assettype.is_file:

                            if asset.exists_client(this_order.client):
                                copy_list.append(asset.get_client_folder(True,this_order.client)) # add to copy list
                                self.stdout.write("[CHECK]\tThe asset %s is available" % asset.name)
                            else:
                                self.stdout.write(self.style.ERROR('[ERROR]\tThe asset %s is offline!' % asset.name))
                                asset_missing = True
                        else:
                                asset_value = asset.get_client_value(this_order.client)
                                immaterial_json[asset.name] = asset_value
                                #otherwise we write it into the json

                    else:
                        #if we don't find the asset in the client's assets, let's look at the company
                        #if asset.value in company_asset:

                        # 
                        #    Checking Company 
                        #
                        if asset.name in company_asset:
                            #(asset.name,asset.exists_company(this_order.client.company))) #debug
                            if asset.exists_company(this_order.client.company):

                                if asset.assettype.is_file:
                                    copy_list.append(asset.get_company_folder(True,this_order.client.company)) # add to copy list if it's a file
                                else:
                                    asset_value = asset.get_company_value(this_order.client.company)
                                    #print("ASSET: %s %s" % ( this_asset, this_order.client.company))
                                    immaterial_json[asset.name] = asset_value
                                    #otherwise we write it into the json

                                self.stdout.write("[CHECK]\tOnly the company asset %s is available" % asset.name)
                            else:
                                self.stdout.write(self.style.ERROR('[ERROR]\tThe company asset %s is offline!' % asset.name))
                                asset_missing = True
                        else:
                            self.stdout.write(self.style.ERROR('[ERROR]\tThe asset %s is not available' % asset.name))
                            asset_missing = True

                        #custom_json = processShopJSON(product.json) #this is depreciated
                        #print("DEBUG %s" % custom_json)
                        #if not custom_json:
                        #    self.stdout.write(self.style.ERROR('[ERROR]\tThere is no valid JSON info on the orderproduct!'))
                        #    asset_missing = True #Json is missing!

            if asset_missing and product.product.base.assets:
                self.stdout.write(self.style.ERROR('[ERROR] Assets are missing!'))
                if createFlag:
                    self.stdout.write("Cannot continue. Please make sure the needed assets are there before retrying")
                    return False

            #self.stdout.write("\tThis will be the custom JSON-File: %s" % custom_json)
            #self.stdout.write("\tThis will be the immaterial JSON-File: %s" % immaterial_json)

            self.stdout.write("\tThis will be the copy list: %s" % copy_list)

        
        else:
            self.stdout.write("No assets needed.")

        #DEBUG
        #outfile = 'S:\\TESTS\\ORDERS\\00051_004018__ESTREGGSAE1DE1080W\\ASSETS\\ESTREGGSAE1DE1080W.JSON'
        #write_json_file(custom_json, immaterial_json, outfile)

        #
        # CREATE FOLDER
        # and perform all necessary steps to make this product ready for production
        #
        product_path = product.product.get_folder()
        json_file = Path(order_target_path) / SHOP_DEFAULT_ASSETS_FOLDER / str(product.product.get_project_file_name(False) + ".JSON")

        self.stdout.write("This is the JSON File: %s" % json_file )

        
        if createFlag:
            #make folder
            #os.makedirs(target_path)

            #copy product assets

            ##
            ## MISSING!!! evaluate files and copy them to their new home
            ##
            if not Path(target_product_asset_folder).is_dir():
                    os.makedirs(target_product_asset_folder)

            """
            if Path(product_asset_folder).is_dir():
                if not Path(target_product_asset_folder).is_dir():
                    os.makedirs(target_product_asset_folder)
                    self._dup_folder(product_asset_folder, target_product_asset_folder, False) 
                else:
                    self.stdout.write("Target ASSETS folder already existing")
            else:
                self.stdout.write("Product ASSETS folder not existing")
            """
            if Path(base_asset_folder).is_dir():
                #copy general assets
                self._dup_folder(base_asset_folder,target_asset_folder, False)
            else:
                self.stdout.write("ProductBase ASSETS folder not existing")

            #copy product file
            self.stdout.write("Going to copy [%s] to [%s]" % (product_file, order_target_path ))
            #shutil.copyfile(product_file, order_target_path)
            shutil.copyfile(product_file, os.path.join(order_target_path, os.path.basename(product_file)))


            #self.stdout.write("Copy %s to %s" % (client_ci_path,target_asset_folder ))

            # copying all the files we have assembled in the copy_list:
            for copy_file in copy_list:
                self.stdout.write("Copying file %s" % copy_file)
                shutil.copyfile(copy_file, os.path.join(target_asset_folder, os.path.basename(copy_file)))

            #collect customer individualization
            #for src_file in Path(client_ci_path).glob('*.*'):
            #    shutil.copyfile(src_file, os.path.join(target_asset_folder, os.path.basename(src_file)))
                #shutil.copy(src_file, target_asset_folder) # hard copy


            #os.symlink(src_file, target_asset_folder) # create symlink
            #shutil.copy(client_ci_path, target_asset_folder)

            #
            # Copy Intake
            #
            if intakes and product.product.base.needs_intake:
                i=1
                k=0
                for intake in intakes:
                    k=k+1
                    intake_folder = intake.get_path()
                    target_intake_folder = order_target_path / SHOP_DEFAULT_FOOTAGE_FOLDER
                    target_output_folder = order_target_path / SHOP_ORDER_RENDER_OUTPUT_FOLDER

                    self.stdout.write("\tIntake [%s]:\t\t\t%s -> %s" % (k, intake_folder, target_intake_folder))
                    if not os.path.isdir(target_intake_folder):
                        os.mkdir(target_intake_folder)

                    # create the default output path for the user so he/she knows where to put the final file
                    if not os.path.isdir(target_output_folder):
                        os.mkdir(target_output_folder)
                    #_dup_folder(target_intake_folder,intake_path, False)

                    for src_file in Path(intake_folder).glob('*.*'):
                        shutil.copyfile(src_file, os.path.join(target_intake_folder, os.path.basename(src_file)))
                        i=i+1

                    self.stdout.write("Copied %s files into the footage folder "% i)

                    #k=k+1
                    #files = File.objects.filter(intake=intake.id)
                    #l=1
                    #for file in files:
                    #     self.stdout.write("\tFiles: [%s]:\t\t\t\t\t%s\t%s\t%s" % (l, file.filename, file.filetype, file.size))
                    #    #if options['create']:
                    #    footage_folder_path = order_target_path / SHOP_DEFAULT_FOOTAGE_FOLDER
                    #     self.stdout.write("\t copying to:\t%s" % footage_folder_path)
                    #    l=l+1


            #now we write the json file
            #if json_file and custom_json:
            self.stdout.write('Writing JSON FILE [%s] [%s] [%s]' % (custom_json, immaterial_json, json_file))
            write_json_file(custom_json, immaterial_json, json_file)

            product.write_log('Create_order command collected assets and created the folder structure [%s]' % order_folder)
            product.status = ORDER_PRODUCT_IDLE_STATUS
            product.save()

        #_dup_folder(full_product_path,target_path)
        self.stdout.write(">------------------------------------------------------------------------------------\n")
        
    def handle(self, *args, **options):
        #here comes the code
        
        order_id = options.get('order_id', None)
        order_product_id = options.get('order_product_id', None)
        
        self.stdout.write("\n>This is the Order Creator (Assembler).\n>It assembles all information/data necessary for a given order")
        
        if options['create']:
            self.stdout.write("The create_flag is set so we will perform the complete creation of this product")
        else:
            self.stdout.write("The create_flag is set NOT set so we will just check")
  
        if order_product_id:
            self.stdout.write("Checking if OrderProduct {%s} exits" % order_product_id)
            try:
                product = OrderProduct.objects.get(id=order_product_id)
            except:
                self.stdout.write("OrderProduct {%s} doesn't exist!" % order_product_id)
                return False
            
            self.assembleOrderProduct(product, options['create'])
        elif order_id:
            #collect data
            try:
                this_order = Order.objects.get(pk=order_id)
            except:
                self.stdout.write("This Order doesn't exist!")
                return False
            products = OrderProduct.objects.filter(order=order_id)
            time_created = this_order.created.strftime("%d.%m.%Y - %H:%M")

            #outputs
            self.stdout.write(">==========================================================================================================")
            self.stdout.write(">This Order:\t\t\t%s (created at: %s)" % (this_order.id,time_created))
            self.stdout.write(">Client:\t\t\t%s" % this_order.client)

            self.stdout.write(">Ordered products:")
            self.stdout.write(">------------------------------------------------------------------------------------\n")
            i = 1

            # loop through the OrderProducts and check/create them
            for product in products:
                self.stdout.write(">Product #%s:\t%s\t%s" % (i, product.product.fsin, product.status))
                self.assembleOrderProduct(product, options['create'])
                i = i + 1

            if this_order.status != ORDER_PRODUCT_READY_STATUS:
                self.stdout.write("\n>FYI: in the future I will just create products with status %s (Status is: [%s])" % (ORDER_PRODUCT_READY_STATUS, this_order.status))
            else:
                self.stdout.write("\n>ORDER STATUS: [%s]" % this_order.status)
                this_order.status = ORDER_PRODUCT_ACTIVE_STATUS
                this_order.save()
        self.stdout.write("\n")