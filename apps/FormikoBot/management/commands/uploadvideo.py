from django.core.management.base import BaseCommand, CommandError
from .models import Project, Video, VimeoResponse
from .utils import firstJob, secondJob
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
        try:
            if (os.path.isdir(options['path'])):
                for f in os.listdir(options['path']):
                    fn, f_ext = os.path.splitext(f)
                    # https://regex101.com/r/NzExg5/4
                    match = re.match(r'(?i)^([0-9a-zA-Z]{3,5})_(EP_([0-9]{1,2})_)?((?!ep_|draft)([0-9a-zA-Z ]+)_)?((draft)_([a-zA-Z0-9]{1,2}|FINAL)|FINAL(_rev[0-9]{1,2})?)\.(mp4)$',f,re.M|re.I)
                    if match:
                        print(f)
                        print(match.groups())
                        video_des = match.group(5)
                        if match.group(8):
                            logging.info("Vidoe Version set to %s." % match.group(8))
                            version = match.group(8)
                        elif match.group(9):
                            logging.info("Vidoe Version set to %s." % match.group(6))
                            version = match.group(6)
                        else:
                            version = 'FINAL'
                           
                    else:
                        logging.info("Filename %s doesnt meet nomenclature requirements. Continue ... " % f)
                        continue 
                    logging.info("%s assigned as project abbreviation." % match.group(1))
                    des = fn.split("_")
                    #logging.info("File %s detected." % f)
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
            else:
                raise Exception('Directory %s doesnt exist.' % options['path'])
        except KeyError as e:
            logging.info(repr(e))
        except Exception as e:
            logging.info(str(e))


    def ffprobe(self, file):
        try:
            logging.info("ffprobe video %s" % file)
            cmd=["ffprobe","-v","error","-select_streams","v:0","-print_format","json","-show_format","-show_streams",file]
            logging.info("Run %s " % " ".join(cmd))
            process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True).communicate()
            return json.loads(process[0])

        except FileNotFoundError:
            return json.loads({"error":"Couldn't find file %s "%file})
