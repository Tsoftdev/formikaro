import json
from urllib.parse import unquote

from django.conf import settings
from django.db.models import Q
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import TemplateView
from django.utils.html import format_html
from django.utils.safestring import mark_safe
from django.http import Http404
import time

from django.http import HttpResponse
from django.contrib import messages
from django.http import JsonResponse

from django.template.loader import render_to_string
from django.shortcuts import render
from django.views.decorators.http import require_http_methods
from django.shortcuts import get_list_or_404, get_object_or_404

from .models import Asset, AssetPreset, AssetType, Task, TaskType, TASK_STATUS_OPEN, TASK_STATUS_ACTIVE, TASK_STATUS_FAILED, TASK_STATUS_COMPLETE, TASK_STATUS_ACTIVE_NAME, TASK_STATUS_FAILED_NAME, TASK_STATUS_COMPLETE_NAME, TASK_STATUS_OPEN_NAME, TaskPreset

from apps.FileCollector.models import Company, Client, Project,ProjectManager
from apps.ProductManager.models import Product, ProductBase
import datetime
from django.conf import settings

RUNTIME_SAVE_INTERVAL = settings.RUNTIME_SAVE_INTERVAL

#TASKS

# INDEX VIEW FOR TASKS
class TaskIndexView(LoginRequiredMixin, TemplateView):
    login_url = '/accounts/login/'

    def get(self, request, *args, **kwargs):
        task_list = Task.objects.all().order_by('-created')[:100]
        context = {'task_list': task_list}
        return render(request, 'Tasks/task_index.html', context)

    
class MyTaskIndexView(LoginRequiredMixin, TemplateView):
    login_url = '/accounts/login/'

    def get(self, request, *args, **kwargs):
        projectmanager_user = ProjectManager.objects.get(user=request.user)
        task_list = Task.objects.filter(user=projectmanager_user).order_by('-created')[:100]
        
        all_project_manager_users = ProjectManager.objects.all()
        context = {
            'task_list': task_list,
            'projectmanager' : projectmanager_user,
            'all_users': all_project_manager_users
        }
        return render(request, 'Tasks/mytasks.html', context)

def changeAjaxTask(request):
    task_id = request.POST['task_id']  
    name = request.POST['name']  
    description = request.POST['description']  
    user_id = request.POST['user_id']  
    status = request.POST['status']  
    deadline = request.POST['deadline']
    priority = request.POST['priority'] 
    
    item = Task.objects.get(id=task_id)
    if name != "undefined":
        item.name = name
    if description != "undefined":
        item.description = description
    if user_id != "undefined":
        item.user_id = user_id
    if status != "undefined":
        # if the status change indicates that there the task has come to a stop, record the stop time.
        if status == TASK_STATUS_COMPLETE or status == TASK_STATUS_FAILED:
            now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            item.endtime = now

        item.status = status
    if deadline != "undefined":
        if deadline != '':
            item.deadline = datetime.datetime.strptime(deadline, "%d.%m.%Y %H:%M")
        else:
            item.deadline = None
    if priority != "undefined":
        item.priority = priority

    item.save()

    return JsonResponse({"statusCode":2})

def updateRuntimeAjaxTask(request):
    task_id = request.POST['task_id']  
    runtime = request.POST['runtime']
    if not runtime: runtime = '0'
    stop_flag = request.POST['stop_flag']

    item = Task.objects.get(id=task_id)
    #print("status %s %s %s" %(item.status, TASK_STATUS_ACTIVE, stop_flag))

    if item.status != TASK_STATUS_ACTIVE:
       item.status = TASK_STATUS_ACTIVE

    if stop_flag != '':
        item.status = TASK_STATUS_OPEN

    # if this is a task that didn't have a starttime set, let's do it now
    if not item.starttime:
        now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        item.starttime = now
        #print("IN %s "% item.starttime)
    if item.runtime:
        actual_runtime = item.runtime
    else:
        actual_runtime = '0'
    item.runtime = int(actual_runtime) + int(runtime) #this is being tested working
    item.save()
    return JsonResponse({"statusCode":2})

def updateCompleteAjaxTask(request):
    task_id = request.POST['task_id']
    item = Task.objects.get(id=task_id)
    item.status = TASK_STATUS_COMPLETE
    item.save()
    return JsonResponse({"statusCode":2})
    
