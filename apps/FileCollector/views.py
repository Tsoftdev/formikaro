# Formikaro.Collector.View
# Module 1
#
from apps.FormikoAudit.models import CameraSetting, LineItem, Shoot
from apps.FormikoBot.models import TaskPreset
from django.core import serializers
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Count, Sum, Q
from django.http import Http404

from django.core.management import call_command

from django.utils.html import format_html
from django.utils.safestring import mark_safe

from django.http import HttpResponse
from django.contrib import messages

from django.shortcuts import render
from django.views.decorators.http import require_http_methods
from django.shortcuts import redirect
from django.views.generic import TemplateView
from django.views.generic.list import ListView
from django.db.models import Max
from django.contrib.auth.models import User

from formikaro.utils import col_names_fo
from django_celery_beat.models import PeriodicTask, PeriodicTasks

from .models import Crew, File, Intake, Person, Project, ProjectVideo, UserRole, Video, OrderProduct, Language, Order, Asset, Company, Client, Product, ProjectManager, \
    ORDER_COMPLETE_STATUS, \
    ORDER_FAILED_STATUS, ORDER_READY_STATUS, ORDER_PENDING_STATUS, ORDER_ACTIVE_STATUS, ORDER_DELIVERED_STATUS, \
    ORDER_PRODUCT_FAILED_STATUS, ORDER_PRODUCT_ACTIVE_STATUS, ORDER_PRODUCT_READY_STATUS, ORDER_PRODUCT_IDLE_STATUS, \
    ORDER_PRODUCT_COMPLETE_STATUS, ORDER_PRODUCT_PENDING_STATUS, VIDEO_RENDERING, ORDER_PRODUCT_DELIVERED_STATUS, \
    ORDER_PRODUCT_RENDER_STATUS, VIDEO_UPLOADING_COMPLETE, VIDEO_UPLOADING_FAILED

from .models import PROJECT_COMPLETE_STATUS, PROJECT_DELIVERED_STATUS, PROJECT_PAID_STATUS

from .tasks import get_shop_orders
from apps.FormikoBot.models import TaskType, TASK_STATUS_COMPLETE
from apps.ProductManager.models import ProductImage, ProductImageText, Resolution, ProductBase, ProductText, VideoFormat

import json
import csv, io
from io import StringIO

from django.http import JsonResponse
from django.template.loader import render_to_string

import datetime
import pytz

from ..ProductManager.tasks import check_video_render_progress
from notifications.signals import notify



def all_files(request):
    myFiles = File.objects.annotate(number_of_answers=Count('intake'))
    return myFiles


# this is a dummy function to link to for all furture pages
class NotYetView(LoginRequiredMixin, TemplateView):
    login_url = '/accounts/login/'

    def get(self, request, *args, **kwargs):

        return render(request, 'Formikaro/notyet.html')

class BetaTestView(LoginRequiredMixin, TemplateView):
    login_url = '/accounts/login/'

    def prepare_data(self):
        context = {}

        #start_date = datetime.datetime.now() - datetime.timedelta(29)
        #start_date = start_date.replace(tzinfo=pytz.UTC)
        video_base_query = Video.objects.all()  # (created__gte=start_date)
        upload_total = video_base_query.count()
        upload_draft_1 = video_base_query.filter(Q(status=VIDEO_UPLOADING_COMPLETE) & Q(version='Draft_1')).count()
        upload_draft_2 = video_base_query.filter(Q(status=VIDEO_UPLOADING_COMPLETE) & Q(version='Draft_2')).count()
        upload_draft_3plus = video_base_query.filter(
            Q(status=VIDEO_UPLOADING_COMPLETE) & (~Q(version='Draft_1') & ~Q(version='Draft_2'))).count()
        upload_draft_final = video_base_query.filter(Q(status=VIDEO_UPLOADING_COMPLETE) & Q(version='FINAL')).count()

        upload_success = video_base_query.filter(status=VIDEO_UPLOADING_COMPLETE).count()
        upload_errors = video_base_query.filter(status=VIDEO_UPLOADING_FAILED).count()

        upload_success_percent = round(upload_success / upload_total * 100)
        upload_errors_percent = round(upload_errors / upload_total * 100)

        upload_draft_1_percent = round(upload_draft_1 / upload_total * 100)
        upload_draft_2_percent = round(upload_draft_2 / upload_total * 100)
        upload_draft_3plus_percent = round(upload_draft_3plus / upload_total * 100)
        upload_draft_final_percent = round(upload_draft_final / upload_total * 100)

        context = {
            'upload_total': upload_total,
            'upload_draft_1': upload_draft_1,
            'upload_draft_1_percent': upload_draft_1_percent,
            'upload_draft_2': upload_draft_2,
            'upload_draft_2_percent': upload_draft_2_percent,
            'upload_draft_3plus': upload_draft_3plus,
            'upload_draft_3plus_percent': upload_draft_3plus_percent,
            'upload_draft_final': upload_draft_final,
            'upload_draft_final_percent': upload_draft_final_percent,
            'upload_errors': upload_errors,
            'upload_errors_percent': upload_errors_percent,
            'upload_success': upload_success,
            'upload_success_percent': upload_success_percent,
        }

        return context

    def get(self, request, *args, **kwargs):
        return render(request, 'Formikaro/beta.html', self.prepare_data())

    def post(self, request, *args, **kwargs):
        return render(request, 'Formikaro/beta.html', self.prepare_data())


