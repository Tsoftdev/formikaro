# this Formikaro function creates the folder structure needed for the CLIENT_CI based
# on the current database entry. It only creates new folders and doesn't remove existing ones

#system librarys
from pathlib import Path
import os

#django librarys
from django.conf import settings
from django.core.management.base import BaseCommand
from django.core.exceptions import ObjectDoesNotExist
from datetime import datetime

#django models
from apps.FileCollector.models import File, Intake, Client, Company, Order, OrderProduct
from apps.ProductManager.models import Product, ProductBase, ProductTextModel, Language, Resolution
from apps.FormikoBot.models import Asset


#get config variables
SHOP_FOLDER = settings.SHOP_FOLDER
SHOP_CLIENT_CI_FOLDER = settings.SHOP_CLIENT_CI_FOLDER

def init_client_ci(company_id='', create=False):
    print("Starting with the Companies:\n")
    
    if create:
        print("Create flag set going to create the following structure:")
    else:
        print("Create flag not set going to only show the following structure:")
    
    if company_id:
        try:
              
                companies = Company.objects.filter(id=company_id)
            
        except:
                print("Could not find Company (%s)" % company_id)
                return False
      
    else:
        companies = Company.objects.all()

    client_ci_path = Path(SHOP_FOLDER) / SHOP_CLIENT_CI_FOLDER
    
    #check if the base client ci directory exists
    if not client_ci_path.is_dir():
        
        if create:
            print("Client CI_FOLDER [%s] does not exist. Trying to create it..." % client_ci_path)
            try:
                os.makedirs(client_ci_path)
            except OSError as e:
                print("Error [%s] tryting to create [%s]" % (e, client_ci_path))
            else:
                print("Successfully created CLIENT_CI folder!")
        else:
            print("Client CI_FOLDER [%s] does not exist" % client_ci_path)
    else:
        print("Client CI_FOLDER [%s] exists!" % client_ci_path)
        
    #iterate all companies
    for company in companies:
        company_folder = company.get_folder(True)
        print("Checking if company sufolder exist: %s" % company_folder)
        
        if Path(company_folder).is_dir():
            print("Company subfolder [%s] exists." % company_folder)
        else:
            #if the correctly named path doesn't exist, maybe check if it's token has been renamed...
            print("Company subfolder doesn't exits. Trying to locate alternative")
            #let's see if we find the ID
            company_folder_variant = company.get_real_folder(True)
            
            if not company_folder_variant:
                print("Couldn't find company subfolder [%s]" % company_folder)
            
                #if it still doesn't exist and we have the 'create' flag set let's do exactly this..
                if create:
                    print("Company subfolder [%s] does not exist. Trying to create it..." % company_folder)
                    try:
                        os.makedirs(company_folder)
                    except OSError as e:
                        print("Error [%s] tryting to create [%s]" % (e, company_folder))
                    else:
                        print("Successfully created sub folder!")
                        
            else:
                company_folder = company_folder_variant
            #else:
            #    print("Client Company subfolder [%s] does not exist" % company_folder)
        
        company_folder_exists = Path(company_folder).is_dir()
        print("\tFolder:\t%s\t\t\t%s" % (company_folder, company_folder_exists))
       
        #let's see if there are clients to this company
        clients = Client.objects.filter(company=company.id)
        if clients:
            print("\tCompany has the following clients:")
            
            #iterate all clients of a company
            for client in clients:
                client_folder = client.get_real_folder(True)
                print("\t\t%s" % client_folder)
                
                #check if the path already exists
                if Path(client_folder).is_dir() and client_folder:
                    print("Client subfolder [%s] exists." % client_folder)
                else:
                    if create:
                        client_folder = client.get_folder(True)
                        print("Client subfolder [%s] does not exist. Trying to create it..." % client_folder)
                        try:
                            os.makedirs(client_folder)
         
                        except OSError as e:
                            print("Error [%s] tryting to create [%s]" % (e, client_folder))
                            continue
                        else:
                            print("Successfully created client sub folder!")
                    else:
                        print("Client subfolder [%s] does not exist" % client_folder)
                        continue
                    
                # at this point we have created the client folder and now let's write a small text file containing all the assets
                # that should live here
                #client_assets = client.client_owned_assets.all()
                client_assets = client.assets.all()
                
                #client_available_assets = Asset.objects.filter(  Q(company_owner__isnull=True) | Q(company_owner=client.company.id)  ) 
                #companies = ";".join([company.name for company in obj.company_assets.all()])
                #companies = companies if companies else 'None'
                #clients = ";".join([client.get_full_name() for client in obj.client_assets.all()])
                #clients = clients if clients else 'None'
                print("ASSETS: %s " % client_assets)
                asset_intro_text = 'This is a info file for client %s written by the init_client_ci command\nDate: %s\n' % (client, datetime.now())
                asset_intro_text += '\nIt contains a list of all assets that should be in this folder:\n\n'
                additional_info = ''
                asset_info_text = ''
                for asset in client_assets:
                    #print("A: %s" % asset)
                    if asset.assettype.is_file:
                        asset_info_text += asset.get_filename() + '\n'
                    else:
                        additional_info += 'Title: [%s] Value: [%s] ' % (asset.title, asset.value)
                    
                if asset_info_text:
                    asset_info_text= asset_intro_text + asset_info_text
                else: 
                     asset_info_text= asset_intro_text + 'There are no assets linked or defined for this client yet\n'
                    
                if additional_info:
                    additional_info = '\nThese values are stored in the database:\n' + additional_info
                else:
                    additional_info = '\nNo values are stored in the database'
                    
                asset_info_text = asset_info_text + additional_info
                ASSET_INFO_FILE = 'AssetInfo_' + str(client.get_name()) + '.txt'
                asset_info_file = Path(client_folder) / ASSET_INFO_FILE
                print("File text:", asset_info_text) 
                print("File path:", asset_info_file)
                if create:
                    f = open(asset_info_file, "w")
                    f.write(asset_info_text)
                    f.close()
        
        #here goes the company assets info file:
        company_assets = company.assets.all()
        asset_intro_text = 'This is a info file for company %s written by the init_client_ci command\nDate: %s\n' % (company, datetime.now())
        asset_intro_text += '\nIt contains a list of all assets that should be in this folder:\n\n'
        additional_info = ''
        asset_info_text = ''
        for asset in company_assets:
            #print("A: %s" % asset)
            if asset.assettype.is_file:
                asset_info_text += asset.get_filename() + '\n'
            else:
                additional_info += 'Title: [%s] Value: [%s] ' % (asset.title, asset.value)
                    
        if asset_info_text:
            asset_info_text= asset_intro_text + asset_info_text
        else: 
             asset_info_text= asset_intro_text + 'There are no assets linked or defined for this company yet\n'
                
        if additional_info:
            additional_info = '\nThese values are stored in the database:\n' + additional_info
        else:
            additional_info = '\nNo values are stored in the database'
                    
        asset_info_text = asset_info_text + additional_info
        ASSET_INFO_FILE = 'AssetInfo_' + str(company.get_name()) + '.txt'
        asset_info_file = Path(company_folder) / ASSET_INFO_FILE
        print("File text:", asset_info_text) 
        print("File path:", asset_info_file)
        if create:
            f = open(asset_info_file, "w")
            f.write(asset_info_text)
            f.close()
        print("\n")
    


class Command(BaseCommand):
    help = 'Creates the correct folder structur for the CLIENT_CI folder'

    def add_arguments(self, parser):
     
        parser.add_argument('--company', action='append', type=int)
   
        parser.add_argument(
            '--create',
            action='store_true',
            help='This creates the folder structure for the base',
        )
    
    def handle(self, **options):
        
        if options['company']:
            company_id=options['company'][0]
        else:
            company_id = 0
        init_client_ci(company_id, options['create'])
