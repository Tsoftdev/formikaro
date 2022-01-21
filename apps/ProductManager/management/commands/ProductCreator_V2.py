#!/usr/bin/env python3

#
# Copyright (c) 2020 Ioanes Sinderman / Filmagio Cine Produktion
#
# Version 0.2
# Date: 26. 11. 2020 
#
# DESCRIPTION
# Production creator (Class)
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
#
#

from pathlib import Path
import os, shutil
from shutil import copyfile
from datetime import datetime
from os import walk
import re
import sys

SHOP_PRODUCTS_PATH = '/home/pi/Projects/shop/PRODUCTS'
SHOP_PRODUCT_TOKEN = 'FSP'
SHOP_PRODUCT_JSON_TOKEN = 'JS'

regex = re.compile(("([a-z0-9!#$%&'*+\/=?^_`{|}~-]+(?:\.[a-z0-9!#$%&'*+\/=?^_`"
                    "{|}~-]+)*(@|\sat\s)(?:[a-z0-9](?:[a-z0-9-]*[a-z0-9])?(\.|"
                    "\sdot\s))+[a-z0-9](?:[a-z0-9-]*[a-z0-9])?)"))

allowedProductTypes= ['AE' , 'PR', 'HB']
productFiles=['TITLE.txt', 'This file contains the title of product {PRODUCT}',
             'DESC_SHORT.txt', 'This file contains the short description (ca 20 words) of product {PRODUCT}',
             'DESC_LONG.txt', 'This file contains the long description (ca 150 words) of product {PRODUCT}']