#Dashboard
class IndexView(LoginRequiredMixin, ListView):
    #login_url = '/accounts/login/'
    def get(self, request, *args, **kwargs):
        start_date = datetime.datetime.now() - datetime.timedelta(29)
        start_date = start_date.replace(tzinfo=pytz.UTC)
        orders_base_query = Order.objects.filter(created__gte=start_date)
        orders_total = orders_base_query.count()
        orders_ready = orders_base_query.filter(status=ORDER_READY_STATUS).count()
        orders_pending = orders_base_query.filter(status=ORDER_PENDING_STATUS).count()
        orders_active = orders_base_query.filter(status=ORDER_ACTIVE_STATUS).count()
        orders_failed = orders_base_query.filter(status=ORDER_FAILED_STATUS).count()
        orders_complete = orders_base_query.filter(status=ORDER_COMPLETE_STATUS).count()
        orders_delivered = orders_base_query.filter(status=ORDER_DELIVERED_STATUS).count()

        products_base_query = OrderProduct.objects.filter(order__created__gte=start_date)
        products_total = products_base_query.count()
        products_pending = products_base_query.filter(status=ORDER_PRODUCT_PENDING_STATUS).count()
        products_active = products_base_query.filter(status=ORDER_PRODUCT_ACTIVE_STATUS).count()
        products_ready = products_base_query.filter(status=ORDER_PRODUCT_READY_STATUS).count()
        products_idle = products_base_query.filter(status=ORDER_PRODUCT_IDLE_STATUS).count()
        products_failed = products_base_query.filter(status=ORDER_PRODUCT_FAILED_STATUS).count()
        products_complete = products_base_query.filter(status=ORDER_PRODUCT_COMPLETE_STATUS).count()
        products_delivered = products_base_query.filter(status=ORDER_PRODUCT_COMPLETE_STATUS).count()

        PeriodicTasks = PeriodicTask.objects.all()

        #video upload statistic
        video_base_query = Video.objects.all() #(created__gte=start_date)
        upload_total = video_base_query.count()
        upload_draft_1 = video_base_query.filter(Q(status=VIDEO_UPLOADING_COMPLETE) & Q(version='Draft_1')).count()
        upload_draft_2 = video_base_query.filter(Q(status=VIDEO_UPLOADING_COMPLETE) & Q(version='Draft_2')).count()
        upload_draft_3plus = video_base_query.filter(Q(status=VIDEO_UPLOADING_COMPLETE) & (~Q(version='Draft_1') & ~Q(version='Draft_2'))).count()
        upload_draft_final = video_base_query.filter(Q(status=VIDEO_UPLOADING_COMPLETE) & Q(version='FINAL')).count()

        upload_success = video_base_query.filter(status=VIDEO_UPLOADING_COMPLETE).count()
        upload_errors = video_base_query.filter(status=VIDEO_UPLOADING_FAILED).count()

        upload_success_percent = round(upload_success / upload_total * 100)
        upload_errors_percent = round(upload_errors / upload_total * 100)

        upload_draft_1_percent = round(upload_draft_1 / upload_total *100 )
        upload_draft_2_percent = round(upload_draft_2 / upload_total * 100)
        upload_draft_3plus_percent = round(upload_draft_3plus / upload_total * 100)
        upload_draft_final_percent = round(upload_draft_final / upload_total * 100)

        orders_incoming_latest = Order.objects.annotate(
            products_count=Count('order_products', distinct=True),
            total_running_time=Sum('order_products__product__runtime')
        ).order_by('-created')[:5]

        #orders_pending_latest = Order.objects.annotate(
        #        products_count=Count('order_products', distinct=True),
        #        total_running_time=Sum('order_products__product__runtime')
        #   ).filter(status=ORDER_PENDING_STATUS).order_by('-created')[:5]

        orders_complete_latest = Order.objects.annotate(
            products_count=Count('order_products', distinct=True),
            total_running_time=Sum('order_products__product__runtime')
        ).filter(status=ORDER_COMPLETE_STATUS).order_by('-created')[:5]

        latest_intakes_list = Intake.objects.annotate(
            files_count=Count('files', distinct=True),
            total_size=Sum('files__size')
        ).order_by('-created')[:5]

        latest_videos_list = Video.objects.order_by('-created')[:10]

        #dont show paid projects
        latest_projects_list = Project.objects.filter(~Q(status=PROJECT_PAID_STATUS)).order_by('-updated')[:20]

        if orders_total != 0:
            orders_ready_percent = round(orders_ready/orders_total * 100)
            orders_active_percent = round(orders_active/orders_total * 100)
            orders_failed_percent = round(orders_failed/orders_total * 100)
            orders_complete_percent = round(orders_complete/orders_total * 100)
            orders_delivered_percent = round(orders_delivered/orders_total * 100)
            orders_pending_percent = round(orders_pending/orders_total * 100)
        else:
            orders_ready_percent = 0
            orders_active_percent = 0
            orders_failed_percent = 0
            orders_complete_percent = 0
            orders_delivered_percent = 0
            orders_pending_percent = 0

        context = {
            'periodic_tasks' : PeriodicTasks,
            'orders_pending' : orders_pending,
            'products_pending' : products_pending,
            'orders_active' : orders_active,
            'products_active' : products_active,
            'orders_failed': orders_failed,
            'products_failed': products_failed,
            'orders_complete' : orders_complete,
            'products_complete' : products_complete,
            'orders_delivered': orders_delivered,
            'products_delivered': products_delivered,
            'orders': True,
            'orders_total': orders_total,
            'orders_ready': orders_ready,
            'products_total': products_total,
            'products_idle': products_idle,
            'products_ready': products_ready,

            'upload_total': upload_total,
            'upload_draft_1': upload_draft_1,
            'upload_draft_1_percent': upload_draft_1_percent,
            'upload_draft_2': upload_draft_2,
            'upload_draft_2_percent': upload_draft_2_percent,
            'upload_draft_3plus': upload_draft_3plus,
            'upload_draft_3plus_percent': upload_draft_3plus_percent,
            'upload_draft_final': upload_draft_final,
            'upload_draft_final_percent': upload_draft_final_percent,
            'upload_errors' : upload_errors,
            'upload_errors_percent': upload_errors_percent,
            'upload_success':upload_success,
            'upload_success_percent': upload_success_percent,

            'orders_ready_percent': orders_ready_percent,
            'orders_active_percent': orders_active_percent,
            'orders_failed_percent': orders_failed_percent,
            'orders_complete_percent': orders_complete_percent,
            'orders_delivered_percent': orders_delivered_percent,
            'orders_pending_percent': orders_pending_percent,

            'orders_incoming_latest': orders_incoming_latest,
            'orders_complete_latest': orders_complete_latest,
            'latest_projects_list' : latest_projects_list,
            'latest_intakes_list': latest_intakes_list,
            'latest_videos_list': latest_videos_list,
            'start_date': start_date.isoformat()

        }
        return render(request, 'Formikaro/dashboard.html', context)
    def post(self, request, *args, **kwargs):
        #latest_intakes_list = Intake.objects.order_by('-created')[:100]
        #context = {'latest_order_list': latest_intakes_list}
        #return render(request, 'Formikaro/dashboard.html', context)
        start_date = request.POST.get('start_date')
        end_date = request.POST.get('end_date')

        orders_base_query = Order.objects.filter(created__range=[start_date, end_date])
        orders_total = orders_base_query.count()
        orders_ready = orders_base_query.filter(status=ORDER_READY_STATUS).count()
        orders_pending = orders_base_query.filter(status=ORDER_PENDING_STATUS).count()
        orders_active = orders_base_query.filter(status=ORDER_ACTIVE_STATUS).count()
        orders_failed = orders_base_query.filter(status=ORDER_FAILED_STATUS).count()
        orders_complete = orders_base_query.filter(status=ORDER_COMPLETE_STATUS).count()
        orders_delivered = orders_base_query.filter(status=ORDER_DELIVERED_STATUS).count()


        products_base_query = OrderProduct.objects.filter(order__created__range=[start_date, end_date])
        products_total = products_base_query.count()
        products_pending = products_base_query.filter(status=ORDER_PRODUCT_PENDING_STATUS).count()
        products_active = products_base_query.filter(status=ORDER_PRODUCT_ACTIVE_STATUS).count()
        products_ready = products_base_query.filter(status=ORDER_PRODUCT_READY_STATUS).count()
        products_idle = products_base_query.filter(status=ORDER_PRODUCT_IDLE_STATUS).count()
        products_failed = products_base_query.filter(status=ORDER_PRODUCT_FAILED_STATUS).count()
        products_complete = products_base_query.filter(status=ORDER_PRODUCT_COMPLETE_STATUS).count()
        products_delivered = products_base_query.filter(status=ORDER_PRODUCT_COMPLETE_STATUS).count()

        # video upload statistic
        video_base_query = Video.objects.filter(created__range=[start_date, end_date])
        upload_total = video_base_query.count()
        upload_draft_1 = video_base_query.filter(Q(status=VIDEO_UPLOADING_COMPLETE) & Q(version='Draft_1')).count()
        upload_draft_2 = video_base_query.filter(Q(status=VIDEO_UPLOADING_COMPLETE) & Q(version='Draft_2')).count()
        upload_draft_3plus = video_base_query.filter(
            Q(status=VIDEO_UPLOADING_COMPLETE) & (~Q(version='Draft_1') & ~Q(version='Draft_2'))).count()
        upload_draft_final = video_base_query.filter(Q(status=VIDEO_UPLOADING_COMPLETE) & Q(version='FINAL')).count()

        upload_success = video_base_query.filter(status=VIDEO_UPLOADING_COMPLETE).count()
        upload_errors = video_base_query.filter(status=VIDEO_UPLOADING_FAILED).count()
        if upload_total > 0 :
            upload_success_percent = round(upload_success / upload_total * 100)
            upload_errors_percent = round(upload_errors / upload_total * 100)

            upload_draft_1_percent = round(upload_draft_1 / upload_total * 100)
            upload_draft_2_percent = round(upload_draft_2 / upload_total * 100)
            upload_draft_3plus_percent = round(upload_draft_3plus / upload_total * 100)
            upload_draft_final_percent = round(upload_draft_final / upload_total * 100)
        else:
            upload_success_percent = 0
            upload_errors_percent = 0
            upload_draft_1_percent = 0
            upload_draft_2_percent = 0
            upload_draft_3plus_percent = 0
            upload_draft_final_percent = 0




        PeriodicTasks = PeriodicTask.objects.all()

        orders_incoming_latest= Order.objects.annotate(
            products_count=Count('order_products', distinct=True),
            total_running_time=Sum('order_products__product__runtime')
        ).order_by('-created')[:5]

        #orders_pending_latest = Order.objects.annotate(
        #        products_count=Count('order_products', distinct=True),
        #        total_running_time=Sum('order_products__product__runtime')
        #   ).filter(status=ORDER_PENDING_STATUS).order_by('-created')[:5]

        orders_complete_latest = Order.objects.annotate(
            products_count=Count('order_products', distinct=True),
            total_running_time=Sum('order_products__product__runtime')
        ).filter(status=ORDER_COMPLETE_STATUS).order_by('-created')[:5]

        latest_intakes_list = Intake.objects.annotate(
            files_count=Count('files', distinct=True),
            total_size=Sum('files__size')
        ).order_by('-created')[:5]

        latest_videos_list = Video.objects.order_by('-created')[:5]

        if orders_total != 0:
            orders_ready_percent = round(orders_ready/orders_total * 100)
            orders_active_percent = round(orders_active/orders_total * 100)
            orders_failed_percent = round(orders_failed/orders_total * 100)
            orders_complete_percent = round(orders_complete/orders_total * 100)
            orders_delivered_percent = round(orders_delivered/orders_total * 100)
            orders_pending_percent = round(orders_pending/orders_total * 100)
        else:
            orders_ready_percent = 0
            orders_active_percent = 0
            orders_failed_percent = 0
            orders_complete_percent = 0
            orders_delivered_percent = 0
            orders_pending_percent = 0

        context = {
            'periodic_tasks' : PeriodicTasks,
            'orders_pending' : orders_pending,
            'products_pending' : products_pending,
            'orders_active' : orders_active,
            'products_active' : products_active,
            'orders_failed': orders_failed,
            'products_failed': products_failed,
            'orders_complete' : orders_complete,
            'products_complete' : products_complete,
            'orders_delivered': orders_delivered,
            'products_delivered': products_delivered,
            'orders': True,
            'orders_total': orders_total,
            'orders_ready': orders_ready,
            'products_total': products_total,
            'products_idle': products_idle,
            'products_ready': products_ready,

            'orders_ready_percent': orders_ready_percent,
            'orders_active_percent': orders_active_percent,
            'orders_failed_percent': orders_failed_percent,
            'orders_complete_percent': orders_complete_percent,
            'orders_delivered_percent': orders_delivered_percent,
            'orders_pending_percent': orders_pending_percent,

            'upload_total' : upload_total,
            'upload_draft_1': upload_draft_1,
            'upload_draft_1_percent': upload_draft_1_percent,
            'upload_draft_2': upload_draft_2,
            'upload_draft_2_percent': upload_draft_2_percent,
            'upload_draft_3plus': upload_draft_3plus,
            'upload_draft_3plus_percent': upload_draft_3plus_percent,
            'upload_draft_final': upload_draft_final,
            'upload_draft_final_percent': upload_draft_final_percent,
            'upload_errors': upload_errors,
            'upload_errors_percent': upload_errors_percent,
            'upload_success': upload_success,
            'upload_success_percent': upload_success_percent,

            'orders_incoming_latest': orders_incoming_latest,
            'orders_complete_latest': orders_complete_latest,
            'latest_intakes_list': latest_intakes_list,
            'latest_videos_list': latest_videos_list,
            'start_date': start_date,
            'end_date': end_date
        }
        return render(request, 'Formikaro/dashboard.html', context)


# INDEX VIEW FOR INTAKES
class IntakeIndexView(LoginRequiredMixin, TemplateView):
    login_url = '/accounts/login/'

    def get(self, request, *args, **kwargs):
        #latest_intakes_list = Intake.objects.order_by('-created')[:100]
        latest_intakes_list = Intake.objects.annotate(
            files_count=Count('files', distinct=True),
            total_size=Sum('files__size')
        ).order_by('-created')[:100]
        context = {'latest_intakes_list': latest_intakes_list}
        context['clients'] = Client.objects.all().order_by('lastname')
        return render(request, 'Intake/intake_index.html', context)

def changeAjaxIntakeClient(request):
    if request.method == 'POST':
        client_id = request.POST['client_id']
        intake_id = request.POST['intake_id']
        obj = Intake.objects.get(id=intake_id)
        obj.client_id = client_id
        obj.order = None
        obj.save()
        print(client_id)

        return JsonResponse({"statusCode":2})
    else:
        return JsonResponse({"statusCode":1})

def getAjaxIntakeOrder(request):
    if request.method == 'POST':
        client_id = request.POST['client_id']
        order_objs = Order.objects.filter(Q(client_id=client_id) & ~Q(status=ORDER_COMPLETE_STATUS) & ~Q(status=ORDER_DELIVERED_STATUS)).values_list('id', flat=True)


        return JsonResponse({"statusCode":2, "order_objs": list(order_objs)})
    else:
        return JsonResponse({"statusCode":1})

def changeAjaxIntakeOrder(request):
    if request.method == 'POST':
        order_id = request.POST['order_id']
        intake_id = request.POST['intake_id']
        obj = Intake.objects.get(id=intake_id)
        obj.order_id = order_id
        obj.save()

        return JsonResponse({"statusCode":2})
    else:
        return JsonResponse({"statusCode":1})

def getAjaxIntakeProject(request):
    if request.method == 'POST':
        client_id = request.POST['client_id']
        project_objs = Project.objects.filter(Q(client_id=client_id) & ~Q(status=PROJECT_COMPLETE_STATUS) & ~Q(status=PROJECT_DELIVERED_STATUS) & ~Q(status=PROJECT_PAID_STATUS)).values_list('id', 'name')
        return JsonResponse({"statusCode":2, "project_objs": list(project_objs)})
    else:
        return JsonResponse({"statusCode":1})

def changeAjaxIntakeProject(request):
    if request.method == 'POST':
        project_id = request.POST['project_id']
        intake_id = request.POST['intake_id']
        obj = Intake.objects.get(id=intake_id)
        obj.project_id = project_id
        obj.save()

        return JsonResponse({"statusCode":2})
    else:
        return JsonResponse({"statusCode":1})
def changeAjaxIntakeRemark(request):
    file_id = request.POST['file_id']
    remark = request.POST['remark']
    obj = File.objects.get(id=file_id)
    obj.remark = remark
    obj.save()
    return JsonResponse({"statusCode":2})

# DETAIL VIEW FOR INTAKES
class IntakePageView(LoginRequiredMixin, TemplateView):
    def get(self, request, **kwargs):
        intake_id = kwargs.get('intake_id', None)
        try:
            intake = Intake.objects.select_related().get(id=intake_id)
        except Intake.DoesNotExist:
            raise Http404('No Intake matches the given query.')

        intake_files = File.objects.filter(intake_id=intake_id)
        intake_files_count = File.objects.filter(intake_id=intake_id).count()
        order_products = OrderProduct.objects.select_related().filter(order_id=intake.order_id)
        context = {
            'intake': intake,
            'intake_files': list(intake_files) if intake_files else None,
            'order_products': list(order_products),
            'intake_files_count': intake_files_count
        }

        return render(request, 'Intake/intake_detail.html', context)


class CreateWizard(LoginRequiredMixin, TemplateView):
    login_url = '/accounts/login/'
    def get(self, request, *args, **kwargs):
        #latest_orders_list = Order.objects.annotate(
        #    products_count=Count('order_products', distinct=True),
        #    total_running_time=Sum('order_products__product__runtime')
        #).order_by('-created')[:100]
        companies = Company.objects.all().order_by('name')
        #countries = Countries.objects.all().order_by('name') # not yet implemented
        countries = ''
        languages = Language.objects.all().order_by('name')
        context = {'companies': companies, 'languages':languages, 'countries': countries}
        return render(request, 'Wizard/create.html', context)

# INDEX VIEW FOR ORDERS
class OrderIndexView(LoginRequiredMixin, TemplateView):
    login_url = '/accounts/login/'

    def get(self, request, *args, **kwargs):
        latest_orders_list = Order.objects.annotate(
            products_count=Count('order_products', distinct=True),
            total_running_time=Sum('order_products__product__runtime')
        ).order_by('-created')[:100]
        context = {'latest_orders_list': latest_orders_list}
        return render(request, 'Orders/order_index.html', context)


