#!/usr/bin/env python3

#
# Copyright (c) 2020 Ioanes Sinderman / Filmagio Cine Produktion
#
# Version 0.1
# Date: 12.1.2021
#
# Info for pathlib: https://medium.com/@ageitgey/python-3-quick-tip-the-easy-way-to-deal-with-file-paths-on-windows-mac-and-linux-11a072b58d5f 
#
# checks the integrity of OrderProducts
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

from decouple import config

#django librarys
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.core.exceptions import ObjectDoesNotExist
from datetime import datetime
from apps.FileCollector.models import File, Intake, Client, Company, Order, OrderProduct
from apps.ProductManager.models import Product, ProductBase, ProductTextModel, Language, Resolution
from django.core.exceptions import ObjectDoesNotExist

from formikaro.utils import urlify

#path where all the downloads will be put
SHOP_FOLDER = settings.SHOP_FOLDER
SHOP_SHELF_FOLDER = settings.SHOP_SHELF_FOLDER
SHOP_DEFAULT_ASSETS_FOLDER = settings.SHOP_DEFAULT_ASSETS_FOLDER


#needed for the verification/extraction of email
regex = re.compile(("([a-z0-9!#$%&'*+\/=?^_`{|}~-]+(?:\.[a-z0-9!#$%&'*+\/=?^_`"
                    "{|}~-]+)*(@|\sat\s)(?:[a-z0-9](?:[a-z0-9-]*[a-z0-9])?(\.|"
                    "\sdot\s))+[a-z0-9](?:[a-z0-9-]*[a-z0-9])?)"))


"""
This is the CreateProductBaseFolder function. It is usually called by the user via interface after a ProductBase and it's products 
have been created in the Database. 
It then does:
    -) check if the ProductBase already exists in the SHOP_SHELF_FOLDER. If not:
    -) creates the PB folder and subfolders for all Products. As well as dummyfiles (.txt) for each expected AE/PR file
    
    returns True or False

"""

def CreateProductBaseFolder():
    if not ProductBaseId:
        return False;
    
    #let's see if the product base exists
    print(">>ProductBase Creator")
    print(">Checking input %s", ProductBaseId)
    