class FSP:

    def __init__(self):
        self.data = []    
        print(">CO init"); #DEBUG
    
    def create(prodSystem='',prodJson='',prodName='',prodType='',prodVersion='',prodFsin=''):
        goFlag=True
        prodJsonString=''
        if not prodSystem == '':
            if not prodSystem.upper() in allowedProductTypes:
                    print(">WRONG system token (AE|PR|HB)")
                    goFlag = False;
        else:
            print(">Missing system tolken (AE|PR|HB)")
            goFlag = False;

        if prodName == '':
                print(">Missing product name")
                goFlag = False;
     
        if prodType == '':
                print(">Missing product type")
                goFlag = False;
        
        if prodVersion == '':
                print(">Missing product version")
                goFlag = False;
        
        if prodFsin == '':
                print(">Missing Filmagio Sytem Identification Number (FSIN)")
                goFlag = False;
        else:
            prodFsin = prodFsin.upper();
        if prodJson:
            prodJsonString = 'JS_';
        
        if goFlag:
            print(">Going to create a new product: ")
            
            productName = SHOP_PRODUCT_TOKEN+'_'+prodSystem.upper()+'_'+prodJsonString+prodName+'_'+prodType+'_'+prodVersion+'_'+prodFsin
            print(">", productName);
            eggName = prodFsin+'_EGG'
            productPath = SHOP_PRODUCTS_PATH+'/'+productName
            eggPath = productPath+'/'+eggName
            #does the project already exist?
            if Path(productPath).is_dir():
                print(">Project already exists!");
            else:
                #we checked every parameter and the folder doesn't exist yet so let's create the project
                try:
                    os.mkdir(productPath);
                except OSError:
                    print(">Couldn't create project in", productPath)
                else:
                    
                    #creating the default files as well as the egg folder
                    for x in range(0,len(productFiles),2):
                        f = open(productPath+'/'+productFiles[x], "w")
                        f.write(productFiles[x+1].replace('{PRODUCT}', prodFsin))
                        f.close();
                    try:
                        os.mkdir(eggPath);
                    except OSError:
                        print(">Couldn't create egg folder", eggPath)
                    else:
                        print(">Successfully created egg folder")

                    print(">Successfully created project!")
        else:
            print(">ERROR: Can't create project!");

    def verifyProductFolder(folder=''):
            fsin = ''
            print(">folder: ", folder)
            if not folder: return False    

            pp = re.compile("(FSP)_([A][E]|[P][R]|[H][B])_([J][S])?_?([a-zA-Z0-9]*)_([a-zA-Z]{1,2})_([0-9]+)_([a-zA-Z0-9]{1,8})?")
            productinfo = pp.split(folder)
            print(">", productinfo)
            if len(productinfo) < 4: 
                print(">Invalid folder: ", productinfo[0])
            else:
                if productinfo[1] == SHOP_PRODUCT_TOKEN:
                    print(">Valid product folder")    
                    # count = count + 1
                    if productinfo[2] == "AE":
                        print(">Project Type: After Effects")
                    else:
                        if productinfo[2] == "PR":
                            print(">Project Type: Premiere")
                        else:
                            if productinfo[2] == "HB":
                                print(">Project Type: Hormiga Bot");
                    
                    #perform checks if this is a real FSP here:
                    if productinfo[4]:
                        print(">Name: ", productinfo[4])
                        if productinfo[7]:
                            fsin = productinfo[7];
                            print(">FSIN (Filmagio Standard Identification Number): ", productinfo[7]);
                        else:
                            print(">FSIN missing!");
                #else:
                #    print(">No Name defined! (ERROR)")
                
                
                #perform checks if this is a real FSP here:
                if productinfo[3] == SHOP_PRODUCT_JSON_TOKEN+"_":
                    print(">JSON: active")
                else:
                    print(">JSON: inactive")
                    
                if productinfo[5]: 
                    print(">Type: ",productinfo[5])
                #else:
                #   print(">Type: undefined")
                
                if productinfo[6]: 
                    print(">Version: ",productinfo[6])
                #else:
                #   print(">Version: undefined")
            
            #performing checks of product folders
            #get name of subfolder
            print("product ", folder)

            #productsubfolders = os.listdir(SHOP_PRODUCTS_PATH+'/'+folder)
            #for subfolders in os.listdir(SHOP_PRODUCTS_PATH+'/'+folder):
            #    if os.path.isdir(os.path.join(
            productsubfolders = [filename for filename in os.listdir(SHOP_PRODUCTS_PATH+'/'+folder) if os.path.isdir(os.path.join(SHOP_PRODUCTS_PATH+'/'+folder,filename))] 

            print(">subfolders: ", len(productsubfolders))
            if len(productsubfolders) > 0:
                print(">subfolders seem to exist...");
                #so subfolder exists.. let's see if they are correct
                pathFile = Path(SHOP_PRODUCTS_PATH+'/'+folder+'/TITLE.txt');
                if pathFile.is_file():
                    print(">We have a TITLE.txt");
                else:
                    print(">MISSING: TITLE.txt");

                pathFile = Path(SHOP_PRODUCTS_PATH+'/'+folder+'/DESC_SHORT.txt');
                if pathFile.is_file():
                    print(">We have a DESC_SHORT.txt")
                else:
                    print(">MISSING: DESC_SHORT.txt")
                
                pathFile = Path(SHOP_PRODUCTS_PATH+'/'+folder+'/DESC_LONG.txt');
                if pathFile.is_file():
                    print(">We have a DESC_LONG.txt")
                else:
                    print(">MISSING: DESC_LONG.txt")

                eggPath = Path(SHOP_PRODUCTS_PATH+'/'+folder+'/'+fsin+'_EGG');
                if eggPath.is_dir():
             
                    print(">EGG Path seems to exist: ", fsin+'_EGG');
                    eggPath = SHOP_PRODUCTS_PATH+'/'+folder+'/'+fsin+'_EGG'+'/'+fsin+'_EGG'
                    
                    if productinfo[2] == 'AE':
                        eggPath = eggPath + '.aep';
                        
                    if productinfo[2] == 'PR':
                        eggPath = eggPath + '.prproj';

                    eggPathfile = Path(eggPath)

                    if eggPathfile.is_file():
                        print(">EGG File exists!")
                        return True;
                    else:
                        print(">MISSING: EGG File! Should be: ", eggPathfile);
                else:
                    print(">MISSING EGG! Should be: ", eggPath);
                #for egg in productsubfolders:
                    
                    #check if at least one PRODUCT PIC exits
                 #   print(">eggs: ", egg);

            else:
                print(">Invalid subfolder count!")
                return False;

    #internal recursive funtion to copy project data
    def _dup_folder(source, dest, fsin, fsinnew):
            
        if os.path.isdir(source):
            #check if already exits
            if not os.path.isdir(dest):
                os.mkdir(dest)
                print("mkdir ", dest)
            
        newFSP = FSP
        print("Source ", source)
        for item in os.listdir(source):
            s = os.path.join(source, item)
            d = os.path.join(dest, item)

            #:newFSP._dup_folder(s, d, fsin, fsinnew);
            d = d.replace(fsin, fsinnew)
            if os.path.isdir(s):
                #this is a directory make a recursive call
                #d = d.replace(fsin, fsinnew)
                print("is dir", s)
                newFSP._dup_folder(s, d, fsin, fsinnew)
            else:
                #copy file
                copyfile(s,d)
                print("copy ", s, d)
            print(".", end='')
            #print(f'copy2: \n{s} to \n{d}')
    
    #duplicates the folder of a given FSIN and replaces the FSIN Tag everywhere with the new FSIN
    def duplicateFsin(fsin = '', fsinnew = ''):
        fspTemp = FSP
        Product = fspTemp.verifyFsin(fsin)
        print(">Product, ", Product)
        #productFolder =''.join(map(str+'_', Product))
        productFolder = Product[1]+'_'+Product[2]
        if Product[3]:
            productFolder = productFolder + Product[3]
        
        productFolder = productFolder + '_'+Product[4]+'_'+Product[5]+'_'+Product[6]
        
        productFolderNew = productFolder + '_' + fsinnew
        productFolder = productFolder + '_' + Product[7]
        # productFolder = seperator.join(Product)

        #productFolder = ''.join(Product)
        print(">Product folder", productFolder)
        
        #src = SHOP_PRODUCTS_PATH + '/'+join(Product)
        src = SHOP_PRODUCTS_PATH + '/' + productFolder
        dst = SHOP_PRODUCTS_PATH + '/' + productFolderNew
        if not src: return False;
        if os.path.isdir(dst):
            print(">Folder already exists!")
            return False;

        print(">going to duplicate product ", fsin)
        print(">into: ", dst)
        fspTemp._dup_folder(src, dst, fsin, fsinnew)

        #create a file in the new folder to say that this is a copy
        copyMarkerFile = dst + '/' + '0_THIS_PROJECT_IS_A_COPY.txt'
        print("MAKRERFILE ", copyMarkerFile)
        f = open(copyMarkerFile, 'w')
        MarkerFileText = 'This project is a copy of '+fsin+' created on '+str(datetime.now())+' by the ProjectCreator script'
        f.write(MarkerFileText)
        f.close()
        print(">Finished copying")
        #creating new folder
        #os.mkdir(dst)
        #print(os.getegid())
        #going to copy treee

    #checks if a Fsin exits in the shop folder and then calls verifyProductFolder to check 
    #if this is a valid product
    #PLEASE NOTE: this function doesn't verify the folder by default, it just checks if it exists and
    #if the FSIN is in the right spot
    def verifyFsin(fsin = '', verify=False):
        if not fsin: return False;
        fspTemp = FSP
        foundProduct = False
        if fsin == '': 
            print(">No FSIN given!")
            return False;
        
        productfolders = [filename for filename in os.listdir(SHOP_PRODUCTS_PATH) if os.path.isdir(os.path.join(SHOP_PRODUCTS_PATH, filename))]
        productinfos = []
        #print("productfolder: ", productfolders)
        pp = re.compile("(FSP)_([A][E]|[P][R]|[H][B])_([J][S])?_?([a-zA-Z0-9]*)_([a-zA-Z]{1,2})_([0-9]+)_([a-zA-Z0-9]{1,8})?")
        for productfolder in productfolders:
            productinfo = pp.split(productfolder)
            #print(">> ", productinfo)
            if len(productinfo) >= 8:
                 #print(f'{fsin} = {productinfo}')
                 if fsin == productinfo[7]:
                    #print(">Found FSIN: ", fsin)
                    foundProduct = True
                    break;
                
                
        if foundProduct and verify:
            #verifiying product before sending
            print(">Verify flag == True, verifying product folder")
            return  fspTemp.verifyProductFolder(productfolder)
        elif foundProduct:
            #just sending the Product without verifying
            return productinfo;
        else:
            #didn't find anything
            return False;
            
                    
        
        return False;


