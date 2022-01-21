import os
import logging
import shutil
import subprocess
import time

# from watchdog.observers import Observer
from watchdog.observers.polling import PollingObserver
from watchdog.events import PatternMatchingEventHandler
from pathlib import Path
from django.conf import settings
from datetime import datetime

from apps.FileCollector.models import OrderProduct, Video, ORDER_COMPLETE_STATUS, ORDER_FAILED_STATUS, \
    ORDER_PRODUCT_COMPLETE_STATUS, ORDER_PRODUCT_FAILED_STATUS

logger = logging.getLogger(__name__)


def is_valid_order_product(order_product_id):
    is_valid = True
    error = None
    try:
        order_product = OrderProduct.objects.get(id=order_product_id)
        if not order_product.order_folder_created:
            error = 'Order Product with ID: {} does not have an order folder'.format(order_product_id)
            is_valid = False
            return is_valid, error
        aep_file_path = '{folder_path}/{aep_file}.aep'.format(
            folder_path=order_product.get_folder(True), aep_file=order_product.product.fsin
        )
        if not os.path.exists(aep_file_path):
            error = 'Order Product with ID: {} does not have an aep file'.format(order_product_id)
            is_valid = False
            return is_valid, error
        return is_valid, error
    except OrderProduct.DoesNotExist as exc:
        is_valid = False
        error = 'Order Product with ID: {} does not exist'.format(order_product_id)
        return is_valid, error