class Command(BaseCommand):
    help = 'Creates a product base folder and subfolders for all related products'

    def add_arguments(self, parser):
        parser.add_argument('ProductBase_ids', nargs='+', type=int)
        
        # Named (optional) arguments
        # Named (optional) arguments
        parser.add_argument(
            '--create',
            action='store_true',
            help='This creates the folder structure for the base',
        )
    def handle(self, *args, **options):
        
        #if options['create']:
        #    print(">Create flag set, so this is getting serious")
        
        
        print("\n>This is the ProductBase Builder.\n>It builds the folder structure for any given ProductBase_ID in the shop folder.")
        
        for ProductBase_id in options['ProductBase_ids']:
            try:
                #init data
                sub_folders = []
                file_fillers = {}
                i=0
                
                #collect data
                prod_base = ProductBase.objects.get(pk=ProductBase_id)
                products = Product.objects.filter(base=ProductBase_id).order_by('variety')
                
                #Format for the Products is ID_FSINBASE_NAME
                #productbase =  str(ProductBase_id) + '_' + str(prod_base) + '_' + urlify(prod_base.name)
                productbase = prod_base.get_folder()
                productbase_folder = Path(SHOP_FOLDER) / SHOP_SHELF_FOLDER / productbase
                
                #outputs
                print(">==========================================================================================================")
                print(">\t\t\t\tFSIN\t\t\tVARIETY\tVERSION\tLANG\tRES\tRUNTIME\tCREATED")
                print(">Base FSIN:\t\t\t%s" % prod_base)
                for product in products:
                    time_created = product.created.strftime("%d.%m.%Y - %H:%M")
                    if not product.fsin:
                        fsin = '---- NO FSIN ----'
                    else:
                        fsin = product.fsin
                    
                    if len(fsin)<16:
                        tab_corr = "\t"
                    else:
                        tab_corr = ""
                        
                    print(">\tRelated Product:\t%s%s\t%s\t%s\t%s\t%s\t%s\t%s" % (fsin, tab_corr, product.variety, product.version, product.language, product.resolution, product.runtime, time_created))
                    
                    #sub_folder = str(product.language) + str(product.variety) + str(product.version)
                    sub_folder = product.get_folder()
                    sub_folder = sub_folder.upper()
                    
                    #if we haven't already registered this subfolder
                    if not sub_folder in sub_folders:
                        sub_folders.append(sub_folder)
                        i=0
                        file_fillers[sub_folder] = {}
                    else: 
                        i=i+1
                    
                    if product.fsin:
                        fsin = str(product.fsin)
                    else:
                        fsin = 'FILLER' #for now we create fillers but there should be a check first and then we decide if we create an empty project anyway
                    file_fillers[sub_folder][i] = fsin
                    
                    
                
                print("\n")
                #if we are really creating this folders...
                if options['create']:
                #let's do it
                    #befor we can do this, let's see if the folder already exists..
                    if os.path.exists(productbase_folder):
                        print(">ERROR: Could not create folder %s because it already exists!" % productbase_folder)    
                    else:
                        #ok now we try to build it.
                        try:
                            os.makedirs(productbase_folder) #don't really need this if there are subdirs as os.makedirs will create it anyway, but if there are not subfolders then we would need it
                            #make assets folder
                            new_assets_folder = productbase_folder / SHOP_DEFAULT_ASSETS_FOLDER
                            os.makedirs(new_assets_folder)
                            #write assets manual
                            assets_file_path =new_assets_folder / 'ASSET_INFO.txt'
                            f = open(assets_file_path, "w")
                            f.write("In this folder belong all files that are used by ALL varieties of product [%s]" % prod_base.name )
                            f.close()
                            
                            print(">CHECK: We created product folder: %s" % productbase_folder)
                            print("Fillers: %s" % file_fillers)
                            for folder in sub_folders:
                                i = 0
                                print("THIS FILLER: ", file_fillers[folder])
                                print("This I: ", i)
                                try:
                                    new_sub_folder = productbase_folder / folder
                                    
                                    #create subfolder
                                    os.makedirs(new_sub_folder)
                                    
                                    #make assets folder for this variety
                                    new_assets_folder = new_sub_folder / SHOP_DEFAULT_ASSETS_FOLDER
                                    assets_file_path = new_assets_folder / 'ASSETS_INFO.txt'
                                    os.makedirs(new_assets_folder)
                                    #write assets manual
                                    f = open(assets_file_path, "w")
                                    print("FOLDER: ", folder)
                                    print("fillers: ", file_fillers[folder][i])
                                    f.write("In this folder belong all files that are ONLY related to the variety [%s] of product [%s]" % (folder, file_fillers[folder][i]) )
                                    f.close()
                                    
                                    print(">CHECK: We created sub folders: %s" % folder )
                                    #print(">FILLERS: ", file_fillers)
                                    i = 0
                                    #print("f", file_fillers[folder])
                                    #print("R",  range(len(file_fillers[folder])))
                                    for i in range(len(file_fillers[folder])):#now we make dummy files for the projects we expect
                                        if prod_base.mode == 'AE':
                                            extention = '.aep'
                                        elif prod_base.mode  == 'PR':
                                            extention = '.prproj'
                                        elif prod_base.mode  == 'FO':
                                            extention = '.fo'
                                        
                                        proto_filler_file = file_fillers[folder][i] + extention
                                        filler_file = proto_filler_file + '.txt'
                                        print("Filler file: ", filler_file)
                                        filler_file_path = new_sub_folder / filler_file
                                        try:
                                            f = open(filler_file_path, "w")
                                            f.write("This is a template file! It remindes you that there should be a file named [%s]" % proto_filler_file)
                                            f.close()
                                        except OSError as e:
                                            print(">ERROR [%s]: Could not create filler file [%s]! " % (e.errno, filler_file_path) )
                                            pass
                                        
                                    
                                except OSError as e:
                                    print(">ERROR [%s]: Could not create folder! " % e.errno)
                                    pass

                        except OSError as e:
                            print(">ERROR [%s]: Could not create folder! " % e.errno)
                            pass
                    
                else:
                    #we just output the possible path and do nothing
                    print("\n>ProductBase Folder would be: %s (folder: %s)" % (productbase_folder, productbase))
                    
                print("\n")
                
            except ProductBase.DoesNotExist:
                raise CommandError('ProductBase ID "%s" does not exist' % ProductBase_id)

           
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        