#filter view for all orders having one given status
class OrderStatusView(LoginRequiredMixin, TemplateView):
    login_url = '/accounts/login/'

    def get(self, request, **kwargs):
        filter_status = kwargs.get('status', None)
        filter_status = filter_status.upper()

        if filter_status == ORDER_COMPLETE_STATUS or filter_status == ORDER_FAILED_STATUS or filter_status == ORDER_PENDING_STATUS or filter_status == ORDER_ACTIVE_STATUS or filter_status == ORDER_DELIVERED_STATUS or filter_status == ORDER_READY_STATUS:

            status_orders_list = Order.objects.annotate(
                products_count=Count('order_products', distinct=True),
                total_running_time=Sum('order_products__product__runtime')
            ).filter(status=filter_status).order_by('-created')[:100]

            context = {'status_orders_list': status_orders_list,
                       'status' : filter_status }
            return render(request, 'Orders/order_status.html', context)
        elif filter_status == "OPEN":
            status_orders_list = Order.objects.annotate(
                products_count=Count('order_products', distinct=True),
                total_running_time=Sum('order_products__product__runtime')
            ).filter(Q(status=ORDER_ACTIVE_STATUS) | Q(status=ORDER_READY_STATUS)).order_by('-created')[:100]

            context = {'status_orders_list': status_orders_list,
                       'status' : filter_status }
            return render(request, 'Orders/order_status.html', context)
        elif filter_status == "DONE":
            status_orders_list = Order.objects.annotate(
                products_count=Count('order_products', distinct=True),
                total_running_time=Sum('order_products__product__runtime')
            ).filter(Q(status=ORDER_COMPLETE_STATUS) | Q(status=ORDER_DELIVERED_STATUS)).order_by('-created')[:100]

            context = {'status_orders_list': status_orders_list,
                       'status' : filter_status }
            return render(request, 'Orders/order_status.html', context)
        else:
            raise Http404('No product status [%s] found' % filter_status)


# DETAIL VIEW FOR ORDERS
class OrderPageView(LoginRequiredMixin, TemplateView):
    def get(self, request, **kwargs):
        order_id = kwargs.get('order_id', None)
        order = Order.objects.select_related().filter(id=order_id).annotate(
            products_count=Count('order_products', distinct=True),
            total_running_time=Sum('order_products__product__runtime'),
            completed_products_count=Count('order_products', distinct=True,
                                           filter=Q(order_products__status__iexact=ORDER_PRODUCT_COMPLETE_STATUS)
                                                  | Q(order_products__status__iexact=ORDER_PRODUCT_DELIVERED_STATUS)
                                           )
        ).first()

        if not order:
            raise Http404('No Order matches the given query.')

        #let's see if the order folder exists already

        #intake_files = File.objects.filter(order_id=order_id)
        intake = Intake.objects.select_related().filter(order_id=order_id).first()
        order_products = OrderProduct.objects.select_related().filter(order_id=order_id)
        orderprod_ids = order_products.values_list('id', flat=True).distinct()
        order_videos = Video.objects.filter(order_product_id__in=orderprod_ids)
        videos_count = order_videos.filter(status="PENDING").count()
        videos_currently_rendering = {}

        poll_for_videos = False
        for order_prod in list(order_products):
            videos_render_progress_list = []
            rendering_videos_qs = Video.objects.filter(status=VIDEO_RENDERING, order_product_id=order_prod.id)

            if rendering_videos_qs:
                poll_for_videos = True
                for video in list(rendering_videos_qs):
                    render_progress, successful_query, ignored_video = check_video_render_progress(video.id)
                    if successful_query and not ignored_video:
                        videos_render_progress_list.append(
                            {'video_id': video.id, 'progress': render_progress}
                        )

            videos_currently_rendering.update({order_prod.id: videos_render_progress_list})
        is_attached_video = False
        if videos_count > 0:
            is_attached_video = True

        context = {
            'order': order,
            'intake': intake,
            'order_products': list(order_products),
            'is_attached_video': is_attached_video,
            'videos_currently_rendering': videos_currently_rendering,
            'poll_for_videos': json.dumps(poll_for_videos)
        }

        return render(request, 'Orders/order_detail.html', context)


def updateOrderVideosRenderProgressAjaxView(request):
    order_id = request.POST['order_id']
    orderprod_ids = OrderProduct.objects.filter(order_id=order_id).values_list('id', flat=True).distinct()

    videos_currently_rendering = []

    for order_prod_id in list(orderprod_ids):
        videos_render_progress_list = []
        for video in Video.objects.filter(status=VIDEO_RENDERING, order_product_id=order_prod_id):
            render_progress, successful_query, ignored_video = check_video_render_progress(video.id)
            if successful_query and not ignored_video:
                videos_render_progress_list.append(
                    {'video_id': video.id, 'progress': render_progress, 'successful_query': successful_query}
                )

        # Get the latest data of the video after checking for render progress because it could have changed
        refreshed_order_prod = OrderProduct.objects.get(id=order_prod_id)
        order_prod_object = {
            'order_prod_id': order_prod_id,
            'order_product_status': refreshed_order_prod.status,
            'order_folder_created': refreshed_order_prod.order_folder_created(),
            'json': refreshed_order_prod.json, 'rendering_videos': videos_render_progress_list
        }
        videos_currently_rendering.append(order_prod_object)

    return JsonResponse({'data': json.dumps(videos_currently_rendering)})

def removeAjaxLinkedProjectVideo(request):
    video_id = request.POST['video_id']
    project_video_id = request.POST['project_video_id']
    response = ''
    try:
        video = Video.objects.get(id=video_id)
        project_video = ProjectVideo.objects.get(id=project_video_id)
        project_video.videos.remove(video)
        response = 'Video %s sucessfully removed from %s ' % (video.unique_fn, project_video.name)
    except Exception as e:
        response = 'Error removing project video (%s) (%s from %s) ' % (e, video_id, project_video_id)

    return HttpResponse(response)

def consolidateAjaxProjectVideos(request):
    project_id = request.POST['project_id']
    project = Project.objects.get(id=project_id)

    response = ''
    video_count = 0
    try:
        for project_video in project.project_videos.all():
            videos = Video.objects.filter(Q(unique_fn__contains=project_video.name) & Q(project=project))
            for video in videos:
                video_count += 1
                project_video.videos.add(video)
                project = 0 #error
        response = f'Successfully consolidated {video_count} to projectvideo'
    except Exception as e:
        response = 'Error consolidating (%s)' % e
    return HttpResponse(response)

# ajax call delete OrderProduct, related assets and folder
def deleteAjaxOrderProduct(request):
    order_product_id = request.POST['order_product_id']
    order_id = request.POST['order_id']

    orderprod_obj = OrderProduct.objects.get(id=order_product_id)
    if orderprod_obj.order_folder_created():
        orderprod_obj.remove_folder()

    orderprod_obj.assets.clear()
    orderprod_obj.delete()

    order_products = OrderProduct.objects.select_related().filter(order_id=order_id)
    return render(request, 'Orders/order_detail_product_ajax.html', {'order_products': order_products})

# ajax call upload_orders command
def uploadAjaxOrders(request):
    try:
        order_id = request.POST['order_id']
        response=''
        #response = 'this we will do [%s]' % order_id #DEBUG
    except:
        response = 'An error has occurred! (no order_id?)'

    #debug lets just run doorman for now
    with io.StringIO() as out:
        call_command('upload_orders', '-o', order_id, stdout=out)
        response += out.getvalue()

    #response = json.dumps(response)
    return HttpResponse(response)

def createOrderProductFolder(request):
    try:
        order_product_id = request.POST['order_product_id']
        order_id = request.POST['order_id']
        create_flag = request.POST['create_flag']
        response = ''
        #response = 'this we will do [%s]' % order_product_id
    except:
        response = 'An error has occurred! (no order_id?)'

    #debug lets just run doorman for now
    with io.StringIO() as out:
        #if we get the create flag we will run the command with the --create option
        if create_flag == 'true':
            call_command('assembler', '-op', order_product_id, '--create', stdout=out)
        else:
            call_command('assembler', '-op', order_product_id, stdout=out)
        response += out.getvalue()

    #response = json.dumps(response)
    order_products = OrderProduct.objects.select_related().filter(order_id=order_id)
    html = render_to_string('Orders/order_detail_product_ajax.html', {'order_products': order_products}, request=request)
    return JsonResponse({"response":response, "html": html})

def createOrder(request):
    if request.method == 'GET':
        create_flag = ''
        prepare_flag = ''
        try:
            order_id = request.GET['order_id']
            create_flag = request.GET['create_flag']
            prepare_flag = request.GET['prepare_flag']
            response = ''
            # response = 'this we will do [%s]' % order_id
        except:
            response = 'An error has occurred! (no order_id?)'

        #debug lets just run doorman for now
        with io.StringIO() as out:
            #if we get the create flag we will run the command with the --create option
            if create_flag == 'true':
                call_command('assembler', '-o', order_id, '--create', stdout=out)
            elif prepare_flag == 'true':
                call_command('assembler', '-o', order_id, '--prepare', stdout=out)
            else:
                call_command('assembler', '-o', order_id, stdout=out)
            response += out.getvalue()

        #response = json.dumps(response)
        return HttpResponse(response)
    else:
        return HttpResponse("Request method is not a GET")

#under construction
def renderAjaxOrderProduct(request):
    if request.method == 'GET':
        order_product_id = request.GET['order_product_id']
        if not order_product_id:
            response = "No OrderProduct ID given! [%s] " % order_product_id
            return HttpResponse(response)
        response = ''
        with io.StringIO() as out:
            call_command('assembler', '-op', order_product_id, '--render', stdout=out)
            response += out.getvalue()

        return HttpResponse(response)
    else:
        return HttpResponse("Request method is not a GET")

def getAjaxEditOrderProdAsset(request):
    order_prod_id = request.POST.get('order_prod_id')
    line = OrderProduct.objects.select_related().get(id=order_prod_id)

    return render(request, 'Orders/order_asset_template.html', {'line': line})

def changeAjaxEditOrderProdAsset(request):
    json_data = json.loads(request.POST.get('data'))
    order_prod_id = json_data["order_prod_id"]
    order_id = json_data["order_id"]
    removeable_assets = json_data["removeable_assets"]
    changed_assets = json_data["changed_assets"]

    for asset in removeable_assets:
        print(asset["asset_id"], asset["global"])
        if asset["global"] == "0":
            Asset.objects.get(id=asset["asset_id"]).delete()
        else:
            line = OrderProduct.objects.select_related().get(id=order_prod_id)
            line.assets.remove(asset["asset_id"])

    for asset in changed_assets:
        print(asset["asset_id"], asset["asset_value"])
        obj = Asset.objects.get(id=asset["asset_id"])
        obj.value = asset["asset_value"]
        obj.save()
    return JsonResponse({"statusCode":2})

#add order manually page
class OrderAddView(LoginRequiredMixin, TemplateView):
    def get(self, request, *args, **kwargs):
        #list all companies (the clients will be loaded via AJAX)
        client_id =  kwargs.get('client_id', None)
        try:
            this_client = Client.objects.get(id=client_id)
            this_company = this_client.company
        except:
            this_client = None
            this_company = None

        companies = Company.objects.all()

        #show all products that are either active or at least have an FSIN
        products = Product.objects.filter(Q(is_active=True) & ~Q(fsin=None))


        context = {
            'companies': companies,
            'products' : products,
            'sel_company': this_company,
            'sel_client': this_client
        }
        return render(request, 'Orders/add_order.html', context)

