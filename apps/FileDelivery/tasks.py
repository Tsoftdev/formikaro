import os
import logging

from celery import shared_task
from django.core import management
from django.conf import settings
from django.contrib.auth.models import User

from apps.FileDelivery.vimeo.vimeo_uploader import upload_file_to_vimeo, add_vimeo_data_to_video_record
from apps.FileCollector.models import OrderProduct, Video, VIDEO_UPLOADING_FAILED, ORDER_PRODUCT_DELIVERED_STATUS, \
    ORDER_DELIVERED_STATUS


logger = logging.getLogger(__name__)

PROJECT_UPLOAD_FOLDER = settings.PROJECT_UPLOAD_FOLDER
BOT_PALOMA_USERNAME = settings.BOT_PALOMA_USERNAME
BOT_LASTNAME = settings.BOT_LASTNAME


@shared_task(name="apps.FormikoBot.tasks.upload_project_videos")
def upload_project_videos():
    # call_command('assembler', '--create', order_id, stdout=out)
    management.call_command('upload_orders', '-p', PROJECT_UPLOAD_FOLDER)

# debug task for vimeo api tests
def get_vimeo_info(vimeo_id):
    print("k")





@shared_task(name="apps.FormikoBot.tasks.upload_project_video")
def upload_project_video(video_path, data, video_record_id):

    video_record = Video.objects.get(id=video_record_id)
    try:


        uri = upload_file_to_vimeo(video_path=video_path, data=data)
        if uri:
            # move file to completed folder
            processed_file_dst = '{proj_folder}/{processed_folder}/{file_name}'.format(
                proj_folder=settings.PROJECT_UPLOAD_FOLDER, processed_folder=settings.PROJECT_PROCESSED_FOLDER,
                file_name=os.path.basename(video_path)
            )
            print('Moving the local file to: {}'.format(processed_file_dst))
            os.rename(video_path, processed_file_dst)

            size = os.path.getsize(processed_file_dst)
            add_vimeo_data_to_video_record(uri=uri, video_record_id=video_record_id, size=size)

            #video_record.save() #something is not working here
        else:
            print('Upload Failed, Video Model Status set to FAILED')
            video_record.status = VIDEO_UPLOADING_FAILED
            video_record.save()



    except Exception as exc:
        print('Error during upload: {}'.format(exc))
        video_record.status = VIDEO_UPLOADING_FAILED
        video_record.save()


@shared_task(name="apps.FormikoBot.tasks.upload_order_video")
def upload_order_video(video_path, data, video_record_id):
    video_record = Video.objects.get(id=video_record_id)
    try:
        uri = upload_file_to_vimeo(video_path=video_path, data=data)
        if uri:
            add_vimeo_data_to_video_record(uri=uri, video_record_id=video_record_id)
            video_record.order_product.status = ORDER_PRODUCT_DELIVERED_STATUS
            video_record.order_product.save()
            video_record.order_product.write_log(message='Upload Complete: URI {}'.format(uri))
            remaining_undelivered_order_prods = OrderProduct.objects.filter(order=video_record.order_product.order) \
                .exclude(status=ORDER_PRODUCT_DELIVERED_STATUS).exists()
            if not remaining_undelivered_order_prods:
                print('All products for Order {} has been delivered, Order STATUS set to DELIVERED'.format(
                    video_record.order_product.order.id
                ))
                video_record.order_product.write_log(
                    message='All products for Order {} has been delivered, Order STATUS set to DELIVERED'.format(
                        video_record.order_product.order.id)
                )
                video_record.order_product.order.status = ORDER_DELIVERED_STATUS
                video_record.order_product.order.save()
        else:
            video_record.order_product.write_log(message='Upload Failed, Video Model Status set to FAILED')

    except Exception as exc:
        print('Error during upload: {}'.format(exc))
        video_record.order_product.write_log(message='Error during upload: {}'.format(exc))
        video_record.status = VIDEO_UPLOADING_FAILED
        video_record.save()


# creating the paloma user that is used to send all FileDelvery notifications
def get_paloma_user():

    try:
        paloma = User.objects.get(username=BOT_PALOMA_USERNAME)
    except:
        #not existing so create the user
        paloma = User.objects.create_user(username=BOT_PALOMA_USERNAME, email='paloma@formikaro.io', password='p4l0m4', first_name=BOT_PALOMA_USERNAME, last_name=BOT_LASTNAME)
        paloma.save()

    return paloma
