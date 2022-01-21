from django.core.management.base import BaseCommand, CommandError
from apps.FileCollector.models import Project, Video, VimeoResponse
from apps.FormikoBot.utils.jobs import firstJob, secondJob
from redis import Redis

import datetime
import django_rq
import json
import logging
import os
import re
import time
import subprocess
import sys
import vimeo

logging.basicConfig( format='%(asctime)s - %(levelname)s - %(message)s', level=logging.INFO)
#logging = logging.getLogger('videoupload')

class Command(BaseCommand):


    def add_arguments(self, parser):
        parser.add_argument('path', type=str, help="path to mount")        

    def handle(self, *args, **options):
        project = Project.objects.filter(abbreviation=match.group(1)).exclude(videos__unique_fn=f)
        if project.exists() and f.endswith(('.mp4','.avi','.mov')):
            logging.info('New Video %s found' % f)
            ff = options['path']+'/'+f
                        
            logging.info(ff) 
            info = self.ffprobe(file = ff)
            if 'streams' not in info:
                raise KeyError("Key 'streams' not found in stream info.")
            if not info['streams']:
                raise KeyError("'streams' has no object.")
                for dest in info['streams']:
                    if 'duration' not in dest:
                        raise KeyError("First object in 'streams' has no field 'duration'.")
                    if 'width' not in dest:
                        raise KeyError("First object in 'streams' has no field 'height'.")
                    if 'height' not in dest:
                        raise KeyError("First object in 'streams' has no field 'height'.")
                    if 'format' not in info:
                        raise KeyError("Key 'format' not found in stream info.")
                    if 'size' not in info['format']:
                        raise KeyError("'format' has no field 'size'")
                        
                    duration = datetime.timedelta(seconds=int(float(info['streams'][0]['duration'])))
                    width = int(info['streams'][0]['width'])
                    height = int(info['streams'][0]['height'])
                    size = float(info['format']['size'])/1000
                    logging.info("Checking project targets...")
                    
                    if project[0].video_target_duration > duration:
                        raise Exception("Target duration doesnt meet requirements: P.video_target_duration < video.duration")
                    if project[0].video_target_height != height or project[0].video_target_width != width:
                        raise Exception("Target resolution doesnt meet requirements: P.height == video.height && P.width == video.width")
                    if project[0].video_target_size > size:
                        raise Exception("Target size doesnt meet requirements: P.size < video.size")
                    logging.info("Project targets met requirements")
                    video = Video(
                            project=project[0],
                            title=fn,
                            description=video_des,
                            version=version, 
                            vimeo_passwd = project[0].default_vimeo_passwd, 
                            unique_fn=f, 
                            ffprobe_result = {})
                    video.save() 
                    v = Video.objects.get(id=video.id)
                    vim = VimeoResponse()
                    stepOne = django_rq.enqueue(firstJob,
                            args =(ff,v.id)
                            )
                    stepTwo = django_rq.enqueue(secondJob,
                            args = (vim,v.id),
                            depends_on = stepOne
                            )
                        
                    """
                        vim = VimeoResponse(video=v, endpoint=uri, response_text=json.dumps(resp))
                        logging.info(vim) 
                        stepTwo = django_rq.enqueue(secondJob,
                                args = (ff,),
                                depends_on = stepOne
                                )
                    """

   