#ajax calls for create order ###  Zita added ###
def createAjaxOrder(request):
    if request.method == 'POST':
        json_data = json.loads(request.POST.get('data'))
        client_id = json_data["client_id"]
        company_id = json_data["company_id"]
        prod_data = json_data["prod_data"]
        #### create order object ####
        order_obj = Order.objects.create(client_id=client_id, origin='MANUAL')
        order_obj.placed = datetime.datetime.now()
        order_obj.save()

        for key in prod_data:
            prod_id = key.replace('a', '')
            # asset_ids = prod_data[key]["existAsset"]

            asset_ids = []

            for item in prod_data[key]["new_asset"]:
                #### just link id ###
                if item["value"] == item["org_value"] and str(item["owner_type"]) == str(item["org_type"]):
                    asset_ids.append(item["asset_id"])
                else:
                    #### create new asset ####
                    if item["owner_type"] == "1":
                        asset_obj = Asset.objects.create(
                            name=item["asset_name"],
                            value=item["value"],
                            assettype_id=item["asset_type_id"],
                            company_owner_id=company_id
                        )
                        company_obj = Company.objects.get(id=company_id)
                        company_obj.assets.add(asset_obj.id)
                    elif item["owner_type"] == "0":
                        asset_obj = Asset.objects.create(
                            name=item["asset_name"],
                            value=item["value"],
                            assettype_id=item["asset_type_id"],
                            client_owner_id=client_id
                        )
                        client_obj = Client.objects.get(id=client_id)
                        client_obj.assets.add(asset_obj.id)

                    asset_ids.append(asset_obj.id)
            #### create OrderProduct ####
            prod_obj = OrderProduct.objects.create(order_id=order_obj.id, product_id=prod_id)
            for i in asset_ids:
                prod_obj.assets.add(i)
        return JsonResponse({"statusCode":2}) # Sending an success response
    else:
        return JsonResponse({"statusCode":1})

    #ajax calls for add order page
def selectClients(request):
    if request.method == 'GET':
        company_id = request.GET['company_id']

        company = Company.objects.get(pk=company_id)
        company_assets = []
        for item in company.assets.all():
            company_assets.append({'id': item.id, 'name': item.name, 'value': item.value, 'maxlength': item.assettype.maxlength})

        company_assets = json.dumps(company_assets)

        clients = Client.objects.filter(company=company_id) #getting the liked posts

        clients_data = []
        #make a nice json object for the <select> field to get populated
        for client in clients:
            data = {}
            data["id"] = client.id
            data["name"] = client.firstname + ' ' + client.lastname

            client_assets = []
            for item in client.assets.all():
                client_assets.append({'id': item.id, 'name': item.name, 'value': item.value, 'maxlength': item.assettype.maxlength})

            client_assets = json.dumps(client_assets)

            data["assets"] = client_assets
            clients_data.append(data)



        return JsonResponse({"statusCode":2, "clients": clients_data, "company_assets": company_assets}) # Sending an success response
    else:
        return JsonResponse({"statusCode":1, "message":"Request method is not a GET"})

# ajax calls change status order
def changeAjaxStatusOrder(request):
    if request.method == 'POST':
        order_id = request.POST['order_id']
        status = request.POST['status']
        order_obj = Order.objects.get(id=order_id)
        order_obj.status = status
        order_obj.save()

        return JsonResponse({"statusCode":2}) # Sending an success response
    else:
        return JsonResponse({"statusCode":1})

    # ajax calls change status orderproduct
def changeAjaxStatusOrderProduct(request):
    if request.method == 'POST':
        order_prod_id = request.POST['order_prod_id']
        status = request.POST['status']
        order_obj = OrderProduct.objects.get(id=order_prod_id)
        order_obj.status = status
        order_obj.save()

        return JsonResponse({"statusCode":2}) # Sending an success response
    else:
        return JsonResponse({"statusCode":1})

# ajax calls change status orderproduct
def changeAjaxStatusProject(request):
    if request.method == 'POST':
        project_id = request.POST['project_id']
        status = request.POST['status']
        order_obj = Project.objects.get(id=project_id)
        order_obj.status = status
        order_obj.save()

        return JsonResponse({"statusCode":2}) # Sending an success response
    else:
        return JsonResponse({"statusCode":1})

# INDEX VIEW FOR VIDEOS
class VideoIndexView(LoginRequiredMixin, TemplateView):
    login_url = '/accounts/login/'

    def get(self, request, *args, **kwargs):
        videos = Video.objects.order_by('-created')[:100]
        context = {'videos': videos}
        return render(request, 'Videos/video_index.html', context)

# DETAIL VIEW FOR VIDEO
class VideoPageView(LoginRequiredMixin, TemplateView):
    def get(self, request, **kwargs):
        video_id = kwargs.get('video_id', None)
        video = Video.objects.filter(id=video_id).first()
        if not video:
            raise Http404('No client data matches the given query.')

        context = {
            'video': video,
        }

        return render(request, 'Videos/video_detail.html', context)

# INDEX VIEW FOR CLIENTS
class ClientIndexView(LoginRequiredMixin, TemplateView):
    login_url = '/accounts/login/'

    def get(self, request, *args, **kwargs):
        latest_clients_list = Client.objects.annotate(
            orders_count=Count('orders', distinct=True),
            open_orders_count=Count(
                'orders', distinct=True, filter=Q(
                    orders__status__in=[ORDER_ACTIVE_STATUS, ORDER_PENDING_STATUS])),
            completed_orders_count=Count(
                'orders', distinct=True, filter=Q(
                    orders__status__in=[ORDER_DELIVERED_STATUS, ORDER_COMPLETE_STATUS])),
            failed_orders_count=Count(
                'orders', distinct=True, filter=Q(
                    orders__status__in=[ORDER_FAILED_STATUS])
            )
        ).order_by('-created')[:100]
        context = {'latest_clients_list': latest_clients_list}
        return render(request, 'Clients/client_index.html', context)


# DETAIL VIEW FOR CLIENTS
class ClientPageView(LoginRequiredMixin, TemplateView):
    def get(self, request, **kwargs):
        client_id = kwargs.get('client_id', None)
        client = Client.objects.select_related().annotate(
            pending_products_count=Count(
                'orders__order_products', distinct=True,
                filter=Q(orders__order_products__status__iexact=ORDER_PENDING_STATUS)
            )
        ).filter(id=client_id).first()
        purchased_products = OrderProduct.objects.filter(order__client_id=client_id).exclude(status=ORDER_FAILED_STATUS) \
            .aggregate(total=Sum('product__price'))
        if not client:
            raise Http404('No client data matches the given query.')

        client_order_products = OrderProduct.objects.select_related().filter(order__client_id=client.id)

        context = {
            'client': client,
            'client_order_products': client_order_products,
            'purchased_products_total': purchased_products['total']
        }

        return render(request, 'Clients/client_detail.html', context)

#sub page for detail page 'client' showing all it's orders
class ClientOrdersView(LoginRequiredMixin, TemplateView):
    def get(self, request, **kwargs):
        client_id = kwargs.get('client_id', None)
        client = Client.objects.get(id=client_id)
        #client_order_list = Order.objects.filter(client_id=client_id)
        client_order_list = Order.objects.annotate(
            products_count=Count('order_products', distinct=True),
            total_running_time=Sum('order_products__product__runtime')
        ).filter(client_id=client_id).order_by('-created')[:100]

        context = {'client': client,
                   'client_order_list' : client_order_list}
        return render(request, 'Clients/client_orders.html', context)

#sub page for detail page 'client' showing all it's assets
class ClientAssetsView(LoginRequiredMixin, TemplateView):
    def get(self, request, **kwargs):
        client_id = kwargs.get('client_id', None)
        client = Client.objects.get(id=client_id)

        #this is not working correctly.. it should display assets that have been chose not all the ones that exist and could be chosen
        #client_available_assets = Asset.objects.filter(  Q(company_owner__isnull=True) | Q(company_owner=client.company.id)  )

        global_assets = list(Asset.objects.filter(Q(client_owner__isnull=True) & Q(company_owner__isnull=True)).values('id', 'name', 'value'))

        tmp_global_assets = global_assets.copy()

        client_available_assets = client.assets.all()
        for gb_asset in global_assets:
            for cl_asset in client_available_assets:
                if gb_asset["id"] == cl_asset.id:
                    tmp_global_assets.remove(gb_asset)

        company_available_assets = client.company.assets.all()
        client_assets = client.client_owned_assets.all()

        context = {
            'client': client,
            'global_available_assets': tmp_global_assets,
            'client_assets': client_assets,
            'client_available_assets': client_available_assets,
            'company_available_assets' : company_available_assets,
        }
        return render(request, 'Clients/client_assets.html', context)

#ajax calls for add global asset to client ###  Zita added ###
def addAjaxAssetToClient(request):
    if request.method == 'POST':
        gb_asset_ids = request.POST.getlist("gb_asset_ids[]")
        client_id = request.POST['client_id']
        client_obj = Client.objects.get(id=client_id)
        for asset_id in gb_asset_ids:
            client_obj.assets.add(asset_id)

        return JsonResponse({"statusCode":2}) # Sending an success response
    else:
        return JsonResponse({"statusCode":1})

    #not implemented yet (empty view)
class ClientBillingView(LoginRequiredMixin, TemplateView):
    def get(self, request, **kwargs):
        client_id = kwargs.get('client_id', None)
        client = Client.objects.get(id=client_id)
        context = {'client': client,}
        return render(request, 'Clients/client_billing.html', context)

#not implemented yet (empty view)
class ClientVideosView(LoginRequiredMixin, TemplateView):

    def get(self, request, **kwargs):
        client_id = kwargs.get('client_id', None)
        client = Client.objects.get(id=client_id)
        context = {'client': client,}
        return render(request, 'Clients/client_videos.html', context)

#INDEX VIEW FOR COMPANIES
class CompanyIndexView(LoginRequiredMixin, TemplateView):
    login_url = '/accounts/login/'

    def get(self, request, *args, **kwargs):
        company_list = Company.objects.order_by('-created')[:100]
        context = {'company_list': company_list}
        return render(request, 'Companies/company_index.html', context)

#Detail VIEW FOR COMPANIES
class CompanyPageView(LoginRequiredMixin, TemplateView):
    def get(self, request, **kwargs):
        company_id = kwargs.get('company_id', None)
        try:
            this_company = Company.objects.get(id=company_id)
        except:
            raise Http404('No Company matches the given query.')

        #company_clients = Client.objects.select_related().filter(company=company_id)
        company_clients = Client.objects.annotate(
            orders_count=Count('orders', distinct=True),
            open_orders_count=Count(
                'orders', distinct=True, filter=Q(
                    orders__status__in=[ORDER_ACTIVE_STATUS, ORDER_PENDING_STATUS])),
            completed_orders_count=Count(
                'orders', distinct=True, filter=Q(
                    orders__status__in=[ORDER_DELIVERED_STATUS, ORDER_COMPLETE_STATUS])),
            failed_orders_count=Count(
                'orders', distinct=True, filter=Q(
                    orders__status__in=[ORDER_FAILED_STATUS])
            )
        ).filter(company=company_id)

        #company_projects = Project.objects.filter(company =company_id)
        company_projects = Project.objects.annotate(video_count=Count('videos'), latest_data=Max('videos__updated')).filter(company=company_id).order_by(
            '-latest_data')[:100]

        #The following query is not woroking yet!
        company_assets = Asset.objects.filter(
            Q(company_owner__isnull=True) & Q(client_owner__isnull=True) |   Q(company_owner_id=company_id))
        #Q(company_owner__isnull=True) | 

        context = {
            'company': this_company,
            'company_clients': company_clients,
            'company_assets' : company_assets,
            'company_projects': company_projects
        }

        return render(request, 'Companies/company_detail.html', context)

# subpage for Company Detail
# company orders
class CompanyOrderView(LoginRequiredMixin, TemplateView):
    login_url = '/accounts/login/'

    def get(self, request, **kwargs):
        company_id = kwargs.get('company_id', None)
        try:
            this_company = Company.objects.get(id=company_id)
        except:
            raise Http404('No Company matches the given query.')

        #This is not working yet
        company_client_ids = Client.objects.filter(company_id=company_id).values_list('id', flat=True)

        company_order_list = Order.objects.annotate(
            products_count=Count('order_products', distinct=True),
            total_running_time=Sum('order_products__product__runtime')
        ).filter(client_id__in=company_client_ids).order_by('-created')[:100]

        context = {
            'company': this_company,
            'company_order_list' : company_order_list
        }

        return render(request, 'Companies/company_orders.html', context)

