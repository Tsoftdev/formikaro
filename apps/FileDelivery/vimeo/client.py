import json
import vimeo
import time

from django.conf import settings


_client = vimeo.VimeoClient(
    token=settings.VIMEO_TOKEN,
    key=settings.VIMEO_USER_ID,
    secret=settings.VIMEO_SECRET
)

base_url = settings.VIMEO_URL
user_id = settings.VIMEO_USER_ID


class ApiHttpError(Exception):
    def __init__(self, http_status, url, method, response_text):
        self.http_status = http_status
        self.url = url
        self.method = method
        self.response_text = response_text

    def __str__(self):
        return '{} {} {} {}'.format(self.http_status, self.url, self.method, self.response_text)


def _call(path, method, params):
    if method == 'POST':
        resp = _client.post(path, data=params)
    elif method == 'PUT':
        resp = _client.put(path)
        return resp.status_code, None
    else:
        resp = _client.get(path)

    if resp.status_code not in [404, 201, 204, 200]:
        raise ApiHttpError(resp.status_code, path, method, resp.text)

    return resp.status_code, json.loads(resp.text)


def _api_get(path, **kwargs):
    return _call(path, 'GET', kwargs)


def _api_post(path, **kwargs):
    return _call(path, 'POST', kwargs)


def _api_put(path, **kwargs):
    return _call(path, 'PUT', kwargs)


def getAllFolders():
    status_code, result = _api_get(f'/me/projects?per_page=100')  # TODO implement pagination
    return [{'name': d['name'], 'uri': d['uri']} for d in result['data']]


def getFolderByName(name):
    result = getAllFolders()

    for f in result:
        if f['name'] == name:
            return f
    return None


def createNewFolder(name):
    status_code, results = _api_post('/me/projects', name=name)
    return results


def addVideoToFolder(video_id, folder_name, create=True):
    result = getFolderByName(folder_name)
    if not result:
        result = createNewFolder(folder_name)
    folder_uri = '{uri}/videos/{video_id}'.format(uri=result['uri'], video_id=video_id)
    _api_put(folder_uri)
    return folder_uri


def uploadVideo(file_name, title, description, password):
    uri = _client.upload(
        file_name,
        data={
            'name': title,
            'description': description,
            'privacy': {
                'view': 'password',
                'download': True
            },
            'password': password,
            'review_page': {
                'active': True
            }
        }
    )
    vimeo_id = uri.split('/')[-1]
    print('Moving video to Vimeo shop folder')
    new_uri = addVideoToFolder(video_id=vimeo_id, folder_name='Shop')
    print('Video moved to shop folder: URI {}'.format(new_uri))
    # return original uri because vimeo does not have a get call for videos in folders. symbolic links??
    return uri


def getVideoByUri(uri):
    return _api_get(uri)


def getVideoLink(data):
    if 'link' in data:
        return data['link']
    return None


def getReviewLink(data):
    if 'review_page' in data:
        if 'link' in data['review_page']:
            return data['review_page']['link']
    return None


def getDownloadLink(videoid):
    data = _api_get(videoid)
    print("DEBUG: %s" % data)
    if 'files' in data:
        for d in data['files']:
            if 'quality' in d:
                if d['quality'] == "hd":
                    return d['link']
    time.sleep(10)
    return getDownloadLink(videoid)
