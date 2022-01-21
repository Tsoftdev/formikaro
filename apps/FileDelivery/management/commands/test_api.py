import logging
import os
import re

from django.core.management.base import BaseCommand, CommandError

from apps.FileCollector.models import Project, Order, OrderProduct, ORDER_PRODUCT_COMPLETE_STATUS, Video, \
    VIDEO_UPLOADING_NOW, VIDEO_UPLOADING_FAILED, ORDER_PRODUCT_FAILED_STATUS, Client
from apps.FileDelivery.tasks import upload_project_video, upload_order_video
from apps.FileDelivery.vimeo.client import uploadVideo, getVideoByUri

logger = logging.getLogger(__name__)
import requests
import vimeo
from django.conf import settings
from bs4 import BeautifulSoup as bs

v = vimeo.VimeoClient(
    token=settings.VIMEO_TOKEN,
    key=settings.VIMEO_USER_ID,
    secret=settings.VIMEO_SECRET
)

class Command(BaseCommand):
    local_parser = None

    def add_arguments(self, parser):
        self.local_parser = parser
        parser.add_argument(
            '-c', '--check_order_files_flag', action='store_true',
            help="Check if order has files to upload without actually uploading them to Vimeo"
        )
        parser.add_argument('-vid', '--vimeo_id', type=str, help="Vimeo ID we want to check")


    def handle(self, *args, **options):
        vimeo_id = options.get('vimeo_id', None)
        print("Checking Vimeo ID [%s]" % vimeo_id)
        #uri = uploadVideo(
        #    file_name= 'https://api.vimeo.com/videos/' + vimeo_id,
        #    title='',
        #   description='',
        #    password='',
        #)

        # Make the request to the server for the "/me" endpoint.
        #about_me = v.get('/me')
        uri = '/videos/' + vimeo_id

        search_token = '"clip":{"id":' + vimeo_id
        url = "https://vimeo.com/" + vimeo_id

        with requests.Session() as s:
            r = s.get(url).text
            #print(r.text.encode("utf-8"))

        #r.post(url, data=payload)
        data = bs(r, 'html.parser')
        print(data.encode("utf-8"))
        #result = data.find(search_token)
        #print("token:\t%s\ndata:\t%s" % (search_token, data.result))


        exit()
        about_me = v.get(uri)

        # Make sure we got back a successful response.
        assert about_me.status_code == 200

        # Load the body's JSON data.
        print("about me %s" %  about_me.json())

        #result = getVideoByUri(uri)