def createAjaxTask(request):
    project_id = request.POST['project_id']
    user_id = request.POST['user_id']
    status = request.POST['status']
    mode = request.POST['mode']
    starttimeP = request.POST['starttime']
    if starttimeP != '':
        starttimeP = datetime.datetime.strptime(starttimeP, "%d.%m.%Y %H:%M")
    else:
        starttimeP = None
    
    deadlineP = request.POST['deadline']
    if deadlineP != '':
        deadlineP = datetime.datetime.strptime(deadlineP, "%d.%m.%Y %H:%M")
    else:
        deadlineP = None
    priority = request.POST['priority']

    if request.POST['tasktype_id']:
      try:
          tasktype = TaskType.objects.get(id=request.POST['tasktype_id'])
      except:
          tasktype = None
    else:
        tasktype = None

    name = request.POST['name']
    description = request.POST['description']
    user_pm = ProjectManager.objects.filter(user=request.user)[:1]
    
    task = Task(
        name = name,
        description = description,
        user_id = user_id,
        mode = mode,
        status = status,
        type = tasktype,
        priority = priority,
        starttime = starttimeP,
        deadline = deadlineP,
        creator_id = user_pm[0].id,
    )
    task.save()
    try:
        project = Project.objects.get(id=project_id)
        project.tasks.add(task)
        messages.success(request, 'Task created!')
    except:
        return JsonResponse({'status': 'false', 'message':'Could not save task correctly. All data given?'})

    return JsonResponse({'status': 'success'})

# work in progress
def updateAjaxPresetTask(request):
    preset_id = request.POST['preset_id']
    # first of all see if the preset exists
    print("im in %s" % preset_id)
    try:
        taskpreset = TaskPreset.objects.get(id=preset_id)
    except:
        return JsonResponse({'status': 'error'})

    presetname = request.POST['presetName']
    project_id = request.POST['project_id']
    user_id = request.POST['user_id']
    status = request.POST['status']
    mode = request.POST['mode']
    try:
        tasktype = TaskType.objects.get(id=request.POST['tasktype_id'])
    except:
        tasktype = None
    print("tasktype %s (%s)" % (tasktype, request.POST['tasktype_id']))
    name = request.POST['name']
    priority = request.POST['priority']
    description = request.POST['description']
    user_pm = ProjectManager.objects.filter(user=request.user)[:1]

    #setting values
    taskpreset.title = presetname
    taskpreset.name = name
    taskpreset.description = description
    taskpreset.creator_id = user_pm[0].id
    taskpreset.type = tasktype
    taskpreset.status = status
    taskpreset.priority = priority
    taskpreset.mode = mode
    print("im save %s [%s] " % (taskpreset, taskpreset.id))
    try:
        taskpreset.save()
    except Exception as e:
        print("not saving (%s) " % e)
        return JsonResponse({'status': 'error'})

    return JsonResponse({'status': 'success'})

def createAjaxPresetTask(request):
    presetname = request.POST['presetName']
    project_id = request.POST['project_id']
    user_id = request.POST['user_id']
    status = request.POST['status']
    mode = request.POST['mode']
    #starttime = request.POST['starttime'] # presets don't neet begin time or endtime
    #starttimeP = datetime.datetime.strptime(starttime, "%d.%m.%Y %H:%M")
    
    #endtimeP = request.POST['endtime']
    #if endtimeP != '':
    #    endtimeP = datetime.datetime.strptime(endtimeP, "%d.%m.%Y %H:%M")
    #else:
    #    endtimeP = None

    # these are not needed for now for any preset
    starttimeP = None
    endtimeP = None
    deadlineP = None
    
    priority = request.POST['priority']
    try:
        tasktype = TaskType.objects.get(id=request.POST['tasktype_id'])
    except:
        tasktype = None

    name = request.POST['name']
    description = request.POST['description']
    user_pm = ProjectManager.objects.filter(user=request.user)[:1]
    
    task = TaskPreset(
        title = presetname,
        name = name,
        description = description,
        user_id = user_id,
        mode = mode,
        type = tasktype,
        status = status,
        priority = priority,
        starttime = starttimeP,
        deadline=deadlineP,
        endtime = endtimeP,
        creator_id = user_pm[0].id,
    )
    task.save()
    #project = Project.objects.get(id=project_id)
    #project.tasks.add(task)

    return JsonResponse({'status': 'success'})

