#!/usr/bin/env python3

#
# Copyright (c) 2021 Ioanes Sinderman / Filmagio Cine Produktion
#
# Version 0.55
# Date: 27.05.2021
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
#   +) use OrderProduct.assets as priority one and only if assets are missing look at client&company
#
#
# MISSING FEATURES:
# -----------------
#   -) check if order already exists (and task!) to avoid duplication
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

from pathlib import Path, PureWindowsPath
import os
import re
import sys
import json
import fnmatch
import matplotlib.colors
# import _winapi #only works on windows
import shutil

import requests
from tabulate import tabulate

# django librarys
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.core.exceptions import ObjectDoesNotExist
from django.db.models import Q
from django.contrib.auth.models import User
from datetime import datetime
from apps.FileCollector.models import File, Intake, Client, ProjectManager, Company, Order, OrderProduct, \
    ORDER_PENDING_STATUS, ORDER_ACTIVE_STATUS, ORDER_FAILED_STATUS, ORDER_COMPLETE_STATUS, ORDER_DELIVERED_STATUS, \
    ORDER_PRODUCT_PENDING_STATUS, ORDER_PRODUCT_ACTIVE_STATUS, ORDER_PRODUCT_FAILED_STATUS, \
    ORDER_PRODUCT_COMPLETE_STATUS, ORDER_PRODUCT_IDLE_STATUS, ORDER_PRODUCT_READY_STATUS, \
    ORDER_PRODUCT_DELIVERED_STATUS, Video, VIDEO_RENDERING, ORDER_PRODUCT_RENDER_STATUS
from apps.FormikoBot.models import Asset, Task, TASK_STATUS_OPEN, TASK_STATUS_COMPLETE, TASK_STATUS_ACTIVE, \
    TASK_STATUS_FAILED
from apps.ProductManager.models import Product, ProductBase, ProductTextModel, Language, Resolution
from django.core.exceptions import ObjectDoesNotExist

# path where all the downloads will be put
SHOP_FOLDER = settings.SHOP_FOLDER  # '/home/worker/Projects/mount/intake'
INTRANET_INTAKE_DRIVE = settings.INTRANET_INTAKE_DRIVE
INTRANET_SHOP_DRIVE = settings.INTRANET_SHOP_DRIVE
SHOP_SHELF_FOLDER = settings.SHOP_SHELF_FOLDER
SHOP_DEFAULT_ASSETS_FOLDER = settings.SHOP_DEFAULT_ASSETS_FOLDER
SHOP_ORDER_FOLDER = settings.SHOP_ORDER_FOLDER
SHOP_CLIENT_CI_FOLDER = settings.SHOP_CLIENT_CI_FOLDER
SHOP_DEFAULT_FOOTAGE_FOLDER = settings.SHOP_DEFAULT_FOOTAGE_FOLDER
SHOP_ORDER_RENDER_OUTPUT_FOLDER = settings.SHOP_ORDER_RENDER_OUTPUT_FOLDER

BOT_ASSEMBLER_USERNAME = settings.BOT_ASSEMBLER_USERNAME
BOT_LASTNAME = settings.BOT_LASTNAME

# global variables
copy_list = []


# creating the doorman user
def create_assembler_user():
    assembler_user = User.objects.create_user(username=BOT_ASSEMBLER_USERNAME, email='assembler@formikaro.io',
                                              password='4ss3mbler!', first_name=BOT_ASSEMBLER_USERNAME,
                                              last_name=BOT_LASTNAME)
    assembler_user.save()
    return assembler_user


# see if the doorman user is present if not call the create function to create a user and it's projectmanager
def check_assembler_pm():
    # doorman = User.objects.filter(username='doorman')
    try:
        assembler_pm = ProjectManager.objects.get(firstname=BOT_ASSEMBLER_USERNAME)
    except:
        assembler_user = create_assembler_user()
        assembler_pm = ProjectManager.objects.get(firstname=BOT_ASSEMBLER_USERNAME)

    return assembler_pm


# this will take the custom_json for this product and append all general information like colors and fonts to it
def write_json_file(custom_json, immaterial_json, json_file):
    # check if there is a custom_json. if not leave it empty
    try:
        json.loads(custom_json)
    except:
        custom_json = {}

    combined_json = {**custom_json, **immaterial_json}
    # print("immaterial JSON: %s " % combined_json )

    with open(json_file, 'w') as outfile:
        json.dump(combined_json, outfile)


# small search function for the dictionarys
def search(values, searchFor):
    for k in values:
        for v in values[k]:
            if searchFor in v:
                return k
    return None


# small function to convert the hex color code to a AE friendly array
def hexToHsl(hx):
    if not hx.find('#') != -1:
        hx = '#' + hx

    hls = matplotlib.colors.to_rgba(hx)
    return hls


# def hexToRgb(hex):
#    if hex:
#        return tuple(int(hex[i:i + 2], 16) for i in (0, 2, 4))
#    return False

# central function for all asset
def create_asset_json_entry(layerName, property, value, isfile=False):
    asset_data = {"type": "data"}

    if isfile:
        # {
        #    "src": "file:///\\LOBO/SHOP/CLIENT_CI/GLOBAL/LOGO_1920_SQUARE.png",
        #    "type": "image",
        #    "layerName": "PICTURE_1"
        # },
        asset_data['src'] = 'file:///' + str(value)
        asset_data['type'] = 'image'  # for now we assume every file is an imagefile
        asset_data['layerName'] = layerName
    else:
        asset_data['layerName'] = layerName
        asset_data['property'] = property

        # if the first 5 letters of the layername are COLOR then we assume a color value

        if property.find('COLOR') != -1:
            # print("layer: %s" % layerName)
            # print("VALUE %s" % value)
            # print("prop %s" % property)
            if value:
                value = hexToHsl(value)
                # value = colorsys.rgb_to_hls(value)
            else:
                value = 0
        else:
            value = value

        asset_data['value'] = value

    return asset_data


# this function is tailored to read the output of the shop api (FOVO) and convert it into a simple text array TEXT_1, TEXT_2,..

def processShopJSON(shop_json):
    if not shop_json:
        return False

    this_json = {}
    # raw_json = str(shop_json)
    # raw_json = raw_json.replace("\'", "\"")
    # raw_json = raw_json.replace("null", "\"null\"") # this is a hack! the api should deliver json conform values instead
    # raw_json = raw_json.replace("None", "\"None\"")

    # self.stdout.write("JSON;", raw_json)
    # print("DEBUG INSIDE")
    # this_jsons = json.loads(raw_json)

    try:
        # this_json = {}
        # raw_json = str(shop_json)
        # raw_json = raw_json.replace("\'", "\"")
        # raw_json = raw_json.replace("null", "\"null\"") # this is a hack! the api should deliver json conform values instead
        # raw_json = raw_json.replace("None", "\"None\"")

        # self.stdout.write("JSON;", raw_json)
        # print("DEBUG INSIDE")
        this_jsons = shop_json  # json.loads(raw_json)

        custom_json = {}
        k = 0

        # print("[JSON!] Going for JSON")
        for i in range(len(this_jsons)):

            label = this_jsons[i]['label'].upper()

            # print("\tYYY %s\t%s" % (i, label)) #debug
            # self.stdout.write("\t\tlabel: %s" % label)

            if label.find('RESOLUTION') == -1 and label.find('AUFLÖSUNG') == -1:
                key = "TEXT_" + str(k + 1)
                # print("\t\t[JSON] LABEL [%s] KEY [%s]" % (label, key))
                custom_json[key] = {}

                # custom_json[k][key] =
                # here should be also the check for lenght, format and code we don't want in our aftereffect to be injected
                custom_json[key] = this_jsons[i]['value']
                k = k + 1
                # self.stdout.write("\t\tJSON label: %s  value %s " % (this_jsons[i]['label'], this_jsons[i]['value']))
            # else:
            # print("JSON SHOP: %s %s" %  (this_jsons, len(this_jsons)))
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
        parser.add_argument(
            '--prepare',
            action='store_true',
            help='This checks for all required assets and creates tasks if necessary',
        )
        parser.add_argument(
            '--render',
            action='store_true',
            help='Render Video to AEF',
        )

    # internal recursive funtion to copy project data
    # if symlink=True only symlinks will be created instead of a hard copy (NOTE: NOT FUNCTIONAL YET!)
    def _dup_folder(self, source, dest, symlink=False):

        if os.path.isdir(source):
            # check if already exits
            if not os.path.isdir(dest):
                os.mkdir(dest)
                self.stdout.write("mkdir %s" % dest)

        self.stdout.write("Source\t%s" % source)
        for item in os.listdir(source):
            s = os.path.join(source, item)
            d = os.path.join(dest, item)

            # d = d.replace(fsin, fsinnew)
            if os.path.isdir(s):
                # this is a directory make a recursive call
                self.stdout.write("is dir %s" % s)
                self._dup_folder(s, d)
            else:
                # copy file
                if symlink:
                    # os.symlink(s, d) # create symlink
                    # os.system('mklink %s %s' %(d, s)) # not working
                    shutil.copyfile(s, d)  # create hard copy
                    # _winapi.CreateJunction(s, d)
                else:
                    shutil.copyfile(s, d)  # create hard copy
                self.stdout.write("copy\t %s %s" % (s, d))
            # self.stdout.write(".", end='')

    # this function takes an intakes queryset and an asset and trys to find a file among the intake files that
    # matches the assets
    def match_external_asset(self, intakes, asset):

        if not intakes or not asset:
            self.stdout.write("[ERROR]\tNo intake or assets provided to look for EXAU")
            return False
        self.stdout.write("\tAsset source -> ExternalAuto, trying to find it in the intake")
        if intakes:
            for intake in intakes:
                self.stdout.write("\tFound intake from %s matched to client %s" % (intake.sender, intake.client))
                asset_filename = asset.get_filename()
                self.stdout.write("\tFilename %s (asset id: %s)" % (asset_filename, asset.id))
                if asset_filename:
                    asset_filename_ext = asset.get_extension()  # Path(asset_filename).suffix
                    self.stdout.write('\t[INFO]\tLooking to find asset that matches %s' % (asset_filename))
                else:
                    self.stdout.write('\t[ERROR]\tasset_name not valid %s' % (asset_filename))
                    return False

                for file in intake.files.all().order_by('id'):
                    intake_filename = file.filename
                    intake_filename_ext = Path(file.filename).suffix
                    intake_filename_ext = intake_filename_ext.replace('.', '')

                    # if the files have the same file extentions..
                    # self.stdout.write('%s vs %s' % (asset_filename_ext,intake_filename_ext)) #debug
                    # print("IS %s = %s" % (asset_filename_ext,intake_filename_ext))
                    if asset_filename_ext == intake_filename_ext:
                        self.stdout.write(
                            '\t[CHECK]\tFound an intake file matching the asset file type %s %s (%s)' % (
                                intake_filename, asset_filename, intake_filename_ext))

                        # now we found one so we convert the intake file to an asset file
                        intake_file_path = file.get_path()

                        # create a copy of the intake file
                        target_asset_path = os.path.join(intake.get_folder(True), os.path.basename(asset_filename))
                        target_asset_path_windows = PureWindowsPath(
                            INTRANET_INTAKE_DRIVE) / intake.get_folder() / asset_filename
                        # print("Copy %s to %s" % (intake_file_path, target_asset_path))
                        try:
                            shutil.copyfile(intake_file_path,
                                            target_asset_path)  # we'll make a copy for now even though this isn't completely necessary (just so document this step and preserve the original intake)
                        except Exception as e:
                            self.stdout.write(self.style.ERROR(
                                '[ERROR]\tCould not copy file "%s" to "%s" in intake folder.\n\tError occured: [%s]' % (
                                intake_filename, asset_filename, e)))
                            return False
                        print("WINDOWS path: %s " % target_asset_path_windows)
                        # write intake file information to asset json
                        asset_data = create_asset_json_entry(asset.get_layername(), '', target_asset_path_windows, True)

                        # add it to the copy list
                        # copy_list.append(target_asset_path)  # add to copy list

                        # break; # found it so we can stop looking
                        return asset_data

        else:
            self.stdout.write(
                self.style.ERROR('[ERROR]\tNo intake available to search through so asset %s is offline!' % asset.name))
            return False

    # This functions receives a QuerySet and checks or creates the OrderdProduct according to the createFlag
    def assembleOrderProduct(self, product, createFlag, prepareFlag, renderFlag):
        if not product:
            return False

        # SHOP_FOLDER_WINDOWS = '\\LOBO\SHOP'

        # init
        intakes = None
        json_file = ''
        custom_json = ''
        this_order = product.order
        #
        # Assemble the needed folders
        #
        if not product.product.check_online():
            self.stdout.write("[ERROR] Product offline.\nShould be this folder %s and this project file %s" % (
                product.product.get_folder(), product.product.get_project_file_name()))
            return False

        product_folder = product.product.get_folder()  # this is the shelf folder of the product
        full_base_path = Path(SHOP_FOLDER) / SHOP_SHELF_FOLDER / product.product.base.get_folder()
        order_folder = product.product.get_folder()

        full_product_path = Path(SHOP_FOLDER) / SHOP_SHELF_FOLDER / product.product.base.get_folder() / order_folder
        full_product_path_windows = PureWindowsPath(
            INTRANET_SHOP_DRIVE) / SHOP_SHELF_FOLDER / product.product.get_folder(False)

        # full_product_path_windows = str(INTRANET_SHOP_DRIVE) + str(SHOP_SHELF_FOLDER) + str(product.product.base.get_folder()) + str(order_folder)
        print("FULL PATH WINDOWS %s " % full_product_path_windows)
        my_test = PureWindowsPath(
            INTRANET_SHOP_DRIVE) / SHOP_SHELF_FOLDER
        print("FULL PATH WINDOWS2 %s " % my_test)
        print("FULL PATH WINDOWS3 %s " % product.product.base.get_folder())
        print("FULL PATH INTRA %s " % INTRANET_SHOP_DRIVE)
        order_target_path = Path(SHOP_FOLDER) / SHOP_ORDER_FOLDER / product.get_folder()

        self.stdout.write("Checking of product folder [%s] exists in\t%s\t\n" % (product_folder, SHOP_SHELF_FOLDER))
        self.stdout.write("\t\t\tfull path:\t%s" % full_product_path)
        self.stdout.write("[INFO]\tThis will be the order target path:\t%s" % order_target_path)

        #
        # Asset folders
        #
        base_asset_folder = full_base_path / SHOP_DEFAULT_ASSETS_FOLDER
        target_asset_folder = order_target_path / SHOP_DEFAULT_ASSETS_FOLDER
        product_asset_folder = full_product_path / SHOP_DEFAULT_ASSETS_FOLDER
        target_product_asset_folder = order_target_path / SHOP_DEFAULT_ASSETS_FOLDER

        product_file = full_product_path / product.product.get_project_file_name(True)
        product_file_windows = full_product_path_windows / product.product.get_project_file_name(True)

        #
        # Debug output
        #
        self.stdout.write("\nASSET Folders (ProductBase)\t\t%s" % base_asset_folder)
        self.stdout.write("\t->TO:\t\t\t\t%s" % target_asset_folder)
        self.stdout.write("ASSET Folders (Product)\t\t%s" % product_asset_folder)
        self.stdout.write("\t->TO:\t\t\t\t%s" % target_product_asset_folder)
        self.stdout.write("\tPRODUCT FILE:\t\t\t%s" % product_file)

        self.stdout.write("[INFO]\tAvailable Client Assets: ")
        clients_ci_path = Path(SHOP_FOLDER) / Path(SHOP_CLIENT_CI_FOLDER)
        client_ci_path = clients_ci_path / product.order.client.get_folder()
        self.stdout.write("\tPath:\t\t\t\t%s" % client_ci_path)

        #
        # Checks
        #

        # check if product path exists
        if os.path.isdir(full_product_path):
            self.stdout.write('[INFO]\tProduct Folder exists')
        else:
            self.stdout.write(self.style.ERROR('[ERROR]\tProduct folder: %s does not exit!' % full_product_path))
            if createFlag or renderFlag:
                self.stdout.write('\tCannot continue. Please make sure products exist before retrying')
                return False

        # check if actual product file exists
        if os.path.isfile(product_file):
            self.stdout.write('\tProduct file exits [%s]' % product_file)
        else:
            self.stdout.write(self.style.ERROR('[ERROR]\tProduct file: %s does not exit!' % product_file))
            if createFlag or renderFlag:
                self.stdout.write(
                    self.style.ERROR('[ERROR]\tCannot continue. Please make sure products file exist before retrying'))
                return False

        # let's check if the client ci path exists
        if os.path.isdir(client_ci_path):
            self.stdout.write(self.style.WARNING('[CHECK]\tClient CI path exits!'))
        else:
            # let's see if we find the ID
            client_pattern = '*' + "{0:0=4d}".format(product.order.client.id) + '*'
            d = clients_ci_path
            # d = '.'
            dir_list = [os.path.join(d, o) for o in os.listdir(d)
                        if os.path.isdir(os.path.join(d, o))]
            # self.stdout.write("\tAvailable directories:\t\t%s" % dir_list)
            self.stdout.write("\tLooking for:\t\t\t%s" % client_pattern)
            # x =  dir_list.index(client_id_formatted + '*')
            match = fnmatch.filter(dir_list, client_pattern)
            if match:
                self.stdout.write("[CHECK]\tClient CI folder found!\t\t%s" % match)
                client_ci_path = clients_ci_path / match[0]
                self.stdout.write("\t\t\t\t\t%s" % client_ci_path)
            else:
                self.stdout.write(self.style.ERROR('[ERROR] Client CI doesnt exit!'))

        # this part should only cover the copy part as the doorman will make the connection
        # between orders and intakes. if an intake is needed for a product we cannot start production without it
        if product.product.base.needs_intake:
            self.stdout.write('[INFO]\tThis product needs files. So we will look for an intake')
            intake_missing = False
            try:
                intakes = Intake.objects.filter(order=product.order)
                if intakes:
                    for intake in intakes:
                        self.stdout.write(
                            "[CHECK]\tFound intake from [%s] for order[%s]!" % (intake.sender, product.order))
                else:
                    intake_missing = True
            except ObjectDoesNotExist:
                intake_missing = True

            if intake_missing:
                self.stdout.write(self.style.WARNING('[WARNING]\tCould not find intake!'))
            #    if createFlag:
            #        self.stdout.write(
            #            "Cannot continue without an intake!")
            #        return False
        else:
            self.stdout.write('[INFO]\tThis product doesn\'t need an intake.')

        #
        # ASSET CHECK
        #

        client_asset = {}
        company_asset = {}
        order_product_asset = {}
        immaterial_json = {}
        assets_json = []
        asset_count = 0
        productionReadyFlag = True

        # get assembler user (or create it if it doesn't exist)
        assembler_pm = check_assembler_pm()

        # get a list of all assets the user has available
        # client_asset_qs = this_order.client.assets.all()
        # client_asset_qs.filter()
        # print("DEBUG %s" % client_asset_qs)

        # client_asset_qs = this_order.client.assets.all #TEST
        # OLD:
        # for asset in this_order.client.assets.all():
        #    client_asset[asset.name] = asset.value
        # OLD:
        # for asset in this_order.client.company.assets.all():
        #    #company_asset[asset.name] = asset.value
        #    company_asset[asset.name] = asset.value

        for asset in this_order.client.assets.values():
            client_asset[asset['name']] = asset

        for asset in this_order.client.company.assets.values():
            # company_asset[asset.name] = asset.value
            company_asset[asset['name']] = asset

        for asset in product.assets.values():
            order_product_asset[asset['name']] = asset

        # here we write some default values into the json to be used in our products such as name, company, url
        #
        # MISSING
        #

        immaterial_json['URL'] = product.order.client.company.website
        immaterial_json['COMPANY_NAME'] = product.order.client.company.name
        immaterial_json['CLIENT_FIRSTNAME'] = product.order.client.firstname
        immaterial_json['CLIENT_LASTNAME'] = product.order.client.lastname
        self.stdout.write("--------------------------------------")
        self.stdout.write('IMMATERIAL_JSON: %s' % json.dumps(immaterial_json, indent=4, sort_keys=True))

        # self.stdout.write('\nCLIENT available assets:\n%s' % json.dumps(client_asset, indent=4, sort_keys=True))
        # self.stdout.write('\nCOMPANY available assets:\n%s' %json.dumps( company_asset, indent=4, sort_keys=True))

        # check if the assets are there.
        # We do this by 1) checking if the asset is already attatched to the OrderProduct 2) checking the client, 3) checking the company

        # DEBUG INFO (nicely formated)
        self.stdout.write("ORDERPRODUCT linked assets: ")
        product_base_assets = []
        table_header = ['ID', 'Name', 'Value', 'is_global?']
        for asset in product.assets.all():
            table_row = []
            is_global = True
            if asset.company_owner or asset.client_owner:
                is_global = False
            table_row.append(asset.id)
            table_row.append(asset.name)
            table_row.append(asset.value)
            table_row.append(is_global)

            product_base_assets.append(table_row)

        self.stdout.write(tabulate(product_base_assets, table_header))

        asset_count = product.product.base.assets.count()

        # now we iterate through all the assets that are requires for the production of this product (defined in the
        # productbase) and try to locate them.
        if product.product.base.assets.all():
            self.stdout.write("\nAssets required by ProductBase: ")
            asset_missing = False  # flag if we miss one asset
            i = 0
            for asset in product.product.base.assets.all():
                corresponding_asset = None
                i = i + 1
                self.stdout.write('--------------------------------------------')

                # self.stdout.write("%s (%s) %s" % (asset.name, asset.assettype, asset.get_filename()))
                #
                # Checking OrderProduct
                #

                # TO DO:
                # Get QuerySet from OrderProduct, cross reference and ONLY (!) start looking for assets if the OrderProduct doesn't have them.
                # Then
                # print("#%s/%s: checking %s [ID:[%s][source:[%s]" % (i, asset_count, asset.name, asset.id, asset.source))

                # if the ASSET is attached to the ORDERPRODUCT
                if asset.name in order_product_asset:
                    # self.stdout.write("\tThere is an asset (%s [%s]) matching one linked to the OrderProduct (%s [%s])" % (asset.name, asset.id, order_product_asset[asset.name]['name'], order_product_asset[asset.name]['id']))

                    # if it's a file let's see who's the owner
                    if asset.assettype.is_file:
                        # print("\t\t\tCHECK FILE! %s %s %s" % (asset.id, asset.client_owner, asset.company_owner))

                        # if the source is INTERNAL AUTO, meaning it's already stored in the client ci and can be assigned
                        # automatically..
                        if asset.source == 'INAU':

                            self.stdout.write("\tAsset source -> InternalAuto, trying to assign")
                            # in case the asset linked to the orderproduct has an owner (client or company)...
                            if order_product_asset[asset.name]['client_owner_id'] == this_order.client_id:
                                self.stdout.write(
                                    "\tchecking if assets [%s] for this client %s exists" % (asset, this_order.client))
                                self.stdout.write(
                                    "\tThe asset is available for client [%s]" % asset.exists_client(this_order.client))
                                self.stdout.write("\tThe asset is available for company [%s]" % asset.exists_company(
                                    this_order.client.company))
                                if asset.exists_client(this_order.client):
                                    copy_list.append(
                                        asset.get_client_folder(True, this_order.client))  # add to copy list
                                    # corresponding_asset = asset.get_client_folder(True, this_order.client)  # TO TEST
                                    self.stdout.write("\t[CHECK]\tThe asset %s [%s] is available (linked to the OP)" % (
                                        asset.name, asset.id))

                                    # prepare output for RENDER JSON (file)

                                    asset_data = create_asset_json_entry(asset.get_layername(), asset.get_property(),
                                                                         asset.name,
                                                                         True)
                                    assets_json.append(asset_data)
                                    # ------------------------------

                                elif asset.exists_company(this_order.client.company):
                                    # couldn't find the asset in the client so we'll check if it's available for the company
                                    asset_filename = asset.get_company_folder(True,
                                                                              this_order.client.company, True)

                                    copy_list.append(asset_filename)  # add to copy list if it's a file
                                    # corresponding_asset = asset.get_company_folder(True, this_order.client.company)  # TO TEST
                                    # prepare output for RENDER JSON
                                    asset_data = create_asset_json_entry(asset.get_layername(), asset.get_property(),
                                                                         asset_filename,
                                                                         True)
                                    assets_json.append(asset_data)
                                    # ------------------------------

                                else:
                                    # asset attached to the OrderProduct doesn't exist...
                                    self.stdout.write(
                                        self.style.ERROR('\t[ERROR]\tThe client asset %s is offline!' % asset.name))
                                    asset_missing = True
                            elif order_product_asset[asset.name]['company_owner_id'] == this_order.client.company_id:
                                if asset.exists_company(this_order.client.company):
                                    asset_filename = asset.get_company_folder(True,
                                                                              this_order.client.company, True)
                                    copy_list.append(asset_filename)  # add to copy list if it's a file
                                    # corresponding_asset = asset.get_company_folder(True,this_order.client.company) # TO TEST
                                    # prepare output for RENDER JSON
                                    asset_data = create_asset_json_entry(asset.get_layername(), asset.get_property(),
                                                                         asset_filename,
                                                                         True)
                                    assets_json.append(asset_data)
                                    # ------------------------------
                                else:
                                    self.stdout.write(
                                        self.style.ERROR('\t[ERROR]\tThe company asset %s is offline!' % asset.name))
                                    asset_missing = True
                            else:
                                # in case the asset linked to the orderproduct AND doesn't have a client or company owner...
                                # check if the client has it
                                if asset.exists_client(this_order.client):
                                    asset_filename = asset.get_client_folder(True, this_order.client, True)
                                    copy_list.append(asset_filename)  # add to copy list
                                    # corresponding_asset = asset.get_client_folder(True, this_order.client)  # TO TEST
                                    # self.stdout.write("[CHECK]\tThe asset %s is available" % asset.name)
                                    self.stdout.write(
                                        "\t[CHECK]\tThe asset %s [%s] is available (linked to the OP)" % (
                                            asset.name, asset.id))
                                    # prepare output for RENDER JSON
                                    asset_data = create_asset_json_entry(asset.get_layername(), asset.get_property(),
                                                                         asset_filename,
                                                                         True)
                                    assets_json.append(asset_data)
                                    # ------------------------------
                                else:
                                    self.stdout.write(
                                        '\t[INFO]\tThe asset %s is offline for the client, checking company.' % asset.name)
                                    # asset_missing = True # not yet because we will also check the company
                                # check if the company has it

                                if asset.exists_company(this_order.client.company):
                                    asset_filename = asset.get_company_folder(True,
                                                                              this_order.client.company, True)
                                    copy_list.append(asset_filename)  # add to copy list if it's a file
                                    # corresponding_asset = asset.get_company_folder(True, this_order.client.company) # TO TEST
                                    self.stdout.write(
                                        "\t[CHECK]\tOnly the company asset %s is available filename: (%s) " % (
                                        asset.name, asset_filename))

                                    # prepare output for RENDER JSON
                                    asset_data = create_asset_json_entry(asset.get_layername(), asset.get_property(),
                                                                         asset_filename,
                                                                         True)
                                    assets_json.append(asset_data)
                                    # ------------------------------

                                else:
                                    self.stdout.write(
                                        self.style.ERROR('\t[ERROR]\tThe company asset %s is offline!' % asset.name))
                                    asset_missing = True

                        # if the source is EXTERNAL AUTO, meaning the asset is expected to be brought in by intake
                        elif asset.source == 'EXAU':
                            asset_data = self.match_external_asset(intakes, asset)
                            if asset_data:
                                assets_json.append(asset_data)
                            else:
                                # productionReadyFlag = False
                                asset_missing = True

                    else:
                        # here we are if the asset is not a file
                        # this_asset = client_asset_qs.filter(name=asset.name)
                        # print("\nTHIS ASSET: %s\n" % this_asset)

                        # prepare the json
                        immaterial_json[asset.name] = order_product_asset[asset.name]['value']

                        # prepare output for RENDER JSON
                        asset_data = create_asset_json_entry(asset.get_layername(), asset.get_property(),
                                                             order_product_asset[asset.name]['value'])
                        assets_json.append(asset_data)

                    self.stdout.write("\t[CHECK]\tThe asset %s (%s)[%s] is corresponding to OP asset:\t%s [%s]" % (
                        asset.name, asset.value, asset.id, order_product_asset[asset.name]['name'],
                        order_product_asset[asset.name]['id']))
                    # either file or value this asset is linked to the OrderProduct so it's an original asset
                    corresponding_asset = Asset.objects.get(id=order_product_asset[asset.name]['id'])
                else:

                    #
                    # Checking Client
                    #
                    if asset.name in client_asset:
                        # this is the hot production phase so we really need to make sure this asset exists before continuing:

                        if asset.assettype.is_file:

                            if asset.source == 'INAU':
                                if asset.exists_client(this_order.client):

                                    asset_path = asset.get_client_folder(True, this_order.client, True)
                                    copy_list.append(asset_path)  # add to copy list
                                    asset_data = create_asset_json_entry(asset.get_layername(), '',
                                                                         asset_path, True)
                                    assets_json.append(asset_data)
                                    self.stdout.write("\t[CHECK]\tThe asset %s is available" % asset.name)
                                else:
                                    self.stdout.write(
                                        self.style.ERROR('\t[ERROR]\tThe asset %s is offline!' % asset.name))
                                    asset_missing = True
                            elif asset.source == 'EXAU':
                                asset_data = self.match_external_asset(intakes, asset)
                                if asset_data:
                                    assets_json.append(asset_data)
                                else:
                                    asset_missing = True
                        else:
                            asset_value = asset.get_client_value(this_order.client)
                            immaterial_json[asset.name] = asset_value
                            corresponding_asset = Asset.objects.get(
                                id=client_asset[asset.name]['id'])
                            self.stdout.write(
                                "\t[CHECK]\tThe asset %s (%s)[%s] is corresponding to client asset:\t%s [%s]" % (
                                    asset.name, asset.value, asset.id, client_asset[asset.name]['name'],
                                    client_asset[asset.name]['id']))

                            # prepare output for RENDER JSON
                            asset_data = create_asset_json_entry(asset.get_layername(), asset.get_property(),
                                                                 client_asset[asset.name]['value'])
                            assets_json.append(asset_data)

                    else:
                        # if we don't find the asset in the client's assets, let's look at the company
                        # if asset.value in company_asset:

                        #
                        #    Checking Company
                        #
                        if asset.name in company_asset:
                            # (asset.name,asset.exists_company(this_order.client.company))) #debug
                            if asset.exists_company(this_order.client.company):
                                if asset.source == 'INAU':
                                    if asset.assettype.is_file:
                                        asset_path = asset.get_company_folder(True,
                                                                              this_order.client.company, True)
                                        copy_list.append(asset_path)  # add to copy list if it's a file
                                        asset_data = create_asset_json_entry(asset.get_layername(), '',
                                                                             asset_path, True)
                                        assets_json.append(asset_data)

                                    else:
                                        asset_value = asset.get_company_value(this_order.client.company)
                                        # print("ASSET: %s %s" % ( this_asset, this_order.client.company))
                                        immaterial_json[asset.name] = asset_value
                                        corresponding_asset = Asset.objects.get(
                                            id=company_asset[asset.name]['id'])
                                        self.stdout.write(
                                            "\t[CHECK]\tThe asset %s (%s)[%s] is corresponding to company asset:\t%s [%s]" % (
                                                asset.name, asset.value, asset.id, company_asset[asset.name]['name'],
                                                company_asset[asset.name]['id']))

                                        # prepare output for RENDER JSON
                                        asset_data = create_asset_json_entry(asset.get_layername(),
                                                                             asset.get_property(),
                                                                             asset_value)
                                        assets_json.append(asset_data)

                                    self.stdout.write("\t[CHECK]\tOnly the company asset %s is available" % asset.name)

                                elif asset.source == 'EXAU':
                                    asset_data = self.match_external_asset(intakes, asset)
                                    if asset_data:
                                        assets_json.append(asset_data)
                                    else:
                                        asset_missing = True
                            else:
                                self.stdout.write(
                                    self.style.ERROR('\t[ERROR]\tThe company asset %s is offline!' % asset.name))
                                asset_missing = True
                        else:
                            if asset.source == 'EXAU':
                                # if it's an external asset there is always the intake to look for
                                asset_data = self.match_external_asset(intakes, asset)
                                if not asset_data:
                                    asset_missing = True
                                    self.stdout.write(
                                        self.style.ERROR('\t[ERROR]\tThe asset %s is not available' % asset.name))
                                else:
                                    self.stdout.write(
                                        '[CHECK]\tFound asset %s in the intake (%s' % (asset.name, asset_data))
                                    # asset_data = create_asset_json_entry(asset.get_layername(), asset.get_property(),
                                    #                                     asset.value, True)
                                    assets_json.append(asset_data)
                            else:
                                # if it's an internal asset, it should have been found at this point so we raise an error
                                self.stdout.write(
                                    self.style.ERROR('\t[ERROR]\tThe asset %s is not available' % asset.name))
                                asset_missing = True

                        # custom_json = processShopJSON(product.json) #this is depreciated
                        # print("DEBUG %s" % custom_json)
                        # if not custom_json:
                        #    self.stdout.write(self.style.ERROR('[ERROR]\tThere is no valid JSON info on the orderproduct!'))
                        #    asset_missing = True #Json is missing!

                # TASKS
                # here we create a task that are necessary for the production of this assets
                # if we are creating this thing let's check if all tasks of all assets have been completed

                # if we are creating this OrderProduct we have to check if all tasks related to any of the assets
                # have been completed otherwise we can't produce it
                openTasksFlag = False  # flag to find still open tasks if we create this op

                # if createFlag:

                if corresponding_asset:
                    open_tasks = corresponding_asset.tasks.filter(
                        Q(status=TASK_STATUS_OPEN) | Q(status=TASK_STATUS_FAILED) | Q(status=TASK_STATUS_ACTIVE))
                    for open_task in open_tasks:
                        self.stdout.write(
                            '\t[ERROR] There is still a task (%s) [%s] with status \'%s\' for asset %s [%s]' % (
                                open_task.name, open_task.id, open_task.get_status_display(), corresponding_asset.name,
                                corresponding_asset.id))
                        openTasksFlag = True

                if asset.tasks.exists():
                    self.stdout.write('\t[INFO] Task(s) found to do for this asset:\n')
                    j = 0
                    task_table = []
                    table_header = ['#', 'Task', 'Status']

                    for task in asset.tasks.all():
                        j = j + 1
                        self.stdout.write('\t\t#%s:\t%s' % (j, task))

                        # prepare output (debug)
                        table_row = []
                        table_row.append('#%s' % j)
                        table_row.append(task)
                        table_row.append(task.get_status_display())
                        task_table.append(table_row)

                        # we are just preparing, this is an independent step of creation. If tasks are needed for the production
                        # they will be created here (if they haven't already been)
                        if prepareFlag:
                            # get the assembler user which will be the creator of this tasks
                            task_description = "%s \ncreated by assembler %s" % (task.description, datetime.now())
                            # let's check where to connect this task to:

                            # first check if this tasks already exist:

                            # do one last check if this is a global asset or if this one is already attatched to the client
                            # print("checking if asset (%s) has owners %s %s" % (asset.id, asset.client_owner, asset.company_owner))
                            # if asset.client_owner or asset.company_owner:
                            #  corresponding_asset = asset
                            if corresponding_asset:
                                if corresponding_asset.client_owner or corresponding_asset.company_owner:
                                    # we have an owner so will link directly to this asset but first..
                                    # ..lets see if this hasn't happened already:
                                    if corresponding_asset.tasks.filter(name=task.name):
                                        self.stdout.write(
                                            '\t[INFO] Task (%s) already exists so we won\'t create one' % (task.name))
                                    else:
                                        new_task = Task.objects.create(name=task.name, creator=assembler_pm,
                                                                       description=task_description, mode=task.mode,
                                                                       priority=task.priority, status=TASK_STATUS_OPEN)
                                        new_task.save()
                                        # we just created a task so there is no way we'll be ready for production by the end of this run
                                        productionReadyFlag = False
                                        self.stdout.write('\t[CHECK] Created task %s' % new_task)

                                        self.stdout.write('\t[INFO] Attaching task to asset %s' % corresponding_asset)
                                        corresponding_asset.tasks.add(new_task)
                                        corresponding_asset.save()
                            else:
                                # print("This should be the asset %s" % asset)
                                # this is more tricky: this is a global asset but we have to do some special task for this order product.
                                # in that case we will create a copy of this asset and replace the global asset

                                # we create a new asset and link it to the owner of this order
                                # new_asset = Asset.objects.create(name=asset.name, value=asset.value, assettype=asset.assettype, source=asset.source, maxlength=asset.maxlength,description=asset.description,client_owner=this_order.client)
                                try:
                                    old_asset = product.assets.get(name=asset.name)
                                    product.assets.remove(old_asset.id)
                                    self.stdout.write('\tRemoving asset %s ' % old_asset)
                                except:
                                    self.stdout.write(
                                        '\t[ERROR] Could not find asset %s [%s] attatched to OrderProduct (so it could not be removed)' % (
                                            asset.name, asset.id))

                                corresponding_asset = Asset.objects.create(name=asset.name, value=asset.value,
                                                                           assettype=asset.assettype,
                                                                           source=asset.source,
                                                                           maxlength=asset.maxlength,
                                                                           description=asset.description,
                                                                           client_owner=this_order.client)

                                self.stdout.write(
                                    '\tAdding new asset %s [%s] ' % (corresponding_asset.name, corresponding_asset.id))
                                new_task = Task.objects.create(name=task.name, creator=assembler_pm,
                                                               description=task_description, mode=task.mode,
                                                               priority=task.priority, status=TASK_STATUS_OPEN)
                                new_task.save()

                                # we just created a task so there is no way we'll be ready for production by the end of this run
                                productionReadyFlag = False
                                self.stdout.write('\t[CHECK] Created task %s' % new_task)

                                product.assets.add(corresponding_asset)
                                corresponding_asset.tasks.add(new_task)
                                corresponding_asset.save()
                                product.save()
                                # print("THIS ORDER %s" %  product.assets.filter(name=asset.name))
                                # product.assets # remove the old one
                                # product.assets  # add the new one
                    # self.stdout.write(tabulate(task_table, table_header))
                elif not openTasksFlag:
                    self.stdout.write('\t[INFO] No tasks found for this asset')

            # we cannot create this one if any task on any asset is still open
            if openTasksFlag:
                productionReadyFlag = False

            if asset_missing and product.product.base.assets:
                self.stdout.write(self.style.ERROR('[ERROR]\tAssets are missing!'))
                productionReadyFlag = False
                if createFlag or renderFlag:
                    self.stdout.write(self.style.ERROR(
                        '[ERROR]\tCannot continue. Please make sure the needed assets are there before retrying'))
                    return False

            if not productionReadyFlag and createFlag:
                self.stdout.write(self.style.ERROR(
                    '[ERROR]\tCannot continue. There are open tasks, please finish them before trying again'))
                return False
            if not productionReadyFlag and renderFlag:
                self.stdout.write(self.style.ERROR('[ERROR]\t Not ready for production. No rendering possible yet.'))
                return False

        else:
            self.stdout.write("[INFO]\tNo assets needed.")

        template_json = {"template": {
            "src": "",
            "composition": "FINAL",
            "outputModule": "FOPX_1080",
            "outputExt": "mov"
        }}
        template_json['template']['src'] = 'file:///' + str(product_file_windows)

        postrender_json = {}
        render_json = template_json

        # render_json = { **template_json, **assets_json}
        # render_json.update(template_json)
        # render_json.update()

        order_product_version = Video.objects.filter(order_product_id=product.id).count()
        #oxput
        output_file_path = "{prod_path}/{prod_name}_{ver}.mov".format(
            prod_path= PureWindowsPath(INTRANET_SHOP_DRIVE) / SHOP_ORDER_FOLDER / product.get_folder(absolute=False) / settings.SHOP_ORDER_RENDER_OUTPUT_FOLDER,
            prod_name=product.get_folder(absolute=False),
            ver=order_product_version + 1
        )

        postrender_json = {"actions": {"postrender": [
            {
                "module": "@nexrender/action-copy",
                "output": output_file_path
            }
        ]}}
        render_json['assets'] = assets_json
        render_json = {**render_json, **postrender_json}
        render_json_header = 'curl \
    --request POST \
    --header "nexrender-secret: forender" \
    --header "content-type: application/json" \
    --data \''
        render_json_footer = '\' http://10.0.0.105:3050/api/v1/jobs'
        self.stdout.write('PROTO JSON\n%s%s%s' % (
        render_json_header, json.dumps(render_json, indent=4, sort_keys=True), render_json_footer))

        self.stdout.write("-------------------------------------------------------------------------")
        self.stdout.write('[CHECK]\tFinished checking OrderProduct\n')
        if productionReadyFlag:
            self.stdout.write('[STATUS]\tREADY FOR PRODUCTION\n')
        else:
            self.stdout.write(self.style.ERROR('[ERROR]\tNOT READY FOR PRODUCTION\n'))

        if prepareFlag:
            self.stdout.write(
                '[INFO]\tFinished preparation, setting OrderProduct (%s) status to %s' % (
                    product, ORDER_PRODUCT_IDLE_STATUS))
            product.status = ORDER_PRODUCT_IDLE_STATUS
            product.order.status = ORDER_ACTIVE_STATUS
            product.order.save()
            product.save()
        if renderFlag and productionReadyFlag:
            if product.status == ORDER_PRODUCT_COMPLETE_STATUS:
                self.stdout.write(self.style.ERROR(
                    'ERROR: {}, is marked as COMPLETE. Set STATUS TO IDLE/READY TO REPROCESS IT'.format(
                        product.product.fsin)
                ))
                return False

            url = 'http://{ip_address}/api/v1/jobs'.format(ip_address=settings.NEXRENDER_SERVER_IP)
            nexrender_headers = {'Content-type': 'application/json', 'nexrender-secret': settings.NEXRENDER_SECRET}

            # check if order folder and output subfolder exists
            folder = product.get_folder(absolute=True)
            output_folder = folder / settings.SHOP_ORDER_RENDER_OUTPUT_FOLDER
            if not os.path.isdir(folder):
                os.mkdir(folder)

            if not os.path.isdir(output_folder):
                os.mkdir(output_folder)

            try:
                response = requests.post(url, json=render_json, headers=nexrender_headers)
                if response.status_code != 200:
                    self.stdout.write(self.style.ERROR('ERROR: {}, {}'.format(response.status_code, response.text)))
                else:
                    response_data = json.loads(response.text)
                    job_id = response_data.get('uid', None)
                    previous_version_count = Video.objects.filter(order_product_id=product.id).count()
                    product_name = product.get_folder(absolute=False)
                    unique_fn = "{filename}_{ver}".format(filename=product_name, ver=previous_version_count+1)
                    Video.objects.create(
                        order_product=product, unique_fn=unique_fn, status=VIDEO_RENDERING, renderer_job_id=job_id,
                        version=previous_version_count + 1
                    )
                    product.status = ORDER_PRODUCT_RENDER_STATUS
                    product.save()
                    self.stdout.write(
                            'Job {job_id} Created for Order Prod: {order_prod_id}. Status Set to {status}'.format(
                                job_id=job_id, order_prod_id=product.id, status=ORDER_PRODUCT_RENDER_STATUS
                        )
                    )

            except requests.ConnectionError as error:
                self.stdout.write(self.style.ERROR('[ERROR]\tRENDER SERVER offline'))
                return False
            except Exception as ex:
                self.stdout.write(self.style.ERROR('ERROR: {}'.format(ex)))
                return False

        #
        # CREATE FOLDER
        # and perform all necessary steps to make this product ready for production
        #

        if createFlag and productionReadyFlag:
            self.stdout.write('\nall seems fine so we start...')
            json_file = Path(order_target_path) / SHOP_DEFAULT_ASSETS_FOLDER / str(
                product.product.get_project_file_name(False) + ".JSON")
            self.stdout.write('\n===================================================================')
            self.stdout.write('\n============C-R-E-A-T-I-N-G---O-R-D-E-R-P-R-O-D-U-C-T==============')
            self.stdout.write('\n===================================================================')
            self.stdout.write('\n[INFO]\tORDERPRODUCT PATH %s' % order_target_path)
            self.stdout.write('\n[INFO]\tThis will be the asset copy list: %s' % copy_list)
            self.stdout.write("[INFO]\tThis is the JSON File: %s" % json_file)
            self.stdout.write(
                "[INFO]\tThis is the JSON File's content: %s" % json.dumps(immaterial_json, indent=4, sort_keys=True))

            if Path(product_asset_folder).is_dir():
                if not Path(target_product_asset_folder).is_dir():
                    self.stdout.write("[INFO]\tTarget ASSETS folder will be created and folder duplicated")
                    os.makedirs(target_product_asset_folder)
                else:
                    self.stdout.write("[INFO]\tTarget ASSETS folder already existing")

            # make folder
            # os.makedirs(target_path)

            # copy product assets

            ##
            if not Path(target_product_asset_folder).is_dir():
                os.makedirs(target_product_asset_folder)

                # copy part
                # this forces a hardcopy of all files in the project folder that are not part of the copy_list
                # it seems to be unnessesary as AE will access the project assets even in the shelf folder so no duplication is required
                # i = 1
                # for filename in os.listdir(product_asset_folder):
                #    copy_flag = True
                #    print("checking %s " % filename)
                #    # check if this file is in the copy list
                #    for copy_file in copy_list:
                #        print("checking %s - %s" % (copy_file, filename))
                #        if os.path.basename(copy_file) == filename:
                #            copy_flag = False
                #            break;

                #   if copy_flag:
                #       self.stdout.write("Copying ASSETS file [%s] %s" % (i, filename))
                #       i = i + 1
                #       shutil.copyfile(os.path.join(product_asset_folder, filename),
                #                       os.path.join(target_asset_folder, filename))

                # self._dup_folder(product_asset_folder, target_product_asset_folder, False)
            else:
                self.stdout.write("[INFO]\tProduct ASSETS folder not existing")

            if Path(base_asset_folder).is_dir():
                # copy general assets
                self._dup_folder(base_asset_folder, target_asset_folder, False)
            else:
                self.stdout.write("[INFO]\tProductBase ASSETS folder not existing")

            # copy product file
            self.stdout.write("Going to copy [%s] to [%s]" % (product_file, order_target_path))
            # shutil.copyfile(product_file, order_target_path)
            shutil.copyfile(product_file, os.path.join(order_target_path, os.path.basename(product_file)))

            # self.stdout.write("Copy %s to %s" % (client_ci_path,target_asset_folder ))

            # copying all the files we have assembled in the copy_list:
            for copy_file in copy_list:
                self.stdout.write("Copying file %s" % copy_file)
                shutil.copyfile(copy_file, os.path.join(target_asset_folder, os.path.basename(copy_file)))

            # collect customer individualization
            # for src_file in Path(client_ci_path).glob('*.*'):
            #   shutil.copyfile(src_file, os.path.join(target_asset_folder, os.path.basename(src_file)))
            #   shutil.copy(src_file, target_asset_folder) # hard copy

            # os.symlink(src_file, target_asset_folder) # create symlink
            # shutil.copy(client_ci_path, target_asset_folder)

            #
            # Copy Intake
            #
            if intakes and product.product.base.needs_intake:
                i = 1
                k = 0
                for intake in intakes:
                    k = k + 1
                    intake_folder = intake.get_folder()
                    target_intake_folder = order_target_path / SHOP_DEFAULT_FOOTAGE_FOLDER
                    target_output_folder = order_target_path / SHOP_ORDER_RENDER_OUTPUT_FOLDER

                    self.stdout.write("\tIntake [%s]:\t\t\t%s -> %s" % (k, intake_folder, target_intake_folder))
                    if not os.path.isdir(target_intake_folder):
                        os.mkdir(target_intake_folder)

                    # create the default output path for the user so he/she knows where to put the final file
                    if not os.path.isdir(target_output_folder):
                        os.mkdir(target_output_folder)
                    # _dup_folder(target_intake_folder,intake_path, False)

                    # just copy the whole intake folder to the FOOTAGE folder of the new order...
                    # this is the old way and still in there as backup
                    for src_file in Path(intake_folder).glob('*.*'):
                        shutil.copyfile(src_file, os.path.join(target_intake_folder, os.path.basename(src_file)))
                        i = i + 1

                    self.stdout.write("Copied %s files into the footage folder " % i)

                    # k=k+1
                    # files = File.objects.filter(intake=intake.id)
                    # l=1
                    # for file in files:
                    #     self.stdout.write("\tFiles: [%s]:\t\t\t\t\t%s\t%s\t%s" % (l, file.filename, file.filetype, file.size))
                    #    #if options['create']:
                    #    footage_folder_path = order_target_path / SHOP_DEFAULT_FOOTAGE_FOLDER
                    #     self.stdout.write("\t copying to:\t%s" % footage_folder_path)
                    #    l=l+1

            # now we write the json file
            # if json_file and custom_json:
            self.stdout.write('Writing JSON FILE [%s] [%s] [%s]' % (custom_json, immaterial_json, json_file))
            write_json_file(custom_json, immaterial_json, json_file)

            product.write_log(
                'Create_order command collected assets and created the folder structure [%s]' % order_folder)
            product.status = ORDER_PRODUCT_IDLE_STATUS
            product.save()

        # _dup_folder(full_product_path,target_path)
        self.stdout.write(
            "----------------------------------------END OF ACTION--------------------------------------------\n")

    def handle(self, *args, **options):
        # here comes the code

        order_id = options.get('order_id', None)
        order_product_id = options.get('order_product_id', None)

        self.stdout.write(
            "==========================================================================================================")
        self.stdout.write(
            "====================================A--S--S--E--M--B--L--E--R=============================================")
        self.stdout.write(
            "==========================================================================================================")

        self.stdout.write(
            "\nThis is the Order Creator (Assembler).\nIt assembles all information/data necessary for a given order")

        if options['create']:
            self.stdout.write('[INFO]\tThe create_flag is set so we will perform the complete creation of this order')
        else:
            self.stdout.write('[INFO]\tThe create_flag is set NOT set')

        if options['prepare']:
            self.stdout.write("[INFO]\tThe prepare_flag is set so we will perform the preparation of this order")
        else:
            self.stdout.write('[INFO]\tThe prepare_flag is set NOT set')

        if options['render']:
            self.stdout.write("[INFO]\tThe render flag is set so we will render this order")
        else:
            self.stdout.write('[INFO]\tThe render flag is set NOT set')

        self.stdout.write('[INFO]\tOrderID:\t%s\tOrderProductID:\t%s' % (order_id, order_product_id))

        if order_product_id:
            self.stdout.write("Checking if OrderProduct {%s} exits" % order_product_id)
            try:
                product = OrderProduct.objects.get(id=order_product_id)
            except:
                self.stdout.write("OrderProduct {%s} doesn't exist!" % order_product_id)
                return False

            self.assembleOrderProduct(
                product=product, createFlag=options['create'], prepareFlag=options['prepare'],
                renderFlag=options['render']
            )
        elif order_id:
            # collect data
            self.stdout.write('[CHECK]\tChecking if OrderId {%s} exits' % order_id)
            try:
                this_order = Order.objects.get(pk=order_id)
                self.stdout.write('[CHECK]\tThis Order exist! (%s)' % this_order)
            except:
                self.stdout.write("This Order doesn't exist!")
                return False
            products = OrderProduct.objects.filter(order=order_id)
            time_created = this_order.created.strftime("%d.%m.%Y - %H:%M")
        else:
            # if the assembler is called without any particular ids it will iterate all active orders with OrderProducts status == READY
            orders = Order.objects.all().filter(status=ORDER_ACTIVE_STATUS)
            self.stdout.write('We will check all these orders')
            order_count = 0
            order_product_count = 0
            # print("op %s\n" % orders)
            for order in orders:
                order_count = order_count + 1
                this_order_product_count = 0
                self.stdout.write('\nOrder:\t%s\t\tClient: %s ' % (order.id, order.client))
                self.stdout.write('------------------------------------------------------------------------')
                ordered_products = OrderProduct.objects.all().filter(
                    Q(order=order.id) & Q(status=ORDER_PRODUCT_READY_STATUS))
                for orderproduct in ordered_products:
                    this_order_product_count = this_order_product_count + 1
                    self.stdout.write('\t#%s\t%s\t%s\n' % (this_order_product_count, order.id, orderproduct))

                    # this is a safeguard for now to just prepare projects but not create them
                    if options['prepare']:
                        self.assembleOrderProduct(
                            product=orderproduct, createFlag=False, prepareFlag=options['prepare'],
                            renderFlag=options['render']
                        )
                        # after we are done preparing ste the status to idle (this happens in the assembleOrderProduct function)
                        # orderproduct.status = ORDER_PRODUCT_IDLE_STATUS
                        # orderproduct.save()

                if this_order_product_count == 0:
                    self.stdout.write(
                        '[INFO]\tFound no OrderProducts with status [%s]' % ORDER_PRODUCT_READY_STATUS)
                order_product_count = order_product_count + this_order_product_count
            self.stdout.write('\n[INFO]\tChecked %s orders with %s orderproducts' % (order_count, order_product_count))
            exit(0)

        # outputs
        # self.stdout.write("This Order:\t\t\t%s (created at: %s)" % (this_order.id,time_created))
        # self.stdout.write("CLIENT:\t\t\t%s" % this_order.client)
        """
        self.stdout.write("Ordered products:")
        self.stdout.write("------------------------------------------------------------------------------------\n")
        i = 1


        # loop through the OrderProducts and check/create them
        for product in products:
            self.stdout.write("Product #%s:\t%s\t%s" % (i, product.product.fsin, product.status))
            self.assembleOrderProduct(product, options['create'], options['prepare'])
            i = i + 1

        if this_order.status != ORDER_PRODUCT_READY_STATUS:
            self.stdout.write("\nFYI: in the future I will just create products with status %s (Status is: [%s])" % (ORDER_PRODUCT_READY_STATUS, this_order.status))
        else:
            self.stdout.write("\nORDER STATUS: [%s]" % this_order.status)
            this_order.status = ORDER_PRODUCT_ACTIVE_STATUS
            this_order.save()
        self.stdout.write("\n")
        """
