#this extends the admin index
from django.contrib.admin import AdminSite

class CustomAdmin(AdminSite):
    index_template = 'admin/base_site.html'


custom_admin_site = CustomAdmin(name='admin')