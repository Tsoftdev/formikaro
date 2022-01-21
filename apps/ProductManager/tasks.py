import datetime
import json
import os
from pathlib import Path

import requests
from celery import shared_task
from django.conf import settings

from apps.FileCollector.models import Video, VIDEO_RENDERING, VIDEO_RENDERING_COMPLETED, ORDER_PRODUCT_COMPLETE_STATUS, \
    ORDER_PRODUCT_FAILED_STATUS, VIDEO_RENDERING_FAILED, OrderProduct, ORDER_PRODUCT_DELIVERED_STATUS, \
    ORDER_COMPLETE_STATUS, ORDER_FAILED_STATUS


def check_video_render_progress(video_record_id):
    video = Video.objects.get(id=video_record_id)
    url = 'http://{ip_address}/api/v1/jobs/{uid}'.format(
        ip_address=settings.NEXRENDER_SERVER_IP, uid=video.renderer_job_id
    )
    # url = 'http://{ip_address}/api/v1/jobs'.format(ip_address=settings.NEXRENDER_SERVER_IP)
    nexrender_headers = {'Content-type': 'application/json', 'nexrender-secret': settings.NEXRENDER_SECRET}

    # print("URL DEBUG %s" % url)
    successful_query = True
    render_progress = 0
    ignored_video = False  # Set this to True when we try to process an Order Product which is marked as COMPLETE
    if video.order_product.status == ORDER_PRODUCT_COMPLETE_STATUS:
        ignored_video = True
        print(
            'ORDER PRODUCT [{}] IS ALREADY MARKED AS COMPLETE, SKIPPING THIS VIDEO [{}] AND SETTING STATUS TO FAILED'.
                format(video.order_product.id, video.id)
        )
        return successful_query, render_progress, ignored_video

    try:
        response = requests.get(url, headers=nexrender_headers)
        if response.status_code != 200:
            print('ERROR: {}, {}'.format(response.status_code, response.text))
            successful_query = False
        else:
            response_data = json.loads(response.text)
            job_state = response_data.get('state', None)

            if job_state == 'finished':
                _folder = video.order_product.get_folder(absolute=True) / settings.SHOP_ORDER_RENDER_OUTPUT_FOLDER
                output_file = '{folder}/{filename}.mov'.format(folder=_folder, filename=video.unique_fn)
                print('RENDER JOB {} COMPLETED, EXPECTED OUTPUT FILE IS: {}'.format(video.renderer_job_id, output_file))
                if os.path.isfile(output_file):
                    print('RENDER JOB {} COMPLETE, SETTING ORDER PRODUCT TO {}'.format(
                        video.renderer_job_id, ORDER_PRODUCT_COMPLETE_STATUS)
                    )
                    job_start_time = response_data.get('createdAt', None)
                    job_end_time = response_data.get('finishedAt', None)
                    if job_start_time and job_end_time:
                        job_start_time = datetime.datetime.strptime(job_start_time, "%Y-%m-%dT%H:%M:%S.%fZ")
                        job_end_time = datetime.datetime.strptime(job_end_time, "%Y-%m-%dT%H:%M:%S.%fZ")
                        render_time = job_end_time - job_start_time
                        render_time = round(render_time.total_seconds())
                        video.rendering_time = render_time
                    video.size = Path(output_file).stat().st_size
                    video.status = VIDEO_RENDERING_COMPLETED
                    video.order_product.status = ORDER_PRODUCT_COMPLETE_STATUS
                    video.save()
                    video.order_product.save()
                    video.order_product.write_log(
                        message='Order Product {} rendering completed. STATUS set to COMPLETE'.format(
                            video.order_product_id
                        )
                    )

                    # Mark the order as COMPLETE if all OrderProducts are marked as COMPLETE or DELIVERED
                    remaining_undelivered_order_prods = OrderProduct.objects.filter(
                        order=video.order_product.order).exclude(status=ORDER_PRODUCT_COMPLETE_STATUS). \
                        exclude(status=ORDER_PRODUCT_DELIVERED_STATUS).exists()
                    if not remaining_undelivered_order_prods:
                        print('All products for Order {} has been rendered, Order STATUS set to {}'.format(
                            video.order_product.order.id, ORDER_COMPLETE_STATUS
                        ))
                        video.order_product.order.status = ORDER_COMPLETE_STATUS
                        video.order_product.order.save()
                        video.order_product.order.write_log(
                            message='All products for Order {} has been rendered, Order STATUS set to {}'.format(
                                video.order_product.order.id, ORDER_COMPLETE_STATUS)
                        )

                else:
                    print('ERROR: RENDER JOB {} COMPLETED BUT OUTPUT FILE IS MISSING, SETTING ORDER PRODUCT TO {}'.
                          format(video.renderer_job_id, ORDER_PRODUCT_FAILED_STATUS))
                    successful_query = False
                    video.order_product.status = ORDER_PRODUCT_FAILED_STATUS
                    video.status = VIDEO_RENDERING_FAILED
                    video.save()
                    video.order_product.save()
                    video.order_product.write_log(
                        message='RENDER JOB {} COMPLETED BUT OUTPUT FILE IS MISSING, SETTING ORDER PRODUCT TO {}'.
                        format(video.renderer_job_id, ORDER_PRODUCT_FAILED_STATUS))
                    print('Product {} for Order {} has failed rendering, Order STATUS set to {}'.format(
                        video.order_product_id, video.order_product.order.id, ORDER_FAILED_STATUS
                    ))
                    video.order_product.order.status = ORDER_FAILED_STATUS
                    video.order_product.order.save()
                    video.order_product.order.write_log(
                        message='Product ID: {} for this Order has failed rendering, STATUS set to {}'.format(
                            video.order_product_id, ORDER_FAILED_STATUS)
                    )

            if job_state == 'error':
                api_error = response_data.get('error', None)
                print('ERROR: RENDER JOB {} FAILED WITH API MESSAGE: [{}]. SETTING ORDER PRODUCT STATUS TO {}'.
                      format(video.renderer_job_id, api_error, ORDER_PRODUCT_FAILED_STATUS))
                video.order_product.status = ORDER_PRODUCT_FAILED_STATUS
                video.status = VIDEO_RENDERING_FAILED
                video.save()
                video.order_product.save()
                video.order_product.write_log(
                    message='ERROR: RENDER JOB {} FAILED WITH API MESSAGE: [{}]. SETTING ORDER PRODUCT STATUS TO {}'.
                      format(video.renderer_job_id, api_error, ORDER_PRODUCT_FAILED_STATUS)
                )

                # Mark the ORDER as FAILED as well

                print('Product ID: {} for this Order has failed rendering with error: {}.STATUS set to {}'.format(
                        video.order_product_id, api_error, ORDER_FAILED_STATUS)
                )
                video.order_product.order.status = ORDER_FAILED_STATUS
                video.order_product.order.save()
                video.order_product.order.write_log(
                    message='Product ID: {} for this Order has failed rendering with error: {}.STATUS set to {}'.format(
                        video.order_product_id, api_error, ORDER_FAILED_STATUS)
                )

            render_progress = response_data.get('renderProgress', 0)

    except requests.ConnectionError:
        print('[ERROR]\tRENDER SERVER offline')
        successful_query = False
    except Exception as ex:
        successful_query = False
        print('ERROR Connecting to NexRender: {}'.format(ex))
    return render_progress, successful_query, ignored_video


@shared_task(name="apps.ProductManager.tasks.check_all_videos_render_progress")
def check_all_videos_render_progress():
    for video in list(Video.objects.filter(status=VIDEO_RENDERING)):
        render_progress, successful_query, ignored_video = check_video_render_progress(video.id)