class TaskAddView(LoginRequiredMixin, TemplateView):
    login_url = '/accounts/login/'

    def get(self, request, *args, **kwargs):
        project_id = kwargs.get('project_id', None)
        try:
            project = Project.objects.get(id=project_id)
        except:
            project = None

        project_list = Project.objects.filter(projectmanager__user=request.user)
        preset_tasks = TaskPreset.objects.all()
        task_types = TaskType.objects.all()
        context = {'project_list': project_list,  'project': project, 'preset_tasks': preset_tasks, 'task_types' : task_types,}

        return render(request, 'Tasks/add_task.html', context)




class ProjectTaskAddView(LoginRequiredMixin, TemplateView):
    login_url = '/accounts/login/'

    def get(self, request, *args, **kwargs):
        project_id = kwargs.get('project_id', None)
        project = Project.objects.get(id=project_id)
        #project_list = Project.objects.filter(projectmanager__user=request.user)
        preset_tasks = TaskPreset.objects.all()
        task_types = TaskType.objects.all()
        context = {'project': project, 'preset_tasks': preset_tasks, 'task_types' : task_types,}
        return render(request, 'Tasks/add_task.html', context)

def getProjectManagerAjax(request):
    project_id = request.POST['project_id']
    data = []
    try:
        project = Project.objects.get(id=project_id)
    except:
        return JsonResponse({"data": data})

    for tmp in project.projectmanager.all():
        data.append({'id': tmp.id, 'name': tmp.firstname + ' ' + tmp.lastname })
    return JsonResponse({ "data": data })

def getPresetTaskAjax(request):
    pre_task_id = request.POST['pre_task_id']
    task = TaskPreset.objects.get(id=pre_task_id)
    if task.type:
        tasktype_id = task.type.id
    else:
        tasktype_id = 0


    data = {
        'name': task.name,
        'status': task.status,
        'mode': task.mode,
        'tasktype' : tasktype_id,
        'starttime': task.starttime.strftime('%d.%m.%Y %H:%M') if task.starttime != None else '',
        'deadline': task.starttime.strftime('%d.%m.%Y %H:%M') if task.deadline != None else '',
        'priority': task.priority,
        'description': task.description
    }
    
    return JsonResponse({ "data": data })


class TaskStatusView(LoginRequiredMixin, TemplateView):
    login_url = '/accounts/login/'
        
    def get(self, request, **kwargs):
        filter_status = kwargs.get('status', None)
        filter_status = filter_status.upper()
        tmp_status = filter_status
        if filter_status == TASK_STATUS_OPEN_NAME:
            tmp_status = TASK_STATUS_OPEN
        if filter_status == TASK_STATUS_ACTIVE_NAME:
            tmp_status = TASK_STATUS_ACTIVE
        if filter_status == TASK_STATUS_COMPLETE_NAME:
            tmp_status = TASK_STATUS_COMPLETE
        if filter_status == TASK_STATUS_FAILED_NAME:
            tmp_status = TASK_STATUS_FAILED
        
        if filter_status == TASK_STATUS_OPEN_NAME or filter_status == TASK_STATUS_ACTIVE_NAME or filter_status == TASK_STATUS_COMPLETE_NAME or filter_status == TASK_STATUS_FAILED_NAME:
            # the problem is that a status has a name and a value...
            # so by just getting the name we cant determin the value yet
            task_list = Task.objects.filter(status=tmp_status)
            context = {'task_list': task_list,
                       'status' : filter_status }

            return render(request, 'Tasks/task_index.html', context)
        else:
            context = { '':''}
            return render(request, 'Tasks/task_index.html', context)
        #    raise Http404('No task status [%s] found' % filter_status)


