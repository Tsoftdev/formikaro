from apps.FileCollector.models import ProjectManager
from .models import TASK_STATUS_ACTIVE, Task, TASK_STATUS_OPEN
from django.conf import settings
from django.db.models import Q
import os



def get_top_five_tasks(request):
    latest_tasks = []
    if request.user.is_anonymous is False:
        projectmanager_user = ProjectManager.objects.get(user=request.user)
        latest_tasks = Task.objects.filter(user=projectmanager_user).order_by('-priority', 'created')[0:5]
    
    return {
        'top_tasks': latest_tasks,
    }

def get_open_tasks(request):
    latest_tasks = []
    if request.user.is_anonymous is False:
        projectmanager_user = ProjectManager.objects.get(user=request.user)
        latest_tasks = Task.objects.filter(Q(user=projectmanager_user) & (Q(status=TASK_STATUS_OPEN) | Q(status=TASK_STATUS_ACTIVE))).order_by('-priority', 'created')
        for temp in latest_tasks:
            temp.project_name =  temp.tasks.all()[0].name if len(temp.tasks.all()) > 0 else ''
        #latest_tasks = Task.objects.annotate(Count('project')).filter(user=projectmanager_user,status=TASK_STATUS_OPEN).order_by('-priority', 'created')
    return {
        'open_tasks': latest_tasks
    }