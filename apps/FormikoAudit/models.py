# the FormikoAudit contains all models and commands regarding
# audit, accounting and invoicing

from django.db import models
from apps.FileCollector.models import Project, ProjectVideo
from apps.FileCollector.models import Video, UserRole, Person, Crew
from apps.ProductManager.models import Resolution, VideoFormat



# LINE ITEMS

LI_PENDING_STATUS = 'OPEN'
LI_PAID_STATUS = 'PAID'
LI_DISCOUNTED_STATUS = 'DISCOUNTED'

class LineItem(models.Model):
    STATUS = (
        (LI_PENDING_STATUS, LI_PENDING_STATUS),
        (LI_PAID_STATUS, LI_PAID_STATUS),
        (LI_DISCOUNTED_STATUS, LI_DISCOUNTED_STATUS)
    )
    name = models.CharField(max_length=50)
    creator = models.ForeignKey('FileCollector.ProjectManager', on_delete=models.SET_NULL, blank=True, null=True)
    quantity = models.DecimalField(max_digits=5, decimal_places=0, default=0)
    price = models.DecimalField(max_digits=10, decimal_places=2, default=0.00) #the price it is sold
    cost = models.DecimalField(max_digits=10, decimal_places=2, default=0.00) # the actual internal costs associated with it
    project = models.ForeignKey(Project, on_delete=models.SET_NULL, blank=True, null=True, related_name="lineitems")
    video = models.ForeignKey(ProjectVideo, on_delete=models.SET_NULL, blank=True, null=True, related_name="projectvideos")
    description = models.TextField(blank=True)
    change_log = models.TextField(blank=True)
    status = models.CharField(max_length=15, choices=STATUS, default='PENDING')
    paid = models.DateTimeField(null=True, blank=True)
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'fo_lineitem'

    def __str__(self):
        return self.name


# SHOOTING REPORTS
class CameraSetting(models.Model):
    name = models.CharField(max_length=20, blank=True, null=True, default='')
    operator = models.ForeignKey(Crew, on_delete=models.SET_NULL, null=True, blank=True, related_name='camera_operator')
    whitebalance = models.DecimalField(max_digits=4, decimal_places=0, default=5600)
    framerate = models.DecimalField(max_digits=4, decimal_places=0, default=25)
    camera = models.CharField(max_length=20, blank=True, null=True, default='') #replace with own model in the future
    #resolution = models.ForeignKey(Resolution, on_delete=models.SET_NULL, blank=True, null=True, related_name="camerasettings") # already in the video format
    videoformat = models.ForeignKey(VideoFormat, on_delete=models.SET_NULL, blank=True, null=True, related_name="videoformats")
    colorprofile = models.CharField(max_length=20, blank=True, null=True, default='') #replace with own model in the future
    remark = models.TextField(blank=True, null=True)
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'fo_camerasetting'

    def __str__(self):
        return '%s (%s, %s)' % (self.name, self.camera, self.videoformat)

class Shoot(models.Model):
    project = models.ForeignKey(Project, on_delete=models.SET_NULL, blank=True, null=True, related_name="project_shoots")
    creator = models.ForeignKey('FileCollector.ProjectManager', on_delete=models.SET_NULL, blank=True, null=True)
    starttime = models.DateTimeField(null=True, blank=True)
    endtime = models.DateTimeField(null=True, blank=True)
    location = models.CharField(max_length=250)
    damages = models.TextField(blank=True)
    remark = models.TextField(blank=True)
    settings = models.ManyToManyField(CameraSetting, related_name='shoot_settings')
    videos = models.ManyToManyField(ProjectVideo, related_name='shoot_videos')
    crew = models.ManyToManyField(Crew, related_name='shoots', blank=True)
    change_log = models.TextField(blank=True,null=True)
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'fo_shoot'

    def __str__(self):
        return '%s (%s)' % (self.project, self.starttime)
    
    def get_video_ids_str(self):
        ids = []
        for item in self.videos.all():
            ids.append(str(item.id))
        return ','.join(ids)
    
    def get_crew_ids_str(self):
        ids = []
        for item in self.crew.all():
            ids.append(str(item.id))
        return ','.join(ids)

    def get_settings_ids_str(self):
        ids = []
        for item in self.settings.all():
            ids.append(str(item.id))
        return ','.join(ids)