class MyTaskStatusView(LoginRequiredMixin, TemplateView):
    login_url = '/accounts/login/'

    def get(self, request, **kwargs):
        project_id = kwargs.get('project_id', None)
        try:
            project = Project.objects.get(id=project_id)
        except:
            project = None

        filter_status = kwargs.get('status', None)
        filter_status = filter_status.upper()
        tmp_status = filter_status
        if filter_status == TASK_STATUS_OPEN_NAME:
            tmp_status = TASK_STATUS_OPEN
        if filter_status == TASK_STATUS_ACTIVE_NAME:
            tmp_status = TASK_STATUS_ACTIVE
        if filter_status == TASK_STATUS_COMPLETE_NAME:
            tmp_status = TASK_STATUS_COMPLETE
        if filter_status == TASK_STATUS_FAILED_NAME:
            tmp_status = TASK_STATUS_FAILED

        if filter_status == TASK_STATUS_OPEN_NAME or filter_status == TASK_STATUS_ACTIVE_NAME or filter_status == TASK_STATUS_COMPLETE_NAME or filter_status == TASK_STATUS_FAILED_NAME:
            # the problem is that a status has a name and a value...
            # so by just getting the name we cant determin the value yet
            projectmanager_user = ProjectManager.objects.get(user=request.user)
            task_list = Task.objects.filter(Q(user=projectmanager_user) & Q(status=tmp_status)).order_by('-created')[:100]
            all_project_manager_users = ProjectManager.objects.all()
            context = {
                'task_list': task_list,
                'projectmanager': projectmanager_user,
                'all_users': all_project_manager_users,
                'status' : filter_status
            }

            return render(request, 'Tasks/mytasks.html', context)
        else:
            context = {'': ''}
            return render(request, 'Tasks/mytasks.html', context)
        #    raise Http404('No task status [%s] found' % filter_status)

# outputs all tasks of a project
# if called with 'status' returns filtered output.
# function replaced ProjectTasksView
class ProjectTaskStatusView(LoginRequiredMixin, TemplateView):
    login_url = '/accounts/login/'

    def get(self, request, **kwargs):
        project_id = kwargs.get('project_id', None)
        try:
            project = Project.objects.get(id=project_id)
        except:
            raise Http404('No project id [%s] matches the given query.' % project_id)

        filter_status = kwargs.get('status', None)

        if filter_status:
            filter_status = filter_status.upper()
            tmp_status = filter_status
            if filter_status == TASK_STATUS_OPEN_NAME:
                tmp_status = TASK_STATUS_OPEN
            if filter_status == TASK_STATUS_ACTIVE_NAME:
                tmp_status = TASK_STATUS_ACTIVE
            if filter_status == TASK_STATUS_COMPLETE_NAME:
                tmp_status = TASK_STATUS_COMPLETE
            if filter_status == TASK_STATUS_FAILED_NAME:
                tmp_status = TASK_STATUS_FAILED

        if filter_status == TASK_STATUS_OPEN_NAME or filter_status == TASK_STATUS_ACTIVE_NAME or filter_status == TASK_STATUS_COMPLETE_NAME or filter_status == TASK_STATUS_FAILED_NAME:
            task_list = project.tasks.filter(status=tmp_status)
        else:
            task_list = project.tasks.all

        projectmanager_user = ProjectManager.objects.get(user=request.user)
        #task_list = project.tasks.filter(status=tmp_status)
        #task_list = Task.objects.filter(Q(status=tmp_status) & Q(status=tmp_status)).order_by('-created')[:100]
        all_project_manager_users = ProjectManager.objects.all()
        
        project_manager = project.projectmanager.all()[0]
        if project_manager == projectmanager_user and project_manager.is_manager:
            is_editable = True
        else:
            is_editable = False

        context = {
            'project' : project,
            'task_list': task_list,
            'projectmanager': projectmanager_user,
            'all_users': all_project_manager_users,
            'status' : filter_status,
            'is_editable': is_editable
        }

        return render(request, 'Projects/project_tasks.html', context)




#ASSETS

#add order manually page
class AssetCreateView(LoginRequiredMixin, TemplateView):
    def get(self, request, *args, **kwargs):
        #list all companies (the clients will be loaded via AJAX)
        company_id = kwargs.get('company_id', None)
        client_id =  kwargs.get('client_id', None)
        try:
            this_client = Client.objects.get(id=client_id)
            clients = Client.objects.filter(company=this_client.company)
        except:
            this_client = None
            clients = None
        try:
            this_company = Company.objects.get(id=company_id)
        except:
            this_company = None
        
        companies = Company.objects.all()
        #companies = Company.objects.all()
        asset_presets = AssetPreset.objects.all()
        asset_types = AssetType.objects.all()
        #show all products that are either active or at least have an FSIN
        #products = Product.objects.filter(Q(is_active=True) & ~Q(fsin=None))
        context = { 'companies': companies,
                    'company': this_company,
                    'client': this_client,
                    'clients':clients,
                    'asset_types': asset_types,
                    'asset_presets': asset_presets,}
        return render(request, 'Assets/create_asset.html', context)