# company assets
class CompanyAssetsView(LoginRequiredMixin, TemplateView):
    login_url = '/accounts/login/'
    def get(self, request, **kwargs):
        company_id = kwargs.get('company_id', None)
        try:
            this_company = Company.objects.get(id=company_id)
        except:
            raise Http404('No Company matches the given query.')

        #company_clients = Client.objects.select_related().filter(company=company_id)
        company_clients = Client.objects.annotate(
            orders_count=Count('orders', distinct=True),
            open_orders_count=Count(
                'orders', distinct=True, filter=Q(
                    orders__status__in=[ORDER_ACTIVE_STATUS, ORDER_PENDING_STATUS])),
            completed_orders_count=Count(
                'orders', distinct=True, filter=Q(
                    orders__status__in=[ORDER_DELIVERED_STATUS, ORDER_COMPLETE_STATUS])),
            failed_orders_count=Count(
                'orders', distinct=True, filter=Q(
                    orders__status__in=[ORDER_FAILED_STATUS])
            )
        ).filter(company=company_id)

        #The following query is not woroking yet!
        #company_assets = Asset.objects.filter(
        #       Q(company_owner_id=company_id) | Q(client_owner__company_id=company_id))

        company_assets = this_company.assets.all()

        global_assets = list(Asset.objects.filter(Q(client_owner__isnull=True) & Q(company_owner__isnull=True)).values('id', 'name', 'value'))
        print(global_assets)
        tmp_gb_assets = global_assets.copy()
        for gb_asset in global_assets:
            for cl_asset in company_assets:
                print(cl_asset.id)
                if gb_asset["id"] == cl_asset.id:
                    tmp_gb_assets.remove(gb_asset)

        print(tmp_gb_assets)
        context = {
            'company': this_company,
            'company_clients': company_clients,
            'company_assets' : company_assets,
            'global_available_assets': tmp_gb_assets
        }

        return render(request, 'Companies/company_assets.html', context)

#ajax calls for add global asset to client ###  Zita added ###
def addAjaxAssetToCompany(request):
    if request.method == 'POST':
        gb_asset_ids = request.POST.getlist("gb_asset_ids[]")
        company_id = request.POST['company_id']
        company_obj = Company.objects.get(id=company_id)
        for asset_id in gb_asset_ids:
            company_obj.assets.add(asset_id)

        return JsonResponse({"statusCode":2}) # Sending an success response
    else:
        return JsonResponse({"statusCode":1})
    # company billing
class CompanyBillingView(LoginRequiredMixin, TemplateView):
    login_url = '/accounts/login/'
    def get(self, request, **kwargs):
        company_id = kwargs.get('company_id', None)
        try:
            this_company = Company.objects.get(id=company_id)
        except:
            raise Http404('No Company matches the given query.')

        #company_clients = Client.objects.select_related().filter(company=company_id)
        company_clients = Client.objects.annotate(
            orders_count=Count('orders', distinct=True),
            open_orders_count=Count(
                'orders', distinct=True, filter=Q(
                    orders__status__in=[ORDER_ACTIVE_STATUS, ORDER_PENDING_STATUS])),
            completed_orders_count=Count(
                'orders', distinct=True, filter=Q(
                    orders__status__in=[ORDER_DELIVERED_STATUS, ORDER_COMPLETE_STATUS])),
            failed_orders_count=Count(
                'orders', distinct=True, filter=Q(
                    orders__status__in=[ORDER_FAILED_STATUS])
            )
        ).filter(company=company_id)

        #The following query is not woroking yet!
        company_assets = Asset.objects.filter(
            Q(company_owner__isnull=True) & Q(client_owner__isnull=True) |   Q(company_owner_id=company_id))
        #Q(company_owner__isnull=True) | 

        context = {
            'company': this_company,
            'company_clients': company_clients,
            'company_assets' : company_assets
        }

        return render(request, 'Companies/company_billing.html', context)

# INDEX VIEW FOR ORDERS
class ProductIndexView(LoginRequiredMixin, TemplateView):
    login_url = '/accounts/login/'

    def get(self, request, *args, **kwargs):
        latest_orders_list = Product.objects.order_by('-created')[:100]
        context = {'latest_products_list': latest_orders_list}
        return render(request, 'Products/product_index.html', context)

#ajax calls for check status of all products ###  Zita added ###
def checkAjaxStatusProduct(request):
    if request.method == 'POST':
        prod_obj = Product.objects.all()
        for obj in prod_obj:
            obj.check_online()
        return JsonResponse({"statusCode":2}) # Sending an success response
    else:
        return JsonResponse({"statusCode":1})


    # DETAIL VIEW FOR PRODUCTS
class ProductPageView(LoginRequiredMixin, TemplateView):
    def get(self, request, **kwargs):
        order_id = kwargs.get('product_id', None)
        product = Product.objects.select_related().annotate(
            orders_count=Count('orderproduct', distinct=True),
            total_running_time=Sum('orderproduct__product__runtime'),
            failed_products_count=Count(
                'orderproduct', distinct=True, filter=Q(orderproduct__status__iexact=ORDER_FAILED_STATUS)
            )
        ).filter(id=order_id).first()
        if not product:
            raise Http404('No product data matches the given query.')

        related_products = Product.objects.select_related().filter(base_id=product.base_id).exclude(id=product.id)
        langs = Language.objects.filter(system_language=True)
        

        #print(product.product_images.all())
        #DEBUG! (goes into the model function)
        vimeo_link = product.get_vimeo_link()
        context = {
            'product': product,
            'vimeo_link' : vimeo_link,
            'related_products': related_products,
            'langs': langs
        }

        return render(request, 'Products/product_detail.html', context)

#ajax calls for check status of all products ###  Zita added ###
def saveAjaxProductTextInfo(request):
    prod_text_id = request.POST['prod_text_id']
    prod_id = request.POST['prod_id']
    title = request.POST['title']
    description_short = request.POST['description_short']
    description_long = request.POST['description_long']
    language = request.POST['language']
    if prod_text_id == "-1":
        obj = ProductText(
            desc_long=description_long,
            desc_short=description_short,
            language_id=language,
            product_id=prod_id,
            title=title
        )
        obj.save()
    else:
        obj = ProductText.objects.get(id=prod_text_id)
        obj.title = title
        obj.desc_short = description_short
        obj.desc_long = description_long
        obj.language_id = language
        obj.save()

    product = Product.objects.get(id=prod_id)
    return render(request, 'Products/product_textinfo_ajax.html', {'product': product})

def ajaxSubProductInfo(request):
    if request.method == "POST":
        order_id = request.POST.get('productid')
        product = Product.objects.select_related().annotate(
            orders_count=Count('orderproduct', distinct=True),
            total_running_time=Sum('orderproduct__product__runtime'),
            failed_products_count=Count(
                'orderproduct', distinct=True, filter=Q(orderproduct__status__iexact=ORDER_FAILED_STATUS)
            )
        ).filter(id=order_id).first()

        langs = Language.objects.all()

        return render(request, 'Products/sub_product_ajax.html', {'product': product, 'langs': langs})

def ajaxSubProductImageTextUpdate(request):
    if request.method == "POST":
        imagetextid = request.POST.get('imagetextid')
        title = request.POST.get('title')
        description = request.POST.get('description')

        productimagetext = ProductImageText.objects.get(id=imagetextid)
        productimagetext.title = title
        productimagetext.desc_short = description
        productimagetext.desc_long = description
        productimagetext.save()

        return JsonResponse({'status': 'success'})

def ajaxSubProductImageTextDelete(request):
    if request.method == "POST":
        imagetextid = request.POST.get('imagetextid')

        productimagetext = ProductImageText.objects.get(id=imagetextid)
        productimagetext.title = ''
        productimagetext.desc_short = ''
        productimagetext.desc_long = ''
        productimagetext.save()
        # productimagetext.delete()

        return JsonResponse({'status': 'success'})


def ajaxSubProductOrder(request):
    if request.method == "POST":
        orderdata = request.POST.getlist('order[]')
        for index, value in enumerate(orderdata):

            ProductImage.objects.filter(id=value).update(display_order=index + 1)
        
        return JsonResponse({'status': 'success'})

def ajaxProductImageDataAdd(request):
    if request.method == "POST":
        imagedata = request.FILES.getlist('image_files')
        product_pk = request.POST.get('productid')
        upload_id = []
        for image_da in imagedata:
            if ProductImage.objects.filter(product_id=product_pk).exists():
                order = ProductImage.objects.filter(product_id=product_pk).order_by("-display_order")
                order_val = order[0].display_order
            else:
                order_val = 0
            productimage = ProductImage.objects.create(
                image=image_da,
                product_id=product_pk,
                display_order=order_val + 1
            )
            upload_id.append(productimage.id)
            
            
        return JsonResponse({'status': 'success', "uploaded": upload_id})

def ajaxProductImageTextAdd(request):
    if request.method == "POST":
        uploaded_ids = request.POST.get('uploaded_ids')
        for index, uploaded_id in enumerate(uploaded_ids.split(',')):
            num_val = index + 1
            
            for lang in Language.objects.filter(system_language=True):
                picture_title =  request.POST.get('upload_picture_title_' + lang.abbreviation + '_' + str(num_val))
                picture_desc = request.POST.get('upload_picture_description_' + lang.abbreviation + '_' + str(num_val))
                ProductImageText.objects.create(
                    language_id=lang.id,
                    product_image_id=uploaded_id,
                    title=picture_title,
                    desc_short=picture_desc,
                    desc_long=picture_desc,
                    default=True
                )

        return JsonResponse({'status': 'success'})

def deleteAjaxProductTextInfo(request):
    prod_text_id = request.POST['prod_text_id']
    prod_id = request.POST['prod_id']

    ProductText.objects.get(id=prod_text_id).delete()

    product = Product.objects.get(id=prod_id)
    return render(request, 'Products/product_textinfo_ajax.html', {'product': product})

def deleteAjaxProductImageInfo(request):
    prod_image_id = request.POST['prod_image_id']
    product_image = ProductImage.objects.get(id=prod_image_id)
    product_image.delete()
    return HttpResponse("ok")


# DETAIL VIEW FOR PRODUCTBASE
class ProductBasePageView(LoginRequiredMixin, TemplateView):
    def get(self, request, **kwargs):
        productbase_id = kwargs.get('productbase_id', None)
        #productbase = ProductBase.objects.get(id=productbase_id)
        productbase = ProductBase.objects.get(id=productbase_id)
        if not productbase:
            raise Http404('No product data matches the given query.')

        #child_products = Product.objects.filter(base=productbase_id)
        child_products = Product.objects.select_related().filter(base=productbase_id)


        #product_assets

        assets= None
        #DEBUG! (goes into the model function)
        #vimeo_link = product.get_vimeo_link()
        context = {
            'productbase': productbase,
            'child_products': child_products,
            'assets':assets,


        }

        return render(request, 'Products/productbase_detail.html', context)

#ajax calls for check status of all products ###  Zita added ###
def changeProductBaseIntake(request):
    product_base_id = request.POST["product_base_id"]
    intake = request.POST["intake"]
    obj = ProductBase.objects.get(id=product_base_id)
    if intake == "1":
        obj.needs_intake = True
    else:
        obj.needs_intake = False
    obj.save()
    return JsonResponse({"statusCode":2})



@require_http_methods(["GET"])
def clipboard_info(request, project_id):
    if request.user.is_staff:

        try:
            project = Project.objects.get(id=project_id)
            client = project.client
            client_firstname = client.firstname
            client_lastname = client.lastname

            video = list(Video.objects.filter(project=project).values())
            data = {
                'project_name': project.name,
                'client_firstname': client_firstname,
                'client_lastname': client_lastname,

                'video': video
            }
            return render(request, 'clipboard_info.html', data)
        except:
            return []
    return redirect('/')


