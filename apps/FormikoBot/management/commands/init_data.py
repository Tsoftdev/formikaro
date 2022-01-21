# v 081021

from django.core.management.base import BaseCommand
from django.db.models import Count, Sum, Q

from datetime import datetime
from apps.FileCollector.models import File, Intake, Client, Company, Order, OrderProduct
from apps.ProductManager.models import Product, ProductBase, ProductText, Language, Resolution
from apps.FormikoBot.models import Asset, AssetType, AssetPreset, TaskType
from tabulate import tabulate

NUMBER_OF_GLOBAL_ASSETS = 5


new_asset_types = [['Color (RGB)',
                    'COLOR',
                    'CONTROL',
                    '',
                    '',
                    'This is a RGB Color asset stored in HEX format RRGGBB',
                    False,
                    6],
                   ['Text (unlimited)',
                    'TEXT',
                    '',
                    'Source Text',
                    '',
                    'This is an unlimited Text Token',
                    False,
                    0],
                   ['Trigger (on/off)',
                    'TRIGGER',
                    'CONTROL',
                    '',
                    '',
                    'This is an boolean trigger',
                    False,
                    1],
                   ['Font name',
                    'FONTNAME',
                    '',
                    'Source Text.font',
                    '',
                    'This is the name of a font without extension',
                    False,
                    40],
                   ['Font file (ttf)',
                    'FONTTTF',
                    '',
                    '',
                    'ttf',
                    'This is a TrueType File name',
                    True,
                    50],
                   ['Font file (otf)',
                    'FONTOTF',
                    '',
                    '',
                    'odf',
                    'This is a OpenType Font File name',
                    True,
                    50],
                   ['PNG File (with Alpha)',
                    'PNGALPHA',
                    '',
                    '',
                    'png',
                    'This is a OpenType Font File name',
                    True,
                    50],
                   ['JPG File (Image)',
                    'JPG',
                    '',
                    '',
                    'jpg',
                    'This is a JPEG image file',
                    True,
                    50],
                   ['AI File (Image)',
                    'AI',
                    '',
                    '',
                    'AI',
                    'This is a AI vector image file',
                    True,
                    50],
                   ['MOV File (Video)',
                    'MOV',
                    '',
                    '',
                    'mov',
                    'This is a MOV video file',
                    True,
                    50],
                   ['MP4 File (Video)',
                    'MP4',
                    '',
                    '',
                    'mp4',
                    'This is a MP4 video file',
                    True,
                    50]]

new_assets_templates = [['Music trigger',
                         'MUSIC_TRIGGER',
                         'TRIGGER',
                         'This is a music trigger (1=on, 0=off)',
                         'EXAU',
                         '',
                         '',
                         ''],
                        ['Logo 1920px Wide + Alpha',
                         'LOGO_1920_WIDE',
                         'PNGALPHA',
                         'desc',
                         'INAU',
                         'LOGO_1920_WIDE',
                         '',
                         ''],
                        ['Logo 1920px Square + Alpha',
                         'LOGO_1920_SQUARE',
                         'PNGALPHA',
                         'desc',
                         'INAU',
                         'LOGO_1920_SQUARE',
                         '',
                         ''],
                        ['Logo 720px Wide + Alpha',
                         'LOGO_720_WIDE',
                         'PNGALPHA',
                         'desc',
                         'INAU',
                         'LOGO_720_WIDE',
                         '',
                         ''],
                        ['Logo 720px Square + Alpha',
                         'LOGO_720_SQUARE',
                         'PNGALPHA',
                         'desc',
                         'INAU',
                         'LOGO_720_SQUARE',
                         '',
                         ''],
                        ['Logo Vector',
                         'LOGO_AI_VECTOR',
                         'AI',
                         'desc',
                         'INAU',
                         'LOGO_AI_VECTOR',
                         '',
                         ''],
                        ['Intro Animation',
                         'CLIENT_INTRO',
                         'MOV',
                         'desc',
                         'INAU',
                         'CLIENT_OUTRO',
                         '',
                         ''],
                        ['Outro Animation',
                         'CLIENT_OUTRO',
                         'MOV',
                         'desc',
                         'INAU',
                         'CLIENT_OUTRO',
                         '',
                         '']]

# these are presets used for
# name
# value
# assettype
# description
# source
# layername
# property
# maxlength


global_asset_preset = [
    ['TEXT_{#}',
     '',
     'TEXT',
     'This is a placeholder for text (#{#})',
     'EXAU',
     'TEXT_{#}',
     '',
     ''],
    ['FONT_{#}',
     '',
     'FONTNAME',
     'This is a placeholder for a font (#{#})',
     'INAU',
     'FONT_{#}',
     '',
     ''],
    ['IMAGE_PNG_{#}',
     'IMAGE_PNG_{#}',
     'PNGALPHA',
     'This is a placeholder for a PNG image file (#{#})',
     'EXAU',
     'IMAGE_PNG_{#}',
     '',
     ''],
    ['IMAGE_JPG_{#}',
     'IMAGE_JPG_{#}',
     'JPG',
     'This is a placeholder for a JPG image file (#{#})',
     'EXAU',
     'IMAGE_JPG_{#}',
     '',
     ''],
    ['COLOR_{#}',
     '',
     'COLOR',
     'This is a placeholder for a hex color value (#{#})',
     'INAU',
     '',
     'Effects.COLOR_{#}.Color',
     ''],
]

new_resolutions = [['720W',
                    1280,
                    720,
                    '1280x720 HD Widescreen'],
                   ['720H',
                    720,
                    720,
                    '1280x720 HD Square'],
                   ['720S',
                    720,
                    1280,
                    '1280x720 HD Portrait'],
                   ['1080W',
                    1920,
                    1080,
                    '1920x1980 FullHD Widescreen'],
                   ['1080H',
                    1080,
                    1920,
                    '1280x720 FullHD Portrait'],
                   ['1080S',
                    1080,
                    1080,
                    '1080x1080 FullHD Square'],
                   ['1080F',
                    1080,
                    1350,
                    '1080x1350 FullHD Feed'],
                   ['1200S',
                    1200,
                    1200,
                    '1200x1200 FullHD Square Extended']
                   ]

new_tasktypes = [['work',
                  'work done'],
                 ['email',
                  'email written to the client'],
                 ['phone',
                  'phone call to the client'],
                 ['info',
                  'general information']
                 ]

CREATE_ITEM = 'CREATED'
UPDATE_ITEM = 'UPDATED'
INFO_ITEM = 'INFO'
ERROR_ITEM = 'ERROR'
WARNING_ITEM = 'WARNING'