# DETAIL VIEW FOR TASK
class TaskPageView(LoginRequiredMixin, TemplateView):
    login_url = '/accounts/login/'

    def get(self, request, **kwargs):
        task_id = kwargs.get('task_id', None)
        try:
            task = Task.objects.get(id=task_id)
        except:
            task = None
            #raise Http404('No Task matches the given query.')

        try:
            project = Project.objects.get(tasks=task_id)
        except:
            project = None
        #if not task:
        #    raise Http404('No Task matches the given query.')

        context = { 'task': task, 'task_id': task_id, 'project': project}

        return render(request, 'Tasks/task_detail.html', context)

#EDIT VIEW FOR TASK
class TaskEditPageView(LoginRequiredMixin, TemplateView):
    login_url = '/accounts/login/'

    def get(self, request, **kwargs):
        task_id = kwargs.get('task_id', None)
        try:
            task = Task.objects.get(id=task_id)
        except:
            task = None
            #raise Http404('No Task matches the given query.')

        try:
            project = Project.objects.get(tasks=task_id)
        except:
            project = None


        project_list = Project.objects.filter(projectmanager__user=request.user)
        preset_tasks = TaskPreset.objects.all()
        task_types = TaskType.objects.all()

        context = { 'task': task,
                    'task_id': task_id,
                    'project': project,
                    'preset_tasks' : preset_tasks,
                    'project_list' : project_list,
                    'task_types': task_types
                    }

        return render(request, 'Tasks/task_edit.html', context)



# INDEX VIEW FOR ASSETS
class AssetIndexView(LoginRequiredMixin, TemplateView):
    login_url = '/accounts/login/'

    def get(self, request, *args, **kwargs):
        asset_list = Asset.objects.all
        context = {'asset_list': asset_list}
        return render(request, 'Assets/asset_index.html', context)


class AssetPageView(LoginRequiredMixin, TemplateView):
    def get(self, request, **kwargs):
        asset_id = kwargs.get('asset_id', None)
        try:
            asset = Asset.objects.get(id=asset_id)
        except:
            raise Http404('No Order matches the given query.')

        if not asset:
            raise Http404('No Order matches the given query.')

        context = {
            'asset': asset
        }

        return render(request, 'Assets/asset_detail.html', context)
    
class FormikaroSettings(LoginRequiredMixin, TemplateView):
    login_url = '/accounts/login/'

    def get(self, request, *args, **kwargs):
        existing_settings = []
        try:
            env_file = open(settings.BASE_DIR.joinpath('.env'), 'r')
            file_settings = env_file.readlines()
            for line in file_settings:
                line = line.strip()
                if line:
                    key_value_pair = line.split('=')
                    existing_settings.append({key_value_pair[0]: key_value_pair[1]})

        except Exception as exc:
            print(exc)
        context = {'existing_settings': existing_settings}
        return render(request, 'Formikaro/settings.html', context)

    def post(self, request, *args, **kwargs):
        new_settings = request.POST
        with open(settings.BASE_DIR.joinpath('.env'), 'w') as f:
            for key, value in new_settings.items():
                if key == 'csrfmiddlewaretoken':
                    continue
                f.write('{key}={value}\n'.format(key=unquote(key), value=unquote(value)))
        existing_settings = []
        try:
            env_file = open(settings.BASE_DIR.joinpath('.env'), 'r')
            file_settings = env_file.readlines()
            for line in file_settings:
                line = line.strip()
                if line:
                    key_value_pair = line.split('=')
                    existing_settings.append({key_value_pair[0]: key_value_pair[1]})

        except Exception as exc:
            print(exc)
        context = {'existing_settings': existing_settings}
        return render(request, 'Formikaro/settings.html', context)


class FormikaroLogViewer(LoginRequiredMixin, TemplateView):
    login_url = '/accounts/login/'

    def get(self, request, *args, **kwargs):
        try:
            env_file = open(settings.BASE_DIR.joinpath('local.log'), 'r')
            log_entries = env_file.readlines()
        except Exception as exc:
            print(exc)
        context = {'log_entries': log_entries}
        return render(request, 'Formikaro/view_log.html', context)


#AJAX CALLS

