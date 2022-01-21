import os

from dotenv import load_dotenv
from redis import Redis
from rq import get_current_job
from apps.FileDelivery.vimeo import client

import django
import logging

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "web.settings")
django.setup()

logging = logging.getLogger('videoupload')

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

load_dotenv(os.path.join(BASE_DIR, '.env'))

from app.models import Video


def firstJob(file, video_id):
    logging.info("Start video upload.")
    try:
        video = Video.objects.get(id=video_id)
        if video:
            logging.info("Start uploading file %s" % file)

            try:
                uri = client.uploadVideo(file, video.title, video.description, video.vimeo_passwd)
                logging.info("Videoupload sucessfull. Return uri %s" % uri)
                logging.info("Move %s to folder %s." % (video.title,video.project.abbreviation) )
                client.addVideoToFolder(uri, video.project.abbreviation)
                logging.info("Status for video %s set to COMPLETE." % file) 
                video.status = 'COMPLETE'
                video.save()
                return uri
            except Exception as e:
                logging.info(repr(e))
                logging.info("Status for video %s set to FAILED." % file) 
                video.status = 'FAILED'
                video.save()
                return None
    except FileNotFoundError:
        logging.error("file %s not found.",file)
    except:
        raise

def secondJob(vim,video_id):
    logging.info("Start second job")
    try:
        conn = Redis(host='redis')
        currentJob= get_current_job(conn)
        if currentJob is None:
            raise ValueError("No previous Job assigned.")
        if currentJob.dependency is None:
            raise ValueError("No dependency set for job.")
        firstJobRes = currentJob.dependency.result
        if firstJobRes is None:
            raise Exception("Videoupload failed.")
        resp = client.getVideoByUri(firstJobRes)
        video = Video.objects.get(id=video_id)
        if video:
            vim.video = video
            vim.endpoint = firstJobRes
            vim.response_text = resp
            vim.save()
            video.url = client.getVideoLink(resp)
            video.url_review = client.getReviewLink(resp)
            tmp = client.getDownloadLink(firstJobRes)
            logging.info(tmp)
            video.url_download = tmp
            video.save()
    except Exception as e:
        logging.info(repr(e))
    
