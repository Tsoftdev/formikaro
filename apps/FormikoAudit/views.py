from django.http import Http404
from django.shortcuts import render
from django.contrib.auth.mixins import LoginRequiredMixin
from .models import Shoot
from datetime import datetime
from django.utils import formats
from formikaro.utils import  urlify
# from wkhtmltopdf.views import PDFTemplateView, PDFTemplateResponse


class PDFTemplateView:
    pass


class ProjectShootPDF(LoginRequiredMixin, PDFTemplateView):

    login_url = '/accounts/login/'
    template = 'Reports/shoot_report.html'
    cmd_options = {
        'margin-top': 1, 'enable-local-file-access': True, 'quiet': False,
    }


    def get(self, request, **kwargs):
        shoot_id = kwargs.get('shoot_id', None)
        shoot = Shoot.objects.get(id=shoot_id)
        #shoot_date = datetime.fromtimestamp(shoot.starttime)
        shoot_date = format(shoot.starttime, '%d%m%y')
        now = datetime.now()
        report_time = now.strftime("%d%m%y-%H%M%S")
        filename = 'ShootReport_%s_%s_%s_%s' % (shoot.project.abbreviation, shoot_date, urlify(shoot.location), report_time )

        context = {'shoot': shoot,
                   'report_filename' :filename, }

        #ShootReport_MAR_Location
        if not shoot:
            raise Http404('No shoot id matches the given query.')

        # response = PDFTemplateResponse(request=request,
        #                                template=self.template,
        #                                filename=filename,
        #                                context= context,
        #                                show_content_in_browser=False,
        #                                cmd_options=self.cmd_options,
        #                                )
        return None # response
        #return render(request, 'Reports/shoot_report.html', context) #for debugging to output it as html view