def uprint(*objects, sep=' ', end='\n', file=sys.stdout):
    enc = file.encoding
    if enc == 'UTF-8':
        print(*objects, sep=sep, end=end, file=file)
    else:
        f = lambda obj: str(obj).encode(enc, errors='backslashreplace').decode(enc)
        print(*map(f, objects), sep=sep, end=end, file=file)
    
def getProducts(fsin = ''):
    count = 0
    fspTemp = FSP
    if fsin:
        print(f'>FSIN given: {fsin}. Trying to locate product')
        Product = fspTemp.verifyFsin(fsin, True)
        if Product:
            print(">Found product: ", Product)
        else:
            print(">Didn't find any product matching FSIN")
    else:
        print (f'>Checking which products are available in {SHOP_PRODUCTS_PATH}')
        #productfolders = os.listdir(SHOP_PRODUCTS_PATH)
        productfolders = [filename for filename in os.listdir(SHOP_PRODUCTS_PATH) if os.path.isdir(os.path.join(SHOP_PRODUCTS_PATH, filename))]
        print(f'{len(productfolders)} product folders found')
        #print(type(productfolders))
        #pp = re.compile("("+SHOP_PRODUCT_TOKEN+")_("+SHOP_PRODUCT_JSON_TOKEN+"_)?([a-zA-Z0-9]*)_([a-zA-Z]{1,2})_([0-9]+)")
    
        #pp = re.compile("("+SHOP_PRODUCT_TOKEN+")("+SHOP_PRODUCT_JSON_TOKEN+")?(\S+)")
        print(f'Folder found #{len(productfolders)}')
        print("-----------------")
        for productfolder in productfolders:
            #print(">folder: ", productfolder)
            if fspTemp.verifyProductFolder(productfolder):
                count = count + 1;
            #print(productfolder)
            #print(productinfo) ##DEBUG
            print("-----------------")
        
    #for (dirpath, dirnames, filenames) in walk(SHOP_PRODUCTS_PATH):
    #    f.extend(filenames)
    #    print(filenames)
    #    break
    
        print(">Valid Products found: ", count);
    
    return True;