@require_http_methods(["GET"])
def lastnvideos(request):
    if request.user.is_staff:
        data = list(Video.objects.order_by('-updated')[:5].values());
        return render(request, 'last_n_videos.html', {'data': data})
    return redirect('/')


#CSV IMPORT
#only working with UTF8 files, no error catching no evaluation
#https://medium.com/@simathapa111/how-to-upload-a-csv-file-in-django-3a0d6295f624
# one parameter named request
def company_csv_import(request):    # declaring template
    template = "company_csv_import.html"
    data = Company.objects.all()# prompt is a context variable that can have different values      depending on their context
    prompt = {
        'order': 'Order of the CSV should be: id;name;street;zip_code;place;country;language;website;phone_number;description;',
        'companies': data
    }
    # GET request returns the value of the data with the specified key.
    if request.method == "GET":
        return render(request, template, prompt)

    if 'file' in request.FILES:
        csv_file = request.FILES['file']
    else:
        messages.error(request, 'No valid file given!')

    # let's check if it is a csv file
    if not csv_file.name.endswith('.csv'):
        messages.error(request, 'THIS IS NOT A CSV FILE')

    data_set = csv_file.read().decode('UTF-8')

    # setup a stream which is when we loop through each line we are able to handle a data in a stream
    io_string = io.StringIO(data_set)
    next(io_string)
    #print("file:" % csv_file)
    for column in csv.reader(io_string, delimiter=';', quotechar="|"):
        #perform field checks here:
        try:
            lang = Language.objects.get(name__icontains=column[6]) #language
        except:
            lang = Language.objects.get(name__icontains='DE')

        _, created = Company.objects.update_or_create(
            name=column[1],
            street=column[2],
            zip_code=column[3],
            place=column[4],
            country=column[5],
            language=lang,
            website=column[7],
            phone_number=column[8],
            description=column[9]
        )

    context = {}
    return render(request, template, context)

# this function imports a csv table with product information 

def product_csv_import(request):   # declaring template
    template = "product_csv_import.html"
    data = Product.objects.all()
    # prompt is a context variable that can have different values      depending on their context

    #compile format for the import settings, as defined in the global array in formikaro.utils:
    column_order = '<table class="table table-sm table-dark" width="100%" cellspacing="0">'
    column_header = ''
    column_fields = ''
    count = 0

    for col in col_names_fo:
        column_header += '<td class="border-right">' + str(count) + '</td>\n'
        column_fields += '<td class="border-right">' + col + '</td>\n'
        count = count + 1

    column_order += '<thead><tr>' + column_header + '</tr></thead>'
    column_order += '<tbody><tr>' + column_fields + '</tr></tbody>'
    column_order += '</table>'

    prompt = {
        'csv_column_info': format_html(column_order),
        'products': data
    }
    # GET request returns the value of the data with the specified key.
    if request.method == "GET":
        return render(request, template, prompt)

    #checkbox if we want to update existing products
    product_update = request.POST.get('product_update', '') == 'on'

    if 'file' in request.FILES:
        csv_file = request.FILES['file']
    else:
        messages.error(request, 'No valid file given!')

    # let's check if it is a csv file
    if not csv_file.name.endswith('.csv'):
        messages.error(request, 'THIS IS NOT A CSV FILE')

    data_set = csv_file.read().decode('UTF-8')

    #this are the messages/stats we give to the user at the end of the operation
    messages = []
    created_products = 0
    updated_products = 0
    product_count = 0

    # setup a stream which is when we loop through each line we are able to handle a data in a stream
    io_string = io.StringIO(data_set)
    next(io_string)
    for column in csv.reader(io_string, delimiter=';', quotechar="|"):
        product_count = product_count + 1
        try:
            product_fsin_base = str(column[1].strip('\"'))

            product_base = ProductBase.objects.get(fsin_base=product_fsin_base) #get product base

            #messages.append('ProductBase [%s] not found, aborting import!' % product_fsin_base)

            #perform field checks here:
            try:
                lang = Language.objects.get(name__icontains=column[5]) #language
            except:
                lang = Language.objects.get(name__icontains='DE')

                #check if fsin already exists
            try:
                this_product = Product.objects.get(fsin=column[2])
                product_new = False
            except:
                product_new = True


            #if this products already exists and we don't want to perform
            #an update let's skip this one and move on to the next
            if not product_new and not product_update:
                continue

                #is active?
            is_true = column[11].strip('\"')
            if is_true.upper() == 'TRUE':
                active_flag = True
            else:
                active_flag = False

            # remove the " before converting 
            product_price = int(float(column[7].strip('\"')))

            product_variety = column[3].strip('\"')

            #resolution
            try:
                product_resolution = Resolution.objects.get(name__icontains=column[8].strip('\"')) #Resolution
            except:
                product_resolution = False

            product_fsin = column[2].strip('\"')

            temp = column[6].strip('\"')
            product_runtime = int(float(temp))

            temp = column[4].strip('\"')
            product_version = int(float(temp))

            if column[12]:
                product_vimeo_id = column[12].strip('\"')
            else:
                product_vimeo_id = ''

            product_comment = column[13].strip('\"')
            product_change_log = column[14].strip('\"')

            if product_new:
                this_product = Product(
                    base=product_base,
                    fsin=product_fsin,
                    variety=product_variety,
                    version=product_version,
                    language=lang,
                    runtime=product_runtime,
                    price=product_price,
                    resolution=product_resolution,
                    is_active=active_flag,
                    vimeo_id=product_vimeo_id,
                    comment=product_comment,
                    change_log=product_change_log,
                )
                this_product.save()
                messages.append('Created product: [%s]\n' % str(this_product.id))

                created_products = created_products + 1
            else:

                #now that we have prepared everything UPDATE Product
                this_product, created = Product.objects.update_or_create(
                    base=product_base,
                    fsin=product_fsin,
                    variety=product_variety,
                    version=product_version,
                    language=lang,
                    runtime=product_runtime,
                    price=product_price,
                    resolution=product_resolution,
                    is_active=active_flag,
                    vimeo_id=product_vimeo_id,
                    comment=product_comment,
                    change_log=product_change_log,
                )

                updated_products = updated_products + 1

                messages.append('Updated product: [%s]\n' % str(this_product.id))

            #create all texts for this products
            product_title_de = column[15]
            product_text_short_de = column[16]
            product_text_long_de = column[17]
            product_title_en = column[18]
            product_text_short_en = column[19]
            product_text_long_en = column[20]

            lang_de = Language.objects.get(abbreviation__iexact='DE')
            lang_en = Language.objects.get(abbreviation__iexact='EN')

            if product_title_de or product_text_short_de or product_text_long_de:
                product_text_de = ProductText(title=product_title_de,
                                              desc_short=product_text_short_de,
                                              desc_long=product_text_long_de,
                                              language=lang_de,
                                              product=this_product)
                product_text_de.save()

            if product_title_en or product_text_short_en or product_text_long_en:
                product_text_en = ProductText(title=product_title_en,
                                              desc_short=product_text_short_en,
                                              desc_long=product_text_long_en,
                                              language=lang_en,
                                              product=this_product)
                product_text_en.save()

            #info_text = 'ID: ' +str(importedProduct.id) + '] FSIN: '+ str(column[2]) + ' update: ' + str(product_update)
            #messages.append('added product [%s] ' % info_text)


            #and create the TEXTS...
            # MISSING!

            #handling if no base exists 

        except Exception as e:
            messages.append('General - yet uncaught - error not found [%s][%s]' % (e, type(e)))

    messages.append('Processed %s products. Created %s and updated %s' % (product_count, created_products, updated_products))

    data = Product.objects.all()
    # prompt is a context variable that can have different values     
    context = {
        'products' : data,
        'messages' : messages
    }

    return render(request, template, context)

# this function gets all possible videos that can be assigned to a project video
def getAjaxSelectProjectVideo(request):
    try:
        project_id = request.POST['project_id']

        #videos = Video.objects.filter(Q(project_id=project_id) & ~Exists(ProjectVideo.objects.all))
        existing_videos = ProjectVideo.objects.all()
        print("EXISITNG videos %s " % existing_videos)
        videos = Video.objects.filter(project_id=project_id).exclude(existing_videos)

        video_data =[]
        for video in videos:
            data = {}
            data["id"] = video.id
            data["unique_fn"] = video.unique_fn

            video_data.append(data)
        return JsonResponse(
            {'status' : True, "video_data": video_data})  # Sending an success response

    except Exception as e:
        return JsonResponse({'status': False, 'message': str(e)})

def getAjaxSelectVideo(request):


    try:
        project_id = request.POST['project_id']
        existing_videos = ProjectVideo.objects.filter(Q(project_id=project_id) & Q(videos__isnull=False)).values_list(
            'videos', flat=True)
        videos = Video.objects.filter(Q(project_id=project_id) & ~Q(pk__in=existing_videos))

        video_data =[]
        for video in videos:
            data = {}
            data["id"] = video.id
            data["unique_fn"] = video.unique_fn
            print('%s %s ' % (data["id"], data["unique_fn"]))
            video_data.append(data)
        return JsonResponse(
            {"statusCode": 2, "video_data": video_data})  # Sending an success response

    except Exception as e:
        return JsonResponse({'status': False, 'message': str(e)})

# this functions attatches a single video to a given project video
# attention: no validation is performed!
def saveAjaxSelectProjectVideo(request):
    try:
        message = 'not implemented'
        return JsonResponse(
            {"status": True, "message": message})  # Sending an success response
    except Exception as e:
        return JsonResponse({'status': False, 'message': str(e)})

# create new project page
class ProjectCreateView(LoginRequiredMixin, TemplateView):
    def get(self, request, *args, **kwargs):
        #list all companies (the clients will be loaded via AJAX)
        companies = Company.objects.all()
        all_project_manager_users = ProjectManager.objects.all()
        resolutions = Resolution.objects.all()
        context = {
            'companies': companies,
            'project_managers': all_project_manager_users,
            'resolutions': resolutions
        }
        return render(request, 'projects/project_add.html', context)

def getAjaxEditProjectVideo(request):
    video_id = request.POST['video_id']
    is_editable = request.POST['is_editable']
    is_inline = request.POST['is_inline']
    if video_id != '-1':
        video = ProjectVideo.objects.get(id=video_id)
    else:
        video = None
    if is_editable == "0":
        is_editable = False
    else:
        is_editable = True

    if is_inline == "0":
        is_inline = False
    else:
        is_inline = True
    resolutions = Resolution.objects.all()
    languages = Language.objects.all()
    context = {
        'order_number': video_id,
        'project_id': -1, #debug
        'video_id': video_id,
        'resolutions': resolutions,
        'languages' : languages,
        'video': video,
        'is_editable': is_editable,
        'is_inline' : is_inline,
        'edit_mode' : True,
    }
    return render(request, 'projects/project_add_video_template.html', context)


def getAddVideoTemplate(request):
    order_number = request.POST['order_number']
    project_id = request.POST['project_id']
    video_id = request.POST['video_id']
    is_editable = request.POST['is_editable']
    is_inline = request.POST['is_inline']
    try:
        getFilenameToken = request.POST['filename_token']
    except:
        getFilenameToken = 'FILENAME'

    if video_id != '-1':
        video = ProjectVideo.objects.get(id=video_id)
    else:
        video = None
    if is_editable == "0":
        is_editable = False
    else:
        is_editable = True
    if is_inline == "0":
        is_inline = False
    else:
        is_inline = True
    resolutions = Resolution.objects.all()
    languages = Language.objects.all()

    tempProjectVideo = ProjectVideo(
        project_id=project_id,
    )

    projectvideo_filename = tempProjectVideo.getCorrectFilename(getFilenameToken)
    context = {
        'order_number': order_number,
        'project_id': project_id,
        'video_id': video_id,
        'resolutions': resolutions,
        'languages' : languages,
        'video': video,
        'is_editable': is_editable,
        'is_inline' : is_inline,
        'projectvideo_filename' : projectvideo_filename
    }
    return render(request, 'projects/project_add_video_template.html', context)

