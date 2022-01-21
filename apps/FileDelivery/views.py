from django.shortcuts import render

# Create your views here.

from django.conf import settings
from django.db.models import Q
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import TemplateView
from django.utils.html import format_html
from django.utils.safestring import mark_safe
from django.http import Http404

from apps.FileCollector.models import Video, Order, ORDER_COMPLETE_STATUS, ORDER_FAILED_STATUS, ORDER_READY_STATUS, \
    ORDER_PENDING_STATUS, ORDER_ACTIVE_STATUS, ORDER_DELIVERED_STATUS, VIDEO_UPLOADING_COMPLETE


# this is a dummy function to link to for all furture pages
class DeliveryOverview(LoginRequiredMixin, TemplateView):
    login_url = '/accounts/login/'

    def get(self, request, *args, **kwargs):
        # get all videos where the order status is set to delivered
        video_list = Video.objects.filter(
            status=VIDEO_UPLOADING_COMPLETE, order_product__order__status=ORDER_DELIVERED_STATUS
        ).select_related().order_by('-created')[:5]
        context = {'video_list': video_list, }

        return render(request, 'Delivery/delivery_overview.html', context)