def str2bool(v):
        if isinstance(v, bool):
            return v
        if v.lower() in ('yes', 'true', 't', 'y', '1'):
            return True
        elif v.lower() in ('no', 'false', 'f', 'n', '0'):
            return False
        else:
            raise argparse.ArgumentTypeError('Boolean value expected.')


if __name__ == '__main__':
    from sys import exit
    import argparse
    
    
    ap = argparse.ArgumentParser(
        prog='ProductCreator',
        description='Creating products for the shop.filmagio.com interface'
    )
    sp = ap.add_subparsers(dest='action', help='action')

    # create subcommand
    dp = sp.add_parser('create', help='create product')
    dp.add_argument('-f', type=str, default='', required=True, metavar='Filmagio Standard Identification Number', help='FSIN number')
    dp.add_argument('-s', type=str, default='', required=True, metavar='Used system. Either AE=After Effects, PR=Premiere, HB=Hormiga Bot', help='Product system (AE|PR|HB)')
    dp.add_argument('-t', type=str, default='', required=True, metavar='prodtype', help='Product type')
    dp.add_argument('-j', type=str2bool, nargs='?', const=True, default=False, metavar='If JSON is used for data retrieval', help='JSON active (true|false)')
    dp.add_argument('-v', type=str, default='1', required=True, metavar='Product version', help='Product version')
    dp.add_argument('-n', type=str, default='', required=True, metavar='Product name', help='Product name')

    dup = sp.add_parser('dup', help='duplicate product')
    dup.add_argument('-s', type=str, default='', required=True, metavar='Duplicate FSIN Folder [source]', help='duplicating a given FSIN')
    dup.add_argument('-d', type=str, default='', required=True, metavar='New FSIN [destination]', help='New FSIN Number')
    #dp.add_argument('-o', type=str, default='', metavar='file', help='output file to be used')
    #dp.add_argument('url', nargs='+', type=str, metavar='url',
     #               help='URL (we.tl/... or wetransfer.com/downloads/...)')

    # check subcommand
    up = sp.add_parser('check', help='check if there are new files')
    up.add_argument('-f', type=str, default='', metavar='fsin',
                    help='FSIN number')
    #up.add_argument('-f', type=str, metavar='from', help='sender email')
    #up.add_argument('-t', nargs='+', type=str, metavar='to',
    #                help='recipient emails')
    #up.add_argument('files', nargs='+', type=str, metavar='file',
#                    help='files to upload')

    args = ap.parse_args()

    if args.action == 'create':
        prodNew = FSP
        prodNew.create(args.s, args.j, args.n, args.t, args.v, args.f)
        #print(">", args.prodjson);
        exit(0)

    if args.action == 'dup':
        if args.s and args.d:
            prodNew = FSP
            prodNew.duplicateFsin(args.s, args.d)
            exit(0);

    if args.action == 'check':
        if args.f:
            #prodCheck = FSP;
            #print(prodCheck.verifyFsin(args.f))
            getProducts(args.f)
            exit(0);
        else:
            getProducts(args.f)
            exit(0)

    # No action selected, print help message
    ap.print_help()
    exit(1)