def saveAjaxProject(request):
    project_id = request.POST['project_id']
    budget = request.POST['budget']
    paid = request.POST['paid']
    name = request.POST['name']
    abbreviation = request.POST['abbreviation']
    description = request.POST['description']
    deadline = request.POST['deadline']
    shootingdays = request.POST['shootingdays']
    client = request.POST['client']
    company = request.POST['company']
    projectmanager = request.POST['projectmanager']

    try:
        if project_id == "-1":
            obj = Project(
                budget= float(budget),
                paid= float(paid),
                name=name,
                abbreviation=abbreviation,
                change_log=description,
                deadline=datetime.datetime.strptime(deadline, "%d.%m.%Y %H:%M"),
                shootingdays=shootingdays,
                client_id=client,
                company_id=company,
            )
            obj.save()
            obj.projectmanager.add(projectmanager)
        else:
            obj = Project.objects.get(id=project_id)
            obj.budget = float(budget)
            obj.paid = float(paid)
            obj.name = name
            obj.abbreviation = abbreviation
            obj.change_log = description
            obj.deadline = datetime.datetime.strptime(deadline, "%d.%m.%Y %H:%M")
            obj.shootingdays = shootingdays
            obj.client_id = client
            obj.company_id = company
            obj.save()
            obj.projectmanager.clear()
            obj.projectmanager.add(projectmanager)

            messages.success(request, 'Successfully saved projects')
        return JsonResponse({'status': True, "project_id": obj.id })
    except Exception as e:
        #messages.error(request, 'test') #error message is handled on the frontend by alert box
        return JsonResponse({'status': False, 'message': str(e)})



    try:
        project_id = request.POST['project_id']
        videos = Video.objects.filter(project_id=project_id)
        video_data =[]
        for video in videos:
            data = {}
            data["id"] = video.id
            data["unique_fn"] = video.unique_fn

            video_data.append(data)
        return JsonResponse(
            {"statusCode": 2, "video_data": video_data})  # Sending an success response

    except Exception as e:
        return JsonResponse({'status': False, 'message': str(e)})


def loadAjaxProjectVideos(request):
    try:
        project_id = request.POST['project_id']
        try:
            is_editable = request.POST['is_editable']
            if is_editable == "0":
                is_editable = False
            else:
                is_editable = True
        except:
            is_editable = False

        project = Project.objects.get(id=project_id)

        context = {
            'videos' : project.project_videos.all,
            'projectvideo' : True,
            'is_inline' : True,
            'is_editable' : is_editable
        }
        return render(request, 'Videos/video_project_template.html', context)


    except Exception as e:
        return JsonResponse({'status': False, 'message': str(e)})

# this functions attatches a single video to a given project video
# attention: no validation is performed!
def saveAjaxSelectProjectVideo(request):
    try:
        project_video_id = request.POST['project_video_id']
        video_id = request.POST['video_id']

        project_video = ProjectVideo.objects.get(id=project_video_id)
        #missing: check if video is already assigned to other projectvideo!
        video = Video.objects.get(id=video_id)
        video_unique_fn = video.unique_fn
        project_video.videos.add(video)
        project_video.save()
        message = 'Video %s assigned' % video_unique_fn

        return JsonResponse(
            {"status": True, "message": message, "project_video_id": project_video_id, "video_id" : video_id, "video_unique_fn": video_unique_fn})  # Sending an success response
    except Exception as e:
        return JsonResponse({'status': False, 'message': str(e)})



# this function is used to save a newly created project video object via ajax

def saveAjaxProjectVideo(request):
    project_id = request.POST['project_id']
    video_id = request.POST['video_id']
    title = request.POST['title']
    duration = request.POST['duration']
    resolution = request.POST['resolution']
    description = request.POST['description']
    feedbackloops = request.POST['feedbackloops']
    try:
        create_episodes = request.POST['create_episodes']

        if create_episodes == "true":
            create_episodes = True
        else:
            create_episodes = False
    except:
        create_episodes = False

    try:
        episodes = request.POST['episodes']
        episodes_list = json.loads(episodes)
        episode_number = None
        if not '0' in episodes_list or len(episodes_list['0']) == 0:
             episodes_list = False
        elif len(episodes_list) < 2:
            episode_number = episodes_list['0']['number']

    except:
        episodes_list = False
        episode_number = None

    try:
        # serializing in format: index:language_id
        subtitles = request.POST['subtitles']
        subtitle_languages = json.loads(subtitles)
        if len(subtitle_languages) == 0:
            subtitle_languages = False

    except:
        subtitle_languages = False

    #print("DEBUG\tcreate ep\t%s" % create_episodes)
    #print("DEBUG\tep list\t%s\t#: %s" % (episodes_list, episode_number))
    #print("DEBUG\tsubtitles\t%s" % subtitle_languages)

    try:
        is_inline = request.POST['is_inline']
        if is_inline == "0":
            is_inline = False
        else:
            is_inline = True
    except:
        is_inline = False

    try:
        if video_id == "-1":
        #create new videos. in case we have an episode count and the create_episode flag is set we will create
        #all episodes of this series
            if create_episodes:

                episode_number = 1
                for episode_key in episodes_list:
                    print("key %s %s" % (episode_key, episodes_list[episode_key]))

                    if subtitle_languages:

                        for key in subtitle_languages:
                            sub_language = Language.objects.get(id=subtitle_languages[key])
                            obj = ProjectVideo(
                                name=episodes_list[episode_key]['title'],
                                duration=duration,
                                episode=episodes_list[episode_key]['number'],
                                change_log=description,
                                feedbackloops=feedbackloops,
                                project_id=project_id,
                                sub_language=sub_language,
                                resolution_id=resolution,
                            )
                            obj.save()
                    else:
                        obj = ProjectVideo(
                            name=episodes_list[episode_key]['title'],
                            duration=duration,
                            episode=episodes_list[episode_key]['number'],
                            change_log=description,
                            feedbackloops=feedbackloops,
                            project_id=project_id,
                            resolution_id=resolution,
                        )
                        obj.save()
                    episode_number = episode_number + 1
            else:
                #so we don't create a series but maybe more subtitle versions?
                if subtitle_languages:
                    for key in subtitle_languages:
                        sub_language = Language.objects.get(id=subtitle_languages[key])
                        obj = ProjectVideo(
                            name=title,
                            duration=duration,
                            episode=episode_number,
                            change_log=description,
                            feedbackloops=feedbackloops,
                            project_id=project_id,
                            sub_language=sub_language,
                            resolution_id=resolution,
                        )
                        obj.save()
                else:
                    #ok no subs then just this one

                    obj = ProjectVideo(
                        name=title,
                        duration=duration,
                        episode=episode_number,
                        change_log=description,
                        feedbackloops=feedbackloops,
                        project_id=project_id,
                        resolution_id=resolution,
                    )
                    obj.save()
        else:
        #editmode

            obj = ProjectVideo.objects.get(id=video_id)
            obj.name = title
            obj.duration = duration
            obj.change_log = description
            obj.feedbackloops = feedbackloops
            obj.resolution_id = resolution
            if episode_number:
                obj.episode = episode_number
            else:
                obj.episode = None
            if subtitle_languages:
                sub_language = Language.objects.get(id=subtitle_languages['0'])
                obj.sub_language = sub_language
            obj.save()
        return JsonResponse({'status': True, "video_id": obj.id, 'is_inline': is_inline })
    except Exception as e:
        return JsonResponse({'status': False, 'message': str(e), 'is_inline': is_inline})

def deleteAjaxProjectVideo(request):
    video_id = request.POST['video_id']
    try:
        project_video = ProjectVideo.objects.get(id=video_id)
        project_video_name = project_video.name
        project_video.delete()
        message = 'Successfully deleted project video %s (%s)' % (project_video_name, video_id)
        return JsonResponse({'status': True, 'message': message, 'video_id': video_id})
    except Exception as e:
        return JsonResponse({'status': False, 'message': str(e)})

def deleteAjaxVideo(request):
    video_id = request.POST['video_id']
    try:
        video = Video.objects.get(id=video_id)
        video_name = video.unique_fn
        video.delete()
        message = 'Successfully deleted video %s (%s)' % (video_name, video_id)
        return JsonResponse({'status': True, 'message': message, 'video_id': video_id})
    except Exception as e:
        return JsonResponse({'status': False, 'message': str(e)})

# INDEX VIEW FOR POROJECTS
class ProjectvideoPageView(LoginRequiredMixin, TemplateView):
    login_url = '/accounts/login/'

    def get(self, request, *args, **kwargs):
        projectvideo_id = kwargs.get('projectvideo_id', None)
        projectvideo = ProjectVideo.objects.get(id=projectvideo_id)
        #companies = Company.objects.all()
        #all_project_manager_users = ProjectManager.objects.all()
        #resolutions = Resolution.objects.all()
        project = None # not yet

        if not projectvideo:
            raise Http404('No project video id matches the given query.')

        context = {
            'project': project,
            'projectvideo': projectvideo,

        }

        return render(request, 'Projects/projectvideo.html', context)

class ProjectIndexView(LoginRequiredMixin, TemplateView):
    login_url = '/accounts/login/'

    def get(self, request, *args, **kwargs):
        latest_projects_list = Project.objects.annotate(video_count=Count('videos'),latest_data=Max('videos__updated')).order_by('-latest_data')[:100]
        context = {'latest_projects_list': latest_projects_list}
        return render(request, 'Projects/project_index.html', context)

class ProjectShootsView(LoginRequiredMixin, TemplateView):
    login_url = '/accounts/login/'

    def get(self, request, **kwargs):
        project_id = kwargs.get('project_id', None)
        project = Project.objects.get(id=project_id)

        if not project:
            raise Http404('No project id matches the given query.')
        project_manager = project.projectmanager.all()[0]
        if project_manager == ProjectManager.objects.get(user = request.user) and project_manager.is_manager:
            is_editable = True
        else:
            is_editable = False
        context = {
            'project': project,
            'is_editable': is_editable
        }

        return render(request, 'Projects/project_shoots.html', context)


def saveAjaxProjectShoot(request):
    project_id = request.POST['project_id']
    shootvideos = request.POST['shootvideos'].split(',')
    shoot_id = request.POST['shoot_id']
    location = request.POST['shootinglocation']
    startime = request.POST['startime']
    endtime = request.POST['endtime']
    damages = request.POST['damages']
    remark = request.POST['remarks']

    try:
        if shoot_id == "-1":
            obj = Shoot(
                location = location,
                starttime = datetime.datetime.strptime(startime, "%d.%m.%Y %H:%M"),
                endtime = datetime.datetime.strptime(endtime, "%d.%m.%Y %H:%M"),
                damages = damages,
                remark = remark,
                project_id = project_id,
                creator = ProjectManager.objects.get(user = request.user),
            )
            obj.save()
            for video in shootvideos:
                obj.videos.add(video)
        else:
            obj = Shoot.objects.get(id=shoot_id)
            obj.location = location
            obj.starttime = datetime.datetime.strptime(startime, "%d.%m.%Y %H:%M")
            obj.endtime = datetime.datetime.strptime(endtime, "%d.%m.%Y %H:%M")
            obj.damages = damages
            obj.remark = remark
            obj.save()
            for video in shootvideos:
                obj.videos.add(video)
        return JsonResponse({'status': True, "shoot_id": obj.id })
    except Exception as e:
        return JsonResponse({'status': False, 'message': str(e)})

def deleteAjaxProjectShoot(request):
    shoot_id = request.POST['shoot_id']
    shoot = Shoot.objects.get(id=shoot_id)
    for item in shoot.crew.all():
        item.delete()
    for item in shoot.settings.all():
        item.delete()
    shoot.delete()
    return JsonResponse({'status': True})


