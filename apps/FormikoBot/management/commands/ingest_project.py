#
# Ingest Project Command
# Formikaro
# V 13.09.21
#
from django.core.management.base import BaseCommand
from django.db.models import Count, Sum, Q

from datetime import datetime
from apps.FileCollector.models import File, Intake, Client, Company, Order, OrderProduct, Project
from apps.ProductManager.models import Product, ProductBase, ProductTextModel, Language, Resolution
from apps.FormikoBot.models import Asset, AssetType, AssetPreset
from tabulate import tabulate
import os
from pathlib import Path
import ntpath


CREATE_ITEM = 'CREATED'
UPDATE_ITEM = 'UPDATED'
INFO_ITEM = 'INFO'
ERROR_ITEM = 'ERROR'
WARNING_ITEM = 'WARNING'

video_file_type = ['mov', 'mp4', 'mxf']

class Command(BaseCommand):

    help = 'Checks a project for consistency and ingests its footage into an intake'

    def add_arguments(self, parser):

        group = parser.add_mutually_exclusive_group()
        group.add_argument('-p', '--project_id', type=str, help="Order ID to be created/checked")
        group.add_argument('-pf', '--project_folder_id', type=str, help="The ID of the OrderProduct to create/check")
        group.add_argument('-list', '--list_project_folders', type=str, help="Lists all project folders on given path")

        # Named (optional) arguments
        parser.add_argument(
            '--ingest',
            action='store_true',
            help='This ingests the found footage into the database',
        )

        parser.add_argument(
            '--try',
            action='store_true',
            help='This only performs a check on the fly. Nothing is written to the database!',
        )

    def parse_project_folder(self, base_folder, project_folder, newIntake, ingestFlag=False):
        #print("basefolder %s %s %s %s" % (base_folder, project_folder, newIntakeId, ingestFlag))
        for item in os.listdir(project_folder):
            s = os.path.join(project_folder, item)

            if os.path.isdir(s):
                # this is a directory make a recursive call
                #self.stdout.write("is dir %s" % s)
                self.parse_project_folder(base_folder, s, newIntake, ingestFlag)
            else:
                # ingest
                filename, file_extension_long = os.path.splitext(s)
                file_size = os.path.getsize(s)
                file_extension = file_extension_long.replace('.','')
                ingest_file_path = os.path.relpath(s,base_folder)
                self.stdout.write('File:\t%s\t(%s) (%s)' % (ingest_file_path, file_size, file_extension))
                if file_extension in video_file_type:
                    #self.stdout.write("ingesting \t %s (%s)" % (s, file_extension))
                    if ingestFlag:

                        # prepare data for DB
                        #new_path = Path(newAbsFilePath) / filename

                        newSize = os.path.getsize(s)
                        newFileType = Path(filename).suffix
                        newFileName = ntpath.basename(filename)

                        # create new File object
                        newFile_in_DB = File(filename=newFileName, filepath=ingest_file_path, filetype=file_extension, size=newSize, created=datetime.now(), intake=newIntake)
                        # save in Database
                        newFile_in_DB.save()
                        newIntake.write_log('Added file (local) [%s] path [%s]' % (newFileName, s))

                        ingest_file_path= os.path.relpath(s, base_folder)
                        self.stdout.write("Ingesting\t %s (%s) (%s) (%s)" % (ingest_file_path, newFileName, file_extension, file_size))


            # self.stdout.write(".", end='')

    def ingest_project(self, project, ingestFlag):
        if not project:
            return False

        #get footage folder:
        project_footage_folder = project.get_footage_folder()
        self.stdout.write('Ingesting project folder:\t%s' % project_footage_folder)
        self.stdout.write('Ingesting project client:\t%s' % project.id)
        if ingestFlag:
            #create new Intake

            newIntake = Intake(sender='local', client=project.client, project=project,
                               created=datetime.now())
            newIntake.save()
            #newIntakeId = newIntake.id
            self.parse_project_folder(project.get_folder(), project_footage_folder, newIntake, ingestFlag)
        else:
            self.parse_project_folder(project.get_folder(), project_footage_folder, False, ingestFlag)

        return True


    def list_folders(self, folder_path):
        if not folder_path: return False
        valid_project = False
        table_header = ['Status', 'Item', 'FolderID', 'Client', 'Title', 'Comment']
        output_table = []

        for item in os.listdir(folder_path):
            table_row = []
            comment = ''
            project_name = ''
            client_name = ''
            s = os.path.join(folder_path, item)

            if os.path.isdir(s):
                # if this is a dir let's see if it starts with the signature 4 digit folder id
                fid = item[0:4]
                if fid.isnumeric():
                    try:
                        project = Project.objects.get(folderid=fid)
                        project_name = project.name
                        client_name = project.client
                        valid_project = True
                    except:
                        valid_project = False
                        comment = 'Folder id not linked to project'
                else:
                    valid_project = False
                    comment = 'No valid folder id'

                if valid_project:
                    table_row.append('[' + INFO_ITEM + ']')
                else:
                    table_row.append('[' + ERROR_ITEM + ']')

                table_row.append(item)
                table_row.append(fid)
                table_row.append(project_name)
                table_row.append(client_name)
                table_row.append(comment)
                output_table.append(table_row)

        self.stdout.write(tabulate(output_table, table_header))

    def output_warning(self):
        self.stdout.write('====================================================')
        self.stdout.write('__          __     _____  _   _ _____ _   _  _____  ')
        self.stdout.write(' \ \        / /\   |  __ \| \ | |_   _| \ | |/ ____|')
        self.stdout.write('  \ \  /\  / /  \  | |__) |  \| | | | |  \| | |  __ ')
        self.stdout.write('   \ \/  \/ / /\ \ |  _  /| . ` | | | | . ` | | |_ |')
        self.stdout.write('    \  /\  / ____ \| | \ \| |\  |_| |_| |\  | |__| |')
        self.stdout.write('     \/  \/_/    \_\_|  \_\_| \_|_____|_| \_|\_____|')
        self.stdout.write('====================================================')

    def yes_or_no(self, question):
        reply = str(input(question + ' (y/n): ')).lower().strip()
        if not reply: return False  # default no

        if reply[0] == 'y':
            return True
        if reply[0].upper() == 'N':
            return False
        else:
            # return self.yes_or_no("Uhhhh... please enter ")
            return False  # default no


    def handle(self, *args, **options):

        ingestFlag = False
        resetFlag = False

        self.stdout.write(
            "==========================================================================================================")
        self.stdout.write(
            "=====================================I-N-G-E-S-T---G-O-B-B-L-E-R==========================================")
        self.stdout.write(
            "==========================================================================================================")

        #assemble asset list
        #new_global_assets = self.generate_global_presets(NUMBER_OF_GLOBAL_ASSETS)
        #new_assets = new_assets + new_global_assets
        #table_header = ['Name', 'Value', 'AssetType', 'Description', 'Source', 'Layer', 'Property', 'Maxlength']
        #new_assets = new_assets_templates + new_global_assets
        #print(tabulate(new_assets, table_header))

        if options['project_id']:
            self.stdout.write('Project ID (Formikaro ID):\t%s' % options['project_id'])
            project = Project.objects.get(id=options['project_id'])
            try:
                self.stdout.write('Valid Project ID\t\t(%s)' % project.name)
            except:
                self.stdout.write('Invalid Project ID')
                exit()

            if project.folderid:
                #self.stdout.write('Folder Project ID (%s)' % project.folderid)
                self.stdout.write('Folder:\t\t\t\t%s' % project.get_folder())
                if options['ingest']:
                    ingestFlag = True
                self.ingest_project(project, ingestFlag)
            else:
                self.stdout.write(self.style.ERROR('[ERROR] There is no folder_id set with this project!'))
                #if not project.fid

        elif options['project_folder_id']:
            self.stdout.write('Found Project ID (Project folder ID): %s' % options['project_folder_id'])

        elif options['list_project_folders']:
            self.stdout.write('Going to check path (%s) if there are any projects ' % options['list_project_folders'])

            self.list_folders(options['list_project_folders'])
                    #self.stdout.write('Found:\t%s\t%s\t%s ' % (item, fid, valid_project))

        #print(tabulate(new_assets, table_header))

        #if options['reset']:
        #    self.stdout.write('Found ResetFlag set so we are going to reset all exiting assets/assettypes to their default values')
        #    resetFlag = True

        #elif options['purge']:
        #    self.output_warning()
        #    self.stdout.write(
        #        'Note: Language and Resolutions cannot be delete through this command only Assets and AssetTypes')
        #    answer = self.yes_or_no('Are you completely sure that you want to delete ALL assets from this system?')
        #    if answer:
        #        self.stdout.write('Ok here we go...')
        #        self.ingest_project()
        #    else:
        #        self.stdout.write('Aborted deletion.')
        #else:
        #    self.ingest_project(options['project_id'])

        # self.stdout.write(('--EOA------------------------------------------')