def removeAssetProductbase(request):
    if request.method == 'GET':
        #if request.POST.get('productbase_id'):
        #print ("productbase:", request.GET['productbase_id'])
        #print ("asset_id:",request.GET['asset_id'])
        #productbase_id = kwargs.get('productbase_id', None)
        productbase_id = request.GET['productbase_id']
        asset_id = request.GET['asset_id']
        #this_productbase = get_object_or_404(ProductBase, pk=productbase_id)
        data = dict()
    
        
        #data['form_is_valid'] = True  # This is just to play along with the existing code
        #books = Book.objects.all()
        asset = Asset.objects.get(id=asset_id)
        productbase = ProductBase.objects.get(id=productbase_id)
        productbase.assets.remove(asset)
        productbase.save()
        
        assets = productbase.assets.all()
        
        context = { 'assets':assets}
        
        data['asset_list'] = render_to_string('Products/productbase_assets_ajax.html', context)
        
    #else:
        #context = {'book': book}
        #data['html_form'] = render_to_string('books/includes/partial_book_delete.html',
        #    context,
        #    request=request,
        #)
        
    return JsonResponse(data)

class getProductBaseAssetsView(TemplateView):
      def get(self, request, **kwargs):
            productbase_id = request.GET['productbase_id']
            if request.method == 'GET':
                #assets = ProductBase.objects.filter(id=productbase_id)
                productbase = ProductBase.objects.select_related().filter(id=productbase_id)[0]
                assets = productbase.assets.all()

                context = {'assets': assets}
                return render(request, 'Products/productbase_assets_ajax.html', context)
            else:
                context = { 'assets':''}
                return render(request, 'Products/productbase_assets_ajax.html', context)
        
            

#ajax calls searching via ajax
def searchGlobalAssets(request):
        if request.method == 'GET':
            asset_name = request.GET['assetName']
            
            # we want to get all assets that could match the name but only
            # it they are available to everybody
            assets = Asset.objects.filter(Q(name__icontains=asset_name) | Q(value__icontains=asset_name)).exclude(~Q(company_owner__isnull=True) | ~Q(client_owner__isnull=True))
            
            #productbase = ProductBase.objects.select_related().filter(id=productbase_id)[0]
            #assets = productbase.assets.all()
            
            i=0
            data = {}
            #make a nice json object for the <select> field to get populated
            for asset in assets:
                data[i] = {}
                data[i][0] = asset.id
                data[i][1] = asset.name + ' (' + str(asset.value) + ')'
                data[i][2] = asset.assettype.title

                i = i + 1
                
            if i == 0:
                data[i] ={}
                data[i][0] = ''
                data[i][1] = 'No assets found'
            response = json.dumps(data)

            return HttpResponse(response) # Sending an success response
        else:
            return HttpResponse("Request method is not a GET")

        
#ajax calls searching via ajax
def searchClientAssets(request):
        if request.method == 'GET':
            asset_name = request.GET['assetName']
            client_id = request.GET['client_id']
            
            # we want to get all assets that could match the name but only
            # it they are available to everybody
            this_client = Client.objects.get(id=client_id)
            
            assets = Asset.objects.filter(Q(name__icontains=asset_name) | Q(value__icontains=asset_name)).exclude(~Q(company_owner__id=this_client.company.id) | ~Q(client_owner__id=this_client.id))
            #.exclude(~Q(company_owner=this_client.company.id) | ~Q(client_owner=this_client.id))
            
            #productbase = ProductBase.objects.select_related().filter(id=productbase_id)[0]
            #assets = productbase.assets.all()
            
            i=0
            data = {}
            #make a nice json object for the <select> field to get populated
            for asset in assets:
                data[i] = {}
                data[i][0] = asset.id
                data[i][1] = asset.name + ' (' + str(asset.value) + ')'
                data[i][2] = asset.assettype.title

                i = i + 1
                
            if i == 0:
                data[i] ={}
                data[i][0] = ''
                data[i][1] = 'No assets found'
            # debug:
            #data[i] = {}
            #data[i][0] = 1
            #data[i][1] = this_client.get_fullname() + this_client.company.name
            response = json.dumps(data)

            return HttpResponse(response) # Sending an success response
        else:
            return HttpResponse("Request method is not a GET")
        
#ajax calls for add order page
def selectAssetPresets(request):
    if request.method == 'GET':
        #company_id = request.GET['company_id']
        asset_presets = AssetPreset.objects.all()
        i=0
        data = {}
        #make a nice json object for the <select> field to get populated
        for asset_preset in asset_presets:
            data[i] = {}
            data[i][0] = asset_preset.id
            data[i][1] = asset_preset.name + ' (' + asset_preset.title + ')'
            #data[i][2] = asset_preset.value

            i = i + 1
            
        response = json.dumps(data)

        return HttpResponse(response) # Sending an success response
    else:
        return HttpResponse("Request method is not a GET")
    