class Command(BaseCommand):

    def init_data(self, new_assets, createFlag=True, resetFlag=False):

        table_header = ['Status', 'Item', 'Change', 'ID']
        output_table = []
        table_row = []
        n = Language.objects.filter(abbreviation='en').first()
        if not n:
            if createFlag:
                # self.stdout.write('[INFO]\t\tLanguage English is missing!')
                table_row.append('[' + INFO_ITEM + ']')
                table_row.append('LANGUAGE')
                table_row.append('System language English is missing!')
                table_row.append('')
            else:
                try:
                    n = Language.objects.create(abbreviation='en', name='English', system_language=True)
                    # self.stdout.write('[CREATED]\nNew Language: English [EN]')
                    table_row.append('[' + CREATE_ITEM + ']')
                    table_row.append('LANGUAGE')
                    table_row.append('System lnguage English created! ')
                    table_row.append(n.id)

                except:
                    # self.stdout.write('[ERROR]\nCould not CREATED new Language: English [EN]')
                    table_row.append('[' + ERROR_ITEM + ']')
                    table_row.append('LANGUAGE')
                    table_row.append('Could not create new system language: English [EN]')
                    table_row.append('')

            output_table.append(table_row)  # pretty output table

        else:
            # self.stdout.write('[INFO]\t\tLanguage English is present!')
            table_row.append('[' + INFO_ITEM + ']')
            table_row.append('LANGUAGE')
            table_row.append('Found system language English [EN]')
            table_row.append(n.id)
            output_table.append(table_row)  # pretty output table

        table_row = []
        n = Language.objects.filter(abbreviation='de').first()
        if not n:
            if createFlag:
                # self.stdout.write('[INFO]\t\tLanguage German is missing!')
                table_row.append('[' + INFO_ITEM + ']')
                table_row.append('LANGUAGE')
                table_row.append('System language German is missing!')
                table_row.append('')
            else:
                try:
                    Language.objects.create(abbreviation='de', name='Deutsch', system_language=True)
                    self.stdout.write('[CREATED]\nNew system language: German [DE]')
                except Exception as e:
                    # self.stdout.write('[ERROR]\nCould not CREATED new Language: German [DE]')
                    table_row.append('[' + ERROR_ITEM + ']')
                    table_row.append('LANGUAGE')
                    table_row.append('Could not create new system language: German [DE]. Error: [%s]' % e)
                    table_row.append('')
        else:
            # self.stdout.write('[INFO]\t\tLanguage German is present!')s
            table_row.append('[' + INFO_ITEM + ']')
            table_row.append('LANGUAGE')
            table_row.append('Found system language German [DE]')
            table_row.append(n.id)
        output_table.append(table_row)  # pretty output table

        # Resolutions (CREATED the default ones)
        for new_resolution in new_resolutions:
            table_row = []
            n = Resolution.objects.filter(name=new_resolution[0]).first()
            if not n:
                if createFlag:
                    n = Resolution.objects.create(name=new_resolution[0], width=new_resolution[1],
                                                  height=new_resolution[2], description=new_resolution[3])
                    # self.stdout.write('[CREATED]\nNew Resolution: %s\tID: %s' % (new_resolution[3], n.id))
                    table_row.append('[' + CREATE_ITEM + ']')
                    table_row.append('RESOLUTION')
                    table_row.append('New Resolution: %s ID: %s' % (new_resolution[3], n.id))
                    table_row.append('')

                else:
                    # self.stdout.write('[WARNING]\tResolution: (%s)\t%s is missing!' % (new_resolution[0],new_resolution[3]))
                    table_row.append('[' + WARNING_ITEM + ']')
                    table_row.append('RESOLUTION')
                    table_row.append('%s (%s) is missing!' % (new_resolution[0], new_resolution[3]))
                    table_row.append('')
                output_table.append(table_row)
            else:
                # self.stdout.write('[INFO]\t\tResolution: (%s)\t%s is present' % (new_resolution[0],new_resolution[3]))
                table_row.append('[' + INFO_ITEM + ']')
                table_row.append('RESOLUTION')
                table_row.append('%s (%s) is present' % (new_resolution[0], new_resolution[3]))
                table_row.append(n.id)
                output_table.append(table_row)  # pretty output table

        # task types
        # Resolutions (CREATED the default ones)
        for new_tasktype in new_tasktypes:
            table_row = []
            n = TaskType.objects.filter(name=new_tasktype[0]).first()
            if not n:
                if createFlag:
                    n = TaskType.objects.create(name=new_tasktype[0], description=new_tasktype[1])
                    # self.stdout.write('[CREATED]\nNew Resolution: %s\tID: %s' % (new_resolution[3], n.id))
                    table_row.append('[' + CREATE_ITEM + ']')
                    table_row.append('TASKTYPE')
                    table_row.append('New TaskType: %s ID: %s' % (new_tasktype[0], n.id))
                    table_row.append('')

                else:
                    # self.stdout.write('[WARNING]\tResolution: (%s)\t%s is missing!' % (new_resolution[0],new_resolution[3]))
                    table_row.append('[' + WARNING_ITEM + ']')
                    table_row.append('TASKTYPE')
                    table_row.append('%s (%s) is missing!' % (new_tasktype[0], new_tasktype[1]))
                    table_row.append('')
                output_table.append(table_row)
            else:
                # self.stdout.write('[INFO]\t\tResolution: (%s)\t%s is present' % (new_resolution[0],new_resolution[3]))
                table_row.append('[' + INFO_ITEM + ']')
                table_row.append('RESOLUTION')
                table_row.append('%s (%s) is present' % (new_tasktype[0], new_tasktype[1]))
                table_row.append(n.id)
                output_table.append(table_row)  # pretty output table

        # Asset Type
        for new_asset_type in new_asset_types:
            table_row = []
            n = AssetType.objects.filter(name=new_asset_type[1]).first()
            if not n:
                if createFlag:
                    # self.stdout.write('[CREATED]\tNew Asset Type: %s' % new_asset_type[1])
                    n = AssetType.objects.create(title=new_asset_type[0], name=new_asset_type[1],
                                                 layerName=new_asset_type[2], property=new_asset_type[3],
                                                 extension=new_asset_type[4], description=new_asset_type[5],
                                                 is_file=new_asset_type[6], maxlength=new_asset_type[7])
                    # self.stdout.write('[CREATED]\tNew Asset Type: %s\tID: %s' % (new_asset_type[1], n.id))
                    table_row.append('[' + CREATE_ITEM + ']')
                    table_row.append('ASSETTYPE')
                    table_row.append('New Asset Type: %s' % (new_asset_type[1]))
                    table_row.append(n.id)

                else:
                    # self.stdout.write('[WARNING]\tAssetType %s is missing!' % new_asset_type[0])
                    table_row.append('[' + WARNING_ITEM + ']')
                    table_row.append('ASSETTYPE')
                    table_row.append('AssetType %s is missing!' % new_asset_type[0])
                    table_row.append('')

                output_table.append(table_row)  # pretty output table
            else:
                if resetFlag:
                    # self.stdout.write('[INFO]\t\tAssetType: (%s) is present' % (new_asset_type[0]))
                    u = AssetType.objects.filter(id=n.id).update(title=new_asset_type[0], name=new_asset_type[1],
                                                                 layerName=new_asset_type[2], property=new_asset_type[3],
                                                                 extension=new_asset_type[4], description=new_asset_type[5],
                                                                 is_file=new_asset_type[6], maxlength=new_asset_type[7])

                    table_row.append('[' + UPDATE_ITEM + ']')
                    table_row.append('ASSETTYPE')
                    table_row.append('AssetType: (%s) reset to default values' % (new_asset_type[0]))
                    table_row.append(u)
                else:
                    # self.stdout.write('[INFO]\t\tAssetType: (%s) is present' % (new_asset_type[0]))
                    table_row.append('[' + INFO_ITEM + ']')
                    table_row.append('ASSETTYPE')
                    table_row.append('AssetType: %s (%s) is present' % (new_asset_type[1], new_asset_type[0]))
                    table_row.append(n.id)

                output_table.append(table_row)  # pretty output table

        # assets

        for new_asset in new_assets:
            table_row = []

            # CREATE ASSETPRESETS
            #print("CHECKING NA %s" % new_asset[1])
            # only create presets for global assets

            # if the value is empty we create a preset if not this are the base assets that don't need presets so we don't create them
            if new_asset[1] == '':

                this_assetpreset = AssetPreset.objects.filter(title=new_asset[0]).first()
                if not this_assetpreset:
                    if createFlag:
                        try:
                            # create preset
                            this_type = AssetType.objects.get(name=new_asset[2])
                            if new_asset[7]:
                                this_maxlength = int(str(new_asset[7]))
                            else:
                                this_maxlength = None
                            this_assetpreset = AssetPreset.objects.create(title=new_asset[0], name=new_asset[0], value=new_asset[1],
                                                                          assettype=this_type,
                                                                          description=new_asset[3], source=new_asset[4], layerName=new_asset[5],
                                                                          property=new_asset[6], maxlength=this_maxlength)
                            table_row.append('[' + CREATE_ITEM + ']')
                            table_row.append('ASSETPRESET')
                            table_row.append('New AssetPreset: %s' % (new_asset[1]))
                            table_row.append(this_assetpreset.id)
                        except Exception as e:
                            # self.stdout.write('[ERROR]\tAssetType (%s) needed for this Asset %s is missing! Skipping' % (new_asset[2], new_asset[0]))
                            table_row.append('[' + ERROR_ITEM + ']')
                            table_row.append('ASSETPRESET')
                            table_row.append('Can\'t create AssetPreset (%s) Error [%s]' % (new_asset[0], e))
                            table_row.append('')
                    else:
                        # self.stdout.write('[WARNING]\tAsset %s is missing!' % new_asset[0])
                        table_row.append('[' + WARNING_ITEM + ']')
                        table_row.append('ASSETPRESET')
                        table_row.append('AssetPreset %s is missing!' % new_asset[0])
                        table_row.append('')
                else:
                    if resetFlag:
                        # self.stdout.write('[INFO]\t\tAssetType: (%s) is present' % (new_asset_type[0]))
                        try:
                            this_type = AssetType.objects.get(name=new_asset[2])

                            if new_asset[7]:
                                this_maxlength = int(str(new_asset[7]))
                            else:
                                this_maxlength = None
                            try:
                                u = AssetPreset.objects.filter(id=this_assetpreset.id).update(title=new_asset[0], name=new_asset[0], value=new_asset[1],
                                                                                              assettype=this_type,
                                                                                              description=new_asset[3], source=new_asset[4], layerName=new_asset[5],
                                                                                              property=new_asset[6], maxlength=this_maxlength)
                                table_row.append('[' + UPDATE_ITEM + ']')
                                table_row.append('ASSETPRESET')
                                table_row.append('AssetPreset: (%s) reset to default values' % (new_asset[0]))
                                table_row.append(this_assetpreset.id)
                            except Exception as e:
                                table_row.append('[' + ERROR_ITEM+ ']')
                                table_row.append('ASSETPRESET')
                                table_row.append('Error updating (%s). Error: %s' % (new_asset[0], e))
                                table_row.append(this_assetpreset.id)
                        except Exception as e:
                            table_row.append('[' + ERROR_ITEM+ ']')
                            table_row.append('ASSETPRESET')
                            table_row.append('Error updating (%s). Error: %s' % (new_asset[0], e))
                            table_row.append(this_assetpreset.id)
                    else:
                        # self.stdout.write('[INFO]\t\tAsset: (%s) is present' % (new_asset[0]))
                        table_row.append('[' + INFO_ITEM + ']')
                        table_row.append('ASSETPRESET')
                        table_row.append('%s is present' % (new_asset[0]))
                        table_row.append(n.id)
            else:
                # self.stdout.write('[INFO]\t\tAsset: (%s) is present' % (new_asset[0]))
                table_row.append('[' + INFO_ITEM + ']')
                table_row.append('ASSETPRESET')
                table_row.append('no preset created for %s (base asset)' % (new_asset[0]))
                table_row.append('')

            output_table.append(table_row) # new line
            table_row = []

            # CREATE ASSETS
            n = Asset.objects.filter(name=new_asset[0]).first()
            if not n:
                if createFlag:
                    try:
                        this_type = AssetType.objects.get(name=new_asset[2])
                        if new_asset[7]:
                            this_maxlength = int(str(new_asset[7]))
                        else:
                            this_maxlength = None
                        n = Asset.objects.create(name=new_asset[0], value=new_asset[1], assettype=this_type,
                                                 description=new_asset[3], source=new_asset[4], layerName=new_asset[5],
                                                 property=new_asset[6], maxlength=this_maxlength)

                        #self.stdout.write('[CREATED]\tNew Asset: %s\tID:%s' % (new_asset[1], n.id))
                        table_row.append('[' + CREATE_ITEM + ']')
                        table_row.append('ASSET')
                        table_row.append('New Asset: %s' % (new_asset[0]))
                        table_row.append(n.id)


                    except Exception as e:
                        # self.stdout.write('[ERROR]\tAssetType (%s) needed for this Asset %s is missing! Skipping' % (new_asset[2], new_asset[0]))
                        table_row.append('[' + ERROR_ITEM + ']')
                        table_row.append('ASSET')
                        table_row.append('AssetType (%s) needed for this Asset %s is missing! Skipping. Error: [%s]' % (
                            new_asset[2], new_asset[0], e))
                        table_row.append('')

                    output_table.append(table_row)
                else:

                    # self.stdout.write('[WARNING]\tAsset %s is missing!' % new_asset[0])
                    table_row.append('[' + WARNING_ITEM + ']')
                    table_row.append('ASSET')
                    table_row.append('Asset %s is missing!' % new_asset[0])
                    table_row.append('')

                output_table.append(table_row)  # pretty output table
            else:
                if resetFlag:
                    # self.stdout.write('[INFO]\t\tAssetType: (%s) is present' % (new_asset_type[0]))
                    try:
                        this_type = AssetType.objects.get(name=new_asset[2])

                        if new_asset[7]:
                            this_maxlength = int(str(new_asset[7]))
                        else:
                            this_maxlength = None
                        # only reset global assets
                        u = Asset.objects.filter(Q(id=n.id) & Q(client_owner__isnull=True) & Q(company_owner__isnull=True)).update(name=new_asset[0], value=new_asset[1], assettype=this_type,
                                                                                                                                   description=new_asset[3], source=new_asset[4], layerName=new_asset[5],
                                                                                                                                   property=new_asset[6], maxlength=this_maxlength)
                        table_row.append('[' + UPDATE_ITEM + ']')
                        table_row.append('ASSET')
                        table_row.append('Asset: (%s) reset to default values' % (new_asset[0]))
                        table_row.append(n.id)
                    except Exception as e:
                        # self.stdout.write('[ERROR]\tAssetType (%s) needed for this Asset %s is missing! Skipping' % (new_asset[2], new_asset[0]))
                        table_row.append('[' + ERROR_ITEM + ']')
                        table_row.append('ASSET')
                        table_row.append('AssetType (%s) needed for this Asset %s is missing! Skipping. Error: [%s]' % (
                            new_asset[2], new_asset[0], e))
                        table_row.append('')
                else:
                    # self.stdout.write('[INFO]\t\tAsset: (%s) is present' % (new_asset[0]))
                    table_row.append('[' + INFO_ITEM + ']')
                    table_row.append('ASSET')
                    table_row.append('%s is present' % (new_asset[0]))
                    table_row.append(n.id)
                output_table.append(table_row)  # pretty output table



        # output pretty table
        self.stdout.write(tabulate(output_table, table_header))

    # MISSING:
    # check:    find duplicates
    # missing:  identify _original_ (lowest id) global asset of a certain name
    # missing:  see if duplicated is used in AssetPreset, ProductBase, Clients or Companys
    # missing:  if used somewhere relink to _original_ global asset
    def consolidate_assets(self):
        table_header = ['Status', 'Item', 'Change', 'Duplicate', 'ID']
        output_table = []
        existing_global_asset_names = []
        table_row = []

        global_assets = Asset.objects.filter(Q(client_owner__isnull=True) & Q(company_owner__isnull=True)).order_by('-id')

        for global_asset in global_assets:
            table_row = []
            if global_asset.name in existing_global_asset_names:
                is_duplicate = True
            else:
                is_duplicate = False
            existing_global_asset_names.append(global_asset.name)
            table_row.append('[' + INFO_ITEM + ']')
            table_row.append('ASSET')
            table_row.append('%s [%s] ' % (global_asset.name, global_asset.id))
            if is_duplicate:
                table_row.append('Duplicate')
            else:
                table_row.append('Original')
            table_row.append(global_asset.id)
            output_table.append(table_row)  # pretty output table

        self.stdout.write('\nGlobal assets:\n')
        self.stdout.write(tabulate(output_table, table_header))
        return False

    def purge_assets(self):

        try:
            asset_count = Asset.objects.all().count()
            Asset.objects.all().delete()
            self.stdout.write('Delete %s Assets' % asset_count)
        except:
            self.stdout.write('Error deleting Assets!')

        try:
            assettype_count = AssetType.objects.all().count()
            AssetType.objects.all().delete()
            self.stdout.write('Delete %s AssetTypes' % assettype_count)
        except:
            self.stdout.write('Error deleting AssetTypes')

    def add_arguments(self, parser):
        group = parser.add_mutually_exclusive_group()
        # group.add_argument('-o', '--order_id', type=str, help="Order ID to be CREATEDd/checked")
        # group.add_argument('-op', '--order_product_id', type=str, help="The ID of the OrderProduct to CREATED/check")

        # Named (optional) arguments
        group.add_argument(
            '--create',
            action='store_true',
            help='This creates the missing assets',
        )

        group.add_argument(
            '--reset',
            action='store_true',
            help='WARNING! This resets all existing assets to the default setting',
        )

        group.add_argument(
            '--consolidate',
            action='store_true',
            help='WARNING! This will delete all duplicated GLOBAL assets and relink to the original set with the lowest ID',
        )

        group.add_argument(
            '--purge',
            action='store_true',
            help='HUGE WARNING! This will delete all assets in the system and cause a COMPLETE PRODUCTION HALT!\nUse accordingly.',
        )

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

    def generate_global_presets(selfs, number=5):
        # generate global presets,
        new_global_assets = []
        for j in range(len(global_asset_preset)):
            for i in range(number):
                new_global_asset = [w.replace('{#}', str(i + 1)) for w in global_asset_preset[j]]
                new_global_assets.append(new_global_asset)

        #new_assets.append(new_global_assets)
        return new_global_assets

    def handle(self, *args, **options):


        createFlag = False
        resetFlag = False

        self.stdout.write('Initialize Assets')
        self.stdout.write('-----------------------------------------------')

        #assemble asset list
        new_global_assets = self.generate_global_presets(NUMBER_OF_GLOBAL_ASSETS)
        #new_assets = new_assets + new_global_assets
        table_header = ['Name', 'Value', 'AssetType', 'Description', 'Source', 'Layer', 'Property', 'Maxlength']
        new_assets = new_assets_templates + new_global_assets
        #print(tabulate(new_assets, table_header))

        if options['reset']:
            self.stdout.write('ResetFlag set so we are going to reset all exiting assets/assettypes to their default values')
            resetFlag = True

        if options['consolidate']:
            self.output_warning()
            self.stdout.write(
                'ConsolidateFlag set so we are going to delete duplicated assets and relink to the original set')
            answer = self.yes_or_no('Are you completely sure that you want to delete ALL assets from this system?')
            if answer:
                self.stdout.write('Ok here we go...')
                self.consolidate_assets()
                exit(1)
            else:
                self.stdout.write('Aborted deletion.')

        if options['create']:
            self.stdout.write('Let\'s see if we need to create assets...')
            #    createFlag = True
            self.init_data(new_assets, True, resetFlag)

        elif options['purge']:
            self.output_warning()
            self.stdout.write(
                'Note: Language and Resolutions cannot be delete through this command only Assets and AssetTypes')
            answer = self.yes_or_no('Are you completely sure that you want to delete ALL assets from this system?')
            if answer:
                self.stdout.write('Ok here we go...')
                self.purge_assets()
            else:
                self.stdout.write('Aborted deletion.')
        else:
            self.init_data(new_assets, createFlag, resetFlag)

        # self.stdout.write(('--EOA------------------------------------------')
