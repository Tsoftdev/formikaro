import logging
import os
import re
import json
import datetime
import subprocess
from django.db.models import Count, Sum, Q
from django.contrib.auth.models import User
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from apps.FileCollector.models import Project, Order, OrderProduct, ORDER_PRODUCT_COMPLETE_STATUS, Video, \
    VIDEO_UPLOADING_NOW, VIDEO_UPLOADING_FAILED, ORDER_PRODUCT_FAILED_STATUS, Client, VIDEO_RENDERING_COMPLETED
from apps.ProductManager.models import Resolution
from apps.FileDelivery.tasks import upload_project_video, upload_order_video, get_paloma_user
from notifications.signals import notify


logger = logging.getLogger(__name__)
PROJECT_ERROR_FOLDER = settings.PROJECT_ERROR_FOLDER
BOT_PALOMA_USERNAME=settings.BOT_PALOMA_USERNAME

class Command(BaseCommand):
    local_parser = None

    def add_arguments(self, parser):
        self.local_parser = parser
        parser.add_argument(
            '-c', '--check_order_files_flag', action='store_true',
            help="Check if order has files to upload without actually uploading them to Vimeo"
        )

        parser.add_argument(
            '-t', '--try', action='store_true',
            help="Just performing checks no upload"
        )

        group = parser.add_mutually_exclusive_group()
        group.add_argument('-o', '--order_id', type=str, help="Order ID to be uploaded to Vimeo")
        group.add_argument('-p', '--project_folder_path', type=str, help="Directory with files to be uploaded to Vimeo")



    def handle(self, *args, **options):
        order_id = options.get('order_id', None)
        tryFlag = options.get('try', False)

        project_folder = options.get('project_folder_path', None)
        check_order_files_flag = options.get('check_order_files_flag')

        if project_folder:
            if os.path.isdir(project_folder):
                for project_file in os.listdir(project_folder):

                    # check if we are looking at a directory and if yes ignore
                    full_filepath = os.path.join(project_folder, project_file)
                    if os.path.isdir(full_filepath):
                        print('Ignoring directory %s' % project_file)
                        continue

                    # setup destionation and error folder
                    processed_file_dst = '{proj_folder}/{processed_folder}/{file_name}'.format(
                        proj_folder=settings.PROJECT_UPLOAD_FOLDER,
                        processed_folder=settings.PROJECT_ERROR_FOLDER,
                        file_name=os.path.basename(project_file)
                    )

                    error_folder = os.path.join(project_folder, settings.PROJECT_ERROR_FOLDER)
                    if not os.path.isdir(error_folder):
                        print('Error folder [%s] missing, trying to create' % error_folder)
                        try:
                            os.mkdir(error_folder)
                        except:
                            print('Couly not create error folder! Can\'t move files!')
                            continue

                    file_name, file_ext = os.path.splitext(project_file)
                    # https://regex101.com/r/9v2Dhh/1
                    #match = re.match(
                    #    r'^(?P<client_abbr>[0-9a-zA-ZÄÖÜäöüß]{2,5})_(?P<proj_abbr>[0-9a-zA-ZÄÖÜäöüß]{2,'
                    #    r'10})_(?P<episode>EP_([0-9]{1,2})_)?(?P<title>[0-9a-zA-ZÄÖÜäöüß -]{1,255}_)?((?!ep_|draft)(['
                    #    r'0-9a-zA-Z ]+)_)?(?P<version>(draft)_([a-zA-Z0-9]{1,2}|FINAL)|FINAL(_rev[0-9]{1,'
                    #    r'2})?)\.(mp4)$',
                    #   project_file, re.M | re.I) V1.0


                    #NOMENCLATURE V1.2 (since 251121)
                    #match = re.match(
                    #    r'^(?P<client_abbr>[0-9a-zA-ZÄÖÜäöüß]{3,5})_(?P<proj_abbr>[0-9a-zA-ZÄÖÜäöüß]{3,20})_(?'
                    #    r'P<episode>EP_([0-9]{1,2})_)?(?P<title>[0-9a-zA-ZÄÖÜäöüß-]{1,255}_)(?P<subtitle>SUB_'
                    #    r'(?P<sublang>([a-zA-Z]{1,2}))_)?((?!ep_|draft)([0-9a-zA-Z ]+)_)?(?P<version>(draft)_([a-zA-Z0-9]'
                    #    r'{1,2}|FINAL)|FINAL(_rev[0-9]{1,2})?)\.(mp4)$',
                    #   project_file, re.M | re.I)

                    #NOMENCLATUR V1.25 (since 301121)
                    #update V1.26 (since 160122) - title limited to 50 chars
                    match = re.match(
                        r'^(?P<client_abbr>[0-9a-zA-ZÄÖÜäöüß]{3,5})_(?P<proj_abbr>[0-9a-zA-ZÄÖÜäöüß]{3,20})_'
                        r'(?P<episode>EP_([0-9]{1,2})_)?(?P<title>[0-9a-zA-ZÄÖÜäöüß-]{1,50}_)(?P<subtitle>SUB_'
                        r'(?P<sublang>([a-zA-Z]{1,2}))_)?((?!ep_|draft)([0-9a-zA-Z ]+)_)?(?P<version>(draft)_'
                        r'([a-zA-Z0-9]{1,2}|FINAL)|(draft_)?FINAL(_rev[0-9]{1,2})?)\.(mp4)$',
                        project_file, re.M | re.I)

                    if match:
                        project_abbr = match.group('proj_abbr')
                        client_abbr = match.group('client_abbr')
                        version = match.group('version')
                        if version.upper().find('Draft_'):
                            version = version.upper().replace('DRAFT_', '')
                        if version.upper().find('rev'):
                            version = version.upper().replace('FINAL_', '')
                        episode = match.group('episode')
                        sublang = match.group('sublang')
                        if episode:
                            episode = [int(s) for s in episode.split('_') if s.isdigit()][0]
                        title = match.group('title').split("_")[0] if match.group('title') else ''

                        print('Title:\t', title)
                        print('\tProject:\t', project_abbr)
                        print('\tClient:\t\t', client_abbr)
                        print('\tVersion:\t', version)
                        print('\tEpisode:\t', episode)
                        if sublang:
                            print('\tSubtitle:\t', sublang)
                        else:
                            print('\tNo subtitles')
                        project_queryset = Project.objects.filter(abbreviation__iexact=project_abbr)
                        client_queryset = Client.objects.filter(abbreviation__iexact=client_abbr)
                        if not project_queryset and not client_queryset:
                            # either client or project does not exist. Skip to the next file
                            print('No project or client found for file: ', project_file)

                            # send notification
                            paloma_user = get_paloma_user()
                            recepients = User.objects.all()
                            verb_text = 'File <b>%s</b> doesn\'t have a client!' % project_file
                            level = 'error'

                            notify.send(paloma_user, recipient=recepients, verb=verb_text, description='', level=level)
                            print('Moving the local file %s to: %s' % (full_filepath, format(processed_file_dst)))
                            os.rename(full_filepath, processed_file_dst)

                            continue

                        project = project_queryset.first()
                        # print("client %s" % client_abbr)

                        video_path = project_folder + '/' + project_file
                        print('New Video %s found' % video_path)

                        # FF PROBE START
                        ffprobe_result = self.ffprobe_file(file=video_path)
                        if 'streams' not in ffprobe_result:
                            raise KeyError("Key 'streams' not found in stream info.")
                        if not ffprobe_result['streams']:
                            raise KeyError("'streams' has no object.")
                        for dest in ffprobe_result['streams']:
                            if 'duration' not in dest:
                                raise KeyError("First object in 'streams' has no field 'duration'.")
                            if 'width' not in dest:
                                raise KeyError("First object in 'streams' has no field 'height'.")
                            if 'height' not in dest:
                                raise KeyError("First object in 'streams' has no field 'height'.")
                        if 'format' not in ffprobe_result:
                            raise KeyError("Key 'format' not found in stream info.")
                        if 'size' not in ffprobe_result['format']:
                            raise KeyError("'format' has no field 'size'")

                        #duration = datetime.timedelta(seconds=int(float(ffprobe_result['streams'][0]['duration'])))
                        duration = int(float(ffprobe_result['streams'][0]['duration']))
                        width = int(ffprobe_result['streams'][0]['width'])
                        height = int(ffprobe_result['streams'][0]['height'])
                        size = float(ffprobe_result['format']['size'])

                        bitrate = ffprobe_result['format']['bit_rate']
                        fps = int(ffprobe_result['streams'][0]['time_base'][2:4])
                        codec_name = ffprobe_result['streams'][0]['codec_name']
                        codec_long_name = ffprobe_result['streams'][0]['codec_long_name']
                        pix_fmt = ffprobe_result['streams'][0]['pix_fmt']

                        print('video spec:\n\tduration: %s\tWxH:\t%s:%s\tsize:\t%s\n\tbitrate:%s\tfps:\t%s\tcodec_name:\t%s\tcodec_long_name:\t%s\tpix_fmt:\t%s' % (duration, width, height, size, bitrate, fps, codec_name, codec_long_name, pix_fmt))

                        try:
                            resolution = Resolution.objects.filter(Q(width=width) & Q(height = height))[0]
                            print('Found matching resolution %s' % resolution)
                        except Exception as e:
                            resolution = False
                            print('No matching resolution found %s' % e)

                        # UPLOAD START

                        if not tryFlag:
                            video, created = Video.objects.get_or_create(
                                project=project, unique_fn__iexact=file_name,
                                defaults={'unique_fn': file_name, 'version': version, 'episode': episode}
                            )

                            if video.status == VIDEO_UPLOADING_NOW:
                                print('Video: [{}] is being uploaded, skipping to the next project file '.format(
                                    project_file)
                                )
                                continue

                            video.duration = duration
                            video.size = size
                            video.bitrate = bitrate
                            video.fps = fps
                            video.codec_name = codec_name
                            video.codec_long_name = codec_long_name
                            video.pix_fmt = pix_fmt

                            if resolution:
                                video.resolution = resolution
                            else:
                                paloma_user = get_paloma_user()
                                recepients = User.objects.all()
                                verb_text = 'File <b>%s</b> has non standard resolution (%s:%s)' % (project_file, width, height)
                                level = 'warning'
                                notify.send(paloma_user, recipient=recepients, verb=verb_text, description='',
                                            level=level)

                            video.ffprobe_result = ffprobe_result
                            video.status = VIDEO_UPLOADING_NOW
                            video.save()
                            print('Starting New VIMEO upload')
                            data = {
                                'title': file_name,
                                'description': 'description',
                                'password': project.default_vimeo_passwd
                            }
                            _task =     upload_project_video.delay(video_path=video_path, data=data, video_record_id=video.id)
                            print('Upload Task ID: {_id}. Status: {status}. '.format(status=_task.status, _id=_task.id))
                        else:
                            print('Try flag is set so no action is performed\n')
                    else:
                        print("Filename %s doesnt meet nomenclature requirements. Continue ... " % project_file)

                        print('Moving the local file %s to: %s' % (full_filepath, format(processed_file_dst)))
                        os.rename(full_filepath, processed_file_dst)

                        #send notification
                        paloma_user = get_paloma_user()
                        recepients = User.objects.all()
                        verb_text = 'File <b>%s</b> not meeting nomenclature requirements!' % project_file
                        level='error'

                        notify.send(paloma_user, recipient=recepients, verb=verb_text, description='', level=level)

                        continue
            else:
                print('Invalid Directory')
        elif order_id and Order.objects.filter(id=order_id).exists():
            order_products = list(OrderProduct.objects.filter(order_id=order_id, status=ORDER_PRODUCT_COMPLETE_STATUS))
            if check_order_files_flag:
                print('Found [{prod_count}] Order Product(s) for Order Number: {order_num}'.format(
                    prod_count=len(order_products), order_num=order_id))
                print('Check Complete')
                return

            print('Uploading [{prod_count}] Order Products for Order Number: {order_num}'.format(
                prod_count=len(order_products), order_num=order_id))
            for order_prod in order_products:
                video_records = Video.objects.filter(order_product=order_prod, status=VIDEO_RENDERING_COMPLETED)
                if not video_records.exists():
                    continue
                # Get the latest video with the status of COMPLETE
                video_record = video_records.first()

                _folder = video_record.order_product.get_folder(absolute=True) / settings.SHOP_ORDER_RENDER_OUTPUT_FOLDER

                video_path = '{folder}/{filename}.mov'.format(folder=_folder, filename=video_record.unique_fn)

                print('Checking Video Folder: {} for Order PROD {}'.format(video_path, order_prod.id))

                if not os.path.exists(video_path):
                    print(
                        'Video File: {} not found  but order was marked as COMPLETE, setting order STATUS to FAILED'.
                            format(video_path)
                    )
                    order_prod.status = ORDER_PRODUCT_FAILED_STATUS
                    order_prod.save()
                    video_record.status = VIDEO_UPLOADING_FAILED
                    video_record.save()
                    # skip order line item and go to the next one
                    continue

                if video_record.status == VIDEO_UPLOADING_NOW:
                    # Order Line is currently uploading, skip to the next order item
                    print('Video: [{}] is being uploaded, skipping to the next order prod '.format(video_path))
                    continue

                data = {
                    'title': video_record.unique_fn,
                    'description': 'description',
                    'password': order_prod.order.client.default_vimeo_passwd
                }
                print('Starting New VIMEO upload')
                video_record.status = VIDEO_UPLOADING_NOW
                video_record.save()

                _task = upload_order_video.delay(video_path=video_path, data=data, video_record_id=video_record.id)
                print('Upload Task ID: {_id}. Status: {status}. '.format(status=_task.status, _id=_task.id))

        else:
            raise CommandError(
                'Usage: manage.py upload_orders [-h] [-c check_order_files_flag] [-o ORDER_ID | -p PROJECT_FOLDER_PATH]'
            )

    def ffprobe_file(self, file):
        try:
            logging.info("ffprobe video %s" % file)
            cmd = ["ffprobe", "-v", "error", "-select_streams", "v:0", "-print_format", "json", "-show_format",
                   "-show_streams", file]
            logging.info("Run %s " % " ".join(cmd))
            process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                       universal_newlines=True).communicate()
            return json.loads(process[0])

        except FileNotFoundError:
            return json.loads({"error": "Couldn't find file %s " % file})