# this function is called via ajax to add an asset to a productbase
def addAssetProductBase(request):
    if request.method == 'POST':
        data = {}
        data[0] = ''
        noError = True
        
        if request.POST.get('productbase_id'):
            productbase_id =  request.POST['productbase_id']
        else:
            #no productbase id given
            data[0] = False
            data[1] = 'ERROR no ProductBaseId given'
            noError = False
        
        if request.POST.get('foundAssets'):
            asset_ids = request.POST.getlist('foundAssets')
        else:
            #no productbase id given
            data[0] = False
            data[1] += 'ERROR no Assets given'
            noError = False
            
        if noError:
            try:
                this_productbase = ProductBase.objects.get(id=productbase_id)
            except:
                data[0] = False
                data[1] = 'ProductBase (%s) doesn\'t exist' % productbase_id
                noError = False
            
            if noError:
                i = 2
                for asset_id in asset_ids:
                    this_asset = Asset.objects.get(id=int(asset_id))
                    this_productbase.assets.add(this_asset)
                    data[i] = asset_ids
                    i=i+1

                this_productbase.save()
                data[0] = True
                data[1] = 'Successfully added assets'
        
        response = json.dumps(data)
        
        return HttpResponse(response)
    else:
        return HttpResponse("didn't use post")

    
# this function is called via ajax to create an asset
def createAsset(request):
    if request.method == 'POST':
        #response = request.POST['test']
        this_asset = None
        this_company = None
        data = {}
        
        asset_name = request.POST['assetName']
        asset_type = request.POST['assetType']
        asset_value = request.POST['assetValue']
        asset_filename = request.POST['assetFilename']
        asset_json = request.POST['assetJSON']
        asset_source = request.POST['assetSource']
        asset_description = request.POST['assetDescription']
        
        if request.POST.get('checkClient', ''):
            asset_client = request.POST['selectClient']
            try:
                this_client = Client.objects.filter(id=asset_client)[0]
            except:
                this_client = None
        else:
            this_client = None
            if request.POST.get('checkCompany', ''):
                asset_company = request.POST['selectCompany']
                try:
                    this_company = Company.objects.filter(id=asset_company)[0]
                except:
                    this_company = None
            else:
                this_company = None
        
        # if everything works let's create this asset
        try:
            this_asset_type = AssetType.objects.filter(id=asset_type)[0]
        except Exception as e:
            data[0] = False
            data[1] = 'Error, could not find AssetTypet %s (%s)' % (asset_type, e)
            response = json.dumps(data)
            return HttpResponse(response)
        
        # this is also checked via javascript on the frontend but we 
        # want to make sure we get this right and tell the user if something is wrong
        maxlength = this_asset_type.maxlength
        if not maxlength:
            maxlength = 10000
            
        if len(asset_value) > int(maxlength):
            data[0] = False
            data[1] = 'Error, value %s too long for maxlengh (%s)' % (asset_value, maxlength)
        else:
            try:
                #before we try to create this one, let's see if there is any
                this_asset = Asset.objects.filter(Q(name=asset_name) & Q(client_owner=this_client) & Q(company_owner=this_company))
                if this_asset:
                    data[0] = False
                    if this_client:
                        data[1] = 'Error, could not add asset %s because it already exists for this client %s ' % (asset_name, this_client)
                    elif this_company:
                        data[1] = 'Error, could not add asset %s because it already exists for this company %s ' % (asset_name, this_company)
                    else:
                        data[1] = 'Error, could not add asset %s because it already exists (global) ' % (asset_name)
                else:
                    this_asset = Asset(name=asset_name, value=asset_value, source=asset_source, assettype=this_asset_type, company_owner=this_company, client_owner=this_client, description=asset_description)
                    this_asset.save()

                    # this logic defines that an asset defined by client is prioritized over a company
                    # we don't check here if the client belong to the selected company we just assume that 
                    # if a client has been selected the asst will be his/hers
                    if request.POST.get('checkClient', ''):
                        # same goes for the client
                        if this_client:
                            this_client.assets.add(this_asset)
                            this_client.save()
                    elif request.POST.get('checkCompany', ''):
                        if this_company:
                            this_company.assets.add(this_asset)
                            this_company.save()

                    data[0] = True
                    data[1] = 'Successfully added asset %s ' % asset_name
            except Exception as e:
                data[0] = False
                data[1] = 'Error, could not add asset %s (%s)' % (asset_name, e)
        
        data[2] = str(this_company)
        data[3] = str(this_asset_type)
        
        data[4] = str(this_asset)
        data[5] = str(len(asset_value))
        data[6] = maxlength
        response = json.dumps(data)
        
        #return HttpResponse(request.POST.items())
        return HttpResponse(response)
    else:
        return HttpResponse("not working yet")