def getAddCrewTemplate(request):
    order_number = request.POST['order_number']
    crew_id = request.POST['crew_id']
    shoot_id = request.POST['shoot_id']
    is_editable = request.POST['is_editable']

    if is_editable == "0":
        is_editable = False
    else:
        is_editable = True
    if crew_id != "-1":
        crew = Crew.objects.get(id=crew_id)
    else:
        crew = None
    userroles = UserRole.objects.all()
    persons = ProjectManager.objects.all()
    shoot = Shoot.objects.get(id=shoot_id)

    context = {
        'order_number': order_number,
        'crew_id': crew_id,
        'shoot_id': shoot_id,
        'persons': persons,
        'userroles': userroles,
        'crew': crew,
        'setting_ids': shoot.get_settings_ids_str,
        'is_editable': is_editable
    }
    return render(request, 'projects/project_add_crew_template.html', context)

def saveAjaxShootCrew(request):
    shoot_id = request.POST['shoot_id']
    crew_id = request.POST['crew_id']
    person_id = request.POST['person_id']
    role_id = request.POST['role_id']
    remark = request.POST['remark']

    try:
        if crew_id == "-1":
            obj = Crew(
                person_id = person_id,
                role_id = role_id,
                remark = remark,
            )
            obj.save()
            shoot = Shoot.objects.get(id=shoot_id)
            shoot.crew.add(obj)
        else:
            obj = Crew.objects.get(id=crew_id)
            obj.person_id = person_id
            obj.role_id = role_id
            obj.remark = remark
            obj.save()
        return JsonResponse({'status': True, "crew_id": obj.id })
    except Exception as e:
        return JsonResponse({'status': False, 'message': str(e)})

def deleteAjaxShootCrew(request):
    crew_id = request.POST['crew_id']
    shoot_id = request.POST['shoot_id']
    crew = Crew.objects.get(id=crew_id)
    shoot = Shoot.objects.get(id=shoot_id)
    shoot.crew.remove(crew)
    crew.delete()
    return JsonResponse({'status': True})



def getAddCameraTemplate(request):
    order_number = request.POST['order_number']
    camera_id = request.POST['camera_id']
    shoot_id = request.POST['shoot_id']
    is_editable = request.POST['is_editable']

    if is_editable == "0":
        is_editable = False
    else:
        is_editable = True

    videoformats = VideoFormat.objects.all()
    shoot = Shoot.objects.get(id=shoot_id)
    crews = shoot.crew.all()
    # crews = Crew.objects.all()
    if camera_id != "-1":
        setting = CameraSetting.objects.get(id=camera_id)
    else:
        setting = None
    context = {
        'order_number': order_number,
        'camera_id': camera_id,
        'shoot_id': shoot_id,
        'videoformats': videoformats,
        'crews': crews,
        'setting': setting,
        'is_editable': is_editable
    }
    return render(request, 'projects/project_add_camera_template.html', context)

def saveAjaxShootCamera(request):
    shoot_id = request.POST['shoot_id']
    camera_id = request.POST['camera_id']
    setting_name = request.POST['setting_name']
    camera_name = request.POST['camera_name']
    operator = request.POST['operator']
    videoformat = request.POST['videoformat']
    whitebalance = request.POST['whitebalance']
    framerate = request.POST['framerate']
    colorprofle = request.POST['colorprofle']
    remark = request.POST['remark']

    try:
        if camera_id == "-1":
            obj = CameraSetting(
                name = setting_name,
                operator_id = operator,
                camera = camera_name,
                framerate = framerate,
                videoformat_id = videoformat,
                whitebalance = whitebalance,
                colorprofile = colorprofle,
                remark = remark,
            )
            obj.save()
            shoot = Shoot.objects.get(id=shoot_id)
            shoot.settings.add(obj)
        else:
            obj = CameraSetting.objects.get(id=camera_id)
            obj.name = setting_name
            obj.operator_id = operator
            obj.camera = camera_name
            obj.framerate = framerate
            obj.videoformat_id = videoformat
            obj.whitebalance = whitebalance
            obj.colorprofile = colorprofle
            obj.remark = remark
            obj.save()
        return JsonResponse({'status': True, "camera_id": obj.id })
    except Exception as e:
        return JsonResponse({'status': False, 'message': str(e)})

def deleteAjaxShootCamera(request):
    camera_id = request.POST['camera_id']
    shoot_id = request.POST['shoot_id']
    camera = CameraSetting.objects.get(id=camera_id)
    shoot = Shoot.objects.get(id=shoot_id)
    shoot.settings.remove(camera)
    camera.delete()
    return JsonResponse({'status': True})


class ProjectIntakesView(LoginRequiredMixin, TemplateView):
    login_url = '/accounts/login/'

    def get(self, request, **kwargs):
        project_id = kwargs.get('project_id', None)
        project = Project.objects.get(id=project_id)
        #intakes = Intake.objects.filter(project=project_id)
        intakes = Intake.objects.annotate(
            files_count=Count('files', distinct=True),
            total_size=Sum('files__size')
        ).filter(project=project_id)

        if not project:
            raise Http404('No project id matches the given query.')

        project_manager = project.projectmanager.all()[0]
        if project_manager == ProjectManager.objects.get(user = request.user) and project_manager.is_manager:
            is_editable = True
        else:
            is_editable = False

        context = {
            'project': project,
            'project_intake_list': intakes,
            'is_editable': is_editable
        }

        return render(request, 'Projects/project_intakes.html', context)

class ProjectVideosView(LoginRequiredMixin, TemplateView):
    login_url = '/accounts/login/'

    def get(self, request, **kwargs):
        project_id = kwargs.get('project_id', None)
        project = Project.objects.get(id=project_id)
        videos = Video.objects.filter(project=project_id)

        if not project:
            raise Http404('No project id matches the given query.')
        project_manager = project.projectmanager.all()[0]
        if project_manager == ProjectManager.objects.get(user = request.user) and project_manager.is_manager:
            is_editable = True
        else:
            is_editable = False

        context = {
            'project': project,
            'project_video_list': videos,
            'is_editable': is_editable
        }

        return render(request, 'Projects/project_videos.html', context)

# just a filler, billing not yet implemented
class ProjectBillingView(LoginRequiredMixin, TemplateView):
    login_url = '/accounts/login/'

    def get(self, request, **kwargs):
        project_id = kwargs.get('project_id', None)
        project = Project.objects.get(id=project_id)

        if not project:
            raise Http404('No project id matches the given query.')

        project_manager = project.projectmanager.all()[0]
        if project_manager == ProjectManager.objects.get(user = request.user) and project_manager.is_manager:
            is_editable = True
        else:
            is_editable = False

        total_cost = 0
        total_price = 0
        for item in project.lineitems.all():
            total_cost = total_cost + item.cost * item.quantity
            total_price = total_price + item.price * item.quantity
        diff = total_price - total_cost
        if diff < 0:
            diff_class = 'text-danger'
        else:
            diff_class = 'text-success'

        context = {
            'project': project,
            'total_cost': total_cost,
            'total_price': total_price,
            'total_diff': diff,
            'diff_class': diff_class,
            'is_editable': is_editable
        }
        return render(request, 'Projects/project_billing.html', context)

def saveAjaxProjectLineItem(request):
    project_id = request.POST['project_id']
    video_id = request.POST['video_id']
    line_id = request.POST['line_id']
    name = request.POST['name']
    price = request.POST['price']
    cost = request.POST['cost']
    quantity = request.POST['quantity']
    status = request.POST['status']
    description = request.POST['description']
    paiddate = request.POST['paiddate']
    if paiddate != '':
        paid = datetime.datetime.strptime(paiddate, "%d.%m.%Y %H:%M")
    else:
        paid = None
    try:
        if line_id == "-1":
            obj = LineItem(
                creator = ProjectManager.objects.get(user = request.user),
                name = name,
                quantity = quantity,
                price = price,
                cost = cost,
                project_id = project_id,
                video_id = video_id,
                description = description,
                status = status,
                paid = paid
            )
            obj.save()
        else:
            obj = LineItem.objects.get(id=line_id)
            obj.name = name
            obj.quantity = quantity
            obj.price = price
            obj.cost = cost
            obj.project_id = project_id
            obj.video_id = video_id
            obj.description = description
            obj.status = status
            obj.paid = paid
            obj.save()
        return JsonResponse({'status': True, "line_id": obj.id })
    except Exception as e:
        return JsonResponse({'status': False, 'message': str(e)})

def deleteAjaxProjectLineItem(request):
    line_id = request.POST['line_id']
    LineItem.objects.filter(id=line_id).delete()
    return JsonResponse({'status': True})

# NOT IN USE ANYMORE
# now located in FormikoBot/Views: function ProjectTaskStatusView
# if called without status it displays all tasks of a project
#class ProjectTasksView(LoginRequiredMixin, TemplateView):
#login_url = '/accounts/login/'
#
#    def get(self, request, **kwargs):
#        project_id = kwargs.get('project_id', None)
#        try:
#            project = Project.objects.get(id=project_id)
#        except:
#            raise Http404('No project id matches the given query.')
#
#        project.is_owned = False
#        for item in project.projectmanager.all():
#            if item.user ==  request.user:
#                project.is_owned = True
#        project_list = Project.objects.filter(projectmanager__user=request.user)
#        preset_tasks = TaskPreset.objects.all()
#        task_types = TaskType.objects.all()
#        projectmanager_user = ProjectManager.objects.get(user=request.user)
#        all_project_manager_users = ProjectManager.objects.all()
#        context = {
#            'project': project,
#            'project_list': project_list,
#            'preset_tasks': preset_tasks,
#            'all_users': all_project_manager_users, #still debug
#            'projectmanager': projectmanager_user, # still debug
#            'task_types' : task_types,
#        }
#        return render(request, 'Projects/project_tasks.html', context)


class ProjectDashboardView(LoginRequiredMixin, TemplateView):
    def get(self, request, **kwargs):
        project_id = kwargs.get('project_id', None)
        project = Project.objects.get(id=project_id)
        if not project:
            raise Http404('No project id matches the given query.')
        project_manager = project.projectmanager.all()[0]
        if project_manager == ProjectManager.objects.get(user = request.user) and project_manager.is_manager:
            is_editable = True
        else:
            is_editable = False

        task_list = project.tasks.filter(~Q(status=TASK_STATUS_COMPLETE)).order_by('-updated')[:20]

        context = {
            'project': project,
            'task_list': task_list,
            'is_editable': is_editable
        }

        #messages.success(request, "Message 234sent.")

        return render(request, 'Projects/project_dashboard.html', context)


# DETAIL VIEW FOR PRODUCTS
class ProjectPageView(LoginRequiredMixin, TemplateView):
    def get(self, request, **kwargs):
        project_id = kwargs.get('project_id', None)
        project = Project.objects.get(id=project_id)
        companies = Company.objects.all()
        all_project_manager_users = ProjectManager.objects.all()
        resolutions = Resolution.objects.all()

        if not project:
            raise Http404('No project id matches the given query.')

        project_manager = project.projectmanager.all()[0]
        if project_manager == ProjectManager.objects.get(user = request.user) and project_manager.is_manager:
            is_editable = True
        else:
            is_editable = False
        context = {
            'project': project,
            'companies': companies,
            'project_managers': all_project_manager_users,
            'resolutions': resolutions,
            'is_editable': is_editable
        }

        return render(request, 'Projects/project_detail.html', context)

def deleteProjectVideo(request):

    project_id = request.POST['project_id']
    video_id = request.POST['video_id']
    Video.objects.filter(id=video_id).delete()
    project = Project.objects.get(id=project_id)
    return render(request, 'Projects/project_detail_video_ajax.html', {'project': project})

def getUserNotifications(request):
    notifications = ''
    return render(request, 'Formikaro/user-notifications.html', {'notifications': notifications})

def markUserNotificationsRead(request):
    if request.method == 'POST':
        user_id = request.POST['user_id']
        print("USER: %s" %user_id)
        user = User.objects.get(pk=user_id)
        user.notifications.mark_all_as_read()

        return JsonResponse({"statusCode": 2})
    else:
        return JsonResponse({"statusCode": 1})