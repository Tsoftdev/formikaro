import logging


from apps.FileCollector.models import Video, VIDEO_UPLOADING_COMPLETE, VIDEO_UPLOADING_FAILED
from .client import uploadVideo, getVideoByUri

logger = logging.getLogger(__name__)


def add_vimeo_data_to_video_record(uri, video_record_id, size=0):
    video_record = Video.objects.get(id=video_record_id)
    if uri:
        try:
            status_code, vimeo_data = getVideoByUri(uri)
            vimeo_id = uri.split('/')[-1]
            video_record.response_upload = vimeo_data
            video_record.vimeo_id = vimeo_id
            video_password = vimeo_data.get('password', None)
            video_record.vimeo_passwd = video_password
            video_review_link = vimeo_data.get('review_page', {}).get('link', None)
            video_download_links = vimeo_data.get('download', {})
            video_download_link = video_download_links[0].get('link', None) if video_download_links else None
            video_record.url = vimeo_data.get('link', None)
            video_record.url_review = video_review_link
            video_record.url_download = video_download_link
            video_record.status = VIDEO_UPLOADING_COMPLETE
            video_record.size = size
            video_record.save()
            return uri
        except Exception as httpExc:
            print('Failed to get Vimeo Data for URI: [{}]. Error {}'.format(uri, httpExc))

    else:
        print('Upload Failed, setting Video Model Status to FAILED')
        video_record.status = VIDEO_UPLOADING_FAILED
        video_record.save()
        return None


def upload_file_to_vimeo(video_path, data):
    print('Uploading File: {}'.format(video_path))
    uri = uploadVideo(
        file_name=video_path,
        title=data.get('title', 'Untitled'),
        description=data.get('description', ''),
        password=data.get('password', '')
    )
    return uri