def createPresetAsset(request):
    if request.method == 'POST':
        presetasset_name = request.POST['preset_name']
        asset_name = request.POST['assetName']
        asset_type = request.POST['assetType']
        asset_value = request.POST['assetValue']
        asset_filename = request.POST['assetFilename']
        asset_json = request.POST['assetJSON']
        asset_source = request.POST['assetSource']
        asset_description = request.POST['assetDescription']

        data = {}
        asset_type_obj = AssetType.objects.get(id=asset_type)
        maxlength = asset_type_obj.maxlength
        if not maxlength:
            maxlength = 10000
        if len(asset_value) > int(maxlength):
            data[0] = False
            data[1] = 'Error, value %s too long for maxlengh (%s)' % (asset_value, maxlength)
        
        this_asset = Asset.objects.filter(Q(name=asset_name) & Q(client_owner=None) & Q(company_owner=None))
        if this_asset:
            data[0] = False
            data[1] = 'Error, could not add asset %s because it already exists (global) ' % (asset_name)
        else:
            this_asset = AssetPreset(title=presetasset_name, name=asset_name, value=asset_value, source=asset_source, assettype=asset_type_obj, description=asset_description)
            this_asset.save()
            data[0] = True
        
        response = json.dumps(data)
        return HttpResponse(response)
    else:
        return HttpResponse("not working yet")


def editAsset(request):
    asset_id = request.POST['asset_id']
    asset_name = request.POST['asset_name']
    asset_value = request.POST['asset_value']
    obj = Asset.objects.get(id=asset_id)
    obj.name = asset_name
    obj.value = asset_value
    obj.save()
    return HttpResponse("success")


def deleteTask(request):
    task_id = request.POST['task_id']
    obj = Task.objects.get(id=task_id)
    obj.delete()

    return HttpResponse("success")

def deleteAsset(request):
    asset_id = request.POST['asset_id']
    suffix = request.POST['suffix']
    client_id = request.POST['client_id']
    company_id = request.POST['company_id']
    obj = Asset.objects.get(id=asset_id)
    if suffix == "c" or suffix == "e": # client asset
        if obj.client_owner is None and obj.company_owner is None:
            pass
        else:
            obj.delete()
        client = Client.objects.get(id=client_id)
        client.assets.remove(asset_id)
    elif suffix == "co":
        if obj.client_owner is None and obj.company_owner is None:
            pass
        else:
            obj.delete()
        company = Company.objects.get(id=company_id)
        company.assets.remove(asset_id)

    return HttpResponse("success")

def getAssetType (request):
    if request.method == 'GET':
        asset_type_id = request.GET['asset_type_id']
        asset_type = AssetType.objects.filter(id = asset_type_id)[0]
        data = {}
        #make a nice json object for the <select> field to get populated
        data[0] = asset_type.id
        data[1] = asset_type.title
        data[2] = asset_type.extension
        data[3] = asset_type.is_file
        data[4] = asset_type.maxlength
        data[5] = asset_type.description
        
        response = json.dumps(data)

        return HttpResponse(response) # Sending an success response
    else:
        return HttpResponse("Request method is not a GET")

    
def getAssetPreset(request):
    if request.method == 'GET':
        asset_preset_id = request.GET['asset_preset_id']
        asset_preset = AssetPreset.objects.filter(id = asset_preset_id)[0]
        data = {}
        #make a nice json object for the <select> field to get populated
        data[0] = asset_preset.id
        data[1] = asset_preset.name 
        data[2] = asset_preset.value
        data[3] = asset_preset.assettype.is_file
        data[4] = asset_preset.assettype.extension
        
        asset_preset_maxlength = asset_preset.maxlength
        asset_preset_type_maxlength = asset_preset.assettype.maxlength
        if asset_preset_maxlength:
            maxlength = asset_preset_maxlength
        else:
            maxlength = asset_preset_type_maxlength
            
        data[5] = maxlength
        data[6] = asset_preset.source
        data[7] = asset_preset.assettype.id
        response = json.dumps(data)

        return HttpResponse(response) # Sending an success response
    else:
        return HttpResponse("Request method is not a GET")
        