def renderbot(order_product_id):
    renderbot_output_folder = Path(settings.SHOP_FOLDER) / settings.SHOP_ORDER_RENDER_FOLDER / \
                              settings.SHOP_ORDER_RENDER_OUTPUT_FOLDER
    if len(os.listdir(renderbot_output_folder)) > 0:
        for file in os.listdir(renderbot_output_folder):
            if file.startswith('FINAL') and file.endswith('.mp4'):
                print(f'{file} exists in the output directory. Watching the file for size changes')
                previous_rendered_file = "{flder}/{file_name}".format(flder=renderbot_output_folder, file_name=file)
                file_size = Path(previous_rendered_file).stat().st_size
                current_time = start_watch = time.perf_counter()
                while current_time <= start_watch + 3:
                    current_time = time.perf_counter()
                    new_file_size = Path("{flder}/{file_name}".format(flder=renderbot_output_folder, file_name=file)) \
                        .stat().st_size
                if new_file_size == file_size:
                    archived_folder = "{}/ARCHIVED".format(renderbot_output_folder)
                    if not os.path.isdir(archived_folder):
                        os.mkdir(archived_folder)
                    archived_file = "{outfolder}/ARCHIVED/{tstamp}_{file}".format(
                        outfolder=renderbot_output_folder, tstamp=datetime.now().strftime("%Y-%m-%d, %H-%M-%S"),
                        file=file
                    )
                    print('No file changes detected, moving the previous rendered file to {}'.format(archived_file))
                    os.rename(previous_rendered_file, archived_file)
                else:
                    print(f'{file} is still being processed, we can not start a new job, exiting')
                    return
    order_product = OrderProduct.objects.get(id=order_product_id)
    aep_file_path = '{folder_path}/{aep_file}.aep'.format(
        folder_path=order_product.get_folder(True), aep_file=order_product.product.fsin
    )
    renderbot_file = '{shop_folder}/{render_folder}/{file_name}'.format(
        shop_folder=settings.SHOP_FOLDER, render_folder=settings.SHOP_ORDER_RENDER_FOLDER,
        file_name=os.path.basename(aep_file_path)
    )
    print('Copying {} file to: {}'.format(aep_file_path, renderbot_file))
    shutil.copyfile(aep_file_path, renderbot_file)
    renderbot.rendered_file_size = 0
    renderbot.rendered_file_name = None
    renderbot.start_render_time = 0
    renderbot.rendering_final_file = False

    def on_created(event):
        available_files_and_flders = os.listdir(renderbot_output_folder)
        for item in available_files_and_flders:
            if item != 'ARCHIVE' and not os.path.basename(event.src_path).endswith('.mp4'):
                renderbot.start_render_time = time.perf_counter()
        if os.path.basename(event.src_path).startswith('FINAL') and os.path.basename(event.src_path).endswith('.mp4'):
            renderbot.rendering_final_file = True
            renderbot.rendered_file_name = os.path.basename(event.src_path)
            print(f"{event.src_path} has been created!")
            renderbot.rendered_file_size = Path(event.src_path).stat().st_size

    def on_modified(event):
        if os.path.basename(event.src_path).startswith('FINAL') and os.path.basename(event.src_path).endswith('.mp4'):
            renderbot.rendered_file_size = Path(event.src_path).stat().st_size
            renderbot.rendered_file_name = os.path.basename(event.src_path)
            print(f"File {event.src_path}, Rendering in Progress. New Size {renderbot.rendered_file_size}")

    patterns = ["*"]
    ignore_patterns = None
    ignore_directories = False
    case_sensitive = True
    my_event_handler = PatternMatchingEventHandler(patterns, ignore_patterns, ignore_directories, case_sensitive)
    my_event_handler.on_created = on_created
    my_event_handler.on_modified = on_modified
    path = renderbot_output_folder
    go_recursively = False
    my_observer = PollingObserver() # changed from Observer to PollingObserver
    my_observer.schedule(my_event_handler, path, recursive=go_recursively)
    print("Waiting for Adobe to Process file to be rendered to: %s " % renderbot_output_folder)
    initial_watch = watch_time = time.perf_counter()
    my_observer.start()

    file_size_check_counter = 0
    rendering_timeout = False
    # If the file size remains the same after 10 checks we assume the file size has stopped growing
    while True and not file_size_check_counter > 10:
        watch_time = time.perf_counter()
        if watch_time >= initial_watch + 300 and not renderbot.rendering_final_file:
            print('Adobe Rendering timed out. Rendering machine is offline')
            rendering_timeout = True
            break
        rendered_file = '{shop_folder}/{render_folder}/{output}/{file_name}'.format(
            shop_folder=settings.SHOP_FOLDER, render_folder=settings.SHOP_ORDER_RENDER_FOLDER,
            output=settings.SHOP_ORDER_RENDER_OUTPUT_FOLDER, file_name=renderbot.rendered_file_name
        )
        if os.path.exists(rendered_file):
            new_file_size = Path(rendered_file).stat().st_size
            if renderbot.rendered_file_size > 0 and (new_file_size == renderbot.rendered_file_size):
                file_size_check_counter += 1
    rendering_time = time.perf_counter() - renderbot.start_render_time
    my_observer.stop()
    my_observer.join()
    if rendering_timeout:
        return

    final_file = "{folder}/{file_name}.mp4".format(
        folder=order_product.get_folder(absolute=True) / settings.SHOP_ORDER_RENDER_OUTPUT_FOLDER,
        file_name=order_product.get_folder(False)
    )
    try:
        order_output_folder = folder = order_product.get_folder(
            absolute=True) / settings.SHOP_ORDER_RENDER_OUTPUT_FOLDER
        if not os.path.isdir(order_output_folder):
            os.mkdir(order_output_folder)

        shutil.copyfile(rendered_file, final_file)
        os.unlink(rendered_file)
        print("ffprobe video %s" % final_file)
        cmd = ["ffprobe", "-v", "quiet", "-show_error ", "-print_format", "json", final_file]
        print("Run %s " % " ".join(cmd))
        process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                   universal_newlines=True).communicate()
        result = process[0]
        video_record, created = Video.objects.get_or_create(
            order_product=order_product,
            defaults={'rendering_time': rendering_time, 'size': renderbot.rendered_file_size}
        )

        if not result:
            result = {}

        video_record.ffprobe_result = result
        video_record.save() # DEBUG
        if os.path.exists(final_file) and not result:
            print('Order Product {} rendering completed. STATUS set to COMPLETE'.format(
                    order_product_id)
            )
            order_product.write_log(
                message='Order Product {} rendering completed. STATUS set to COMPLETE'.format(
                    order_product_id)
            )
            order_product.status = ORDER_PRODUCT_COMPLETE_STATUS
            order_product.save()
        else:
            print('Order Product {} rendering failed. Order Product and Order STATUSes set to FAILED'.format(
                    order_product_id)
            )
            order_product.write_log(
                message='Order Product {} rendering failed. STATUS set to FAILED'.format(
                    order_product_id)
            )
            order_product.status = ORDER_PRODUCT_FAILED_STATUS
            order_product.save()
            order_product.order.write_log(
                message='Order Product {} rendering failed. Order STATUS set to FAILED'.format(
                    order_product_id)
            )
            order_product.order.status = ORDER_FAILED_STATUS
            order_product.order.save()

        print('RenderBot Process complete')

    except FileNotFoundError:
        print(f"Couldn't find file %s " % final_file)
