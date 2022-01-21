from django.urls import path
from django.conf.urls import url, include

from apps.FileCollector.views import company_csv_import

from . import views

from .views import IndexView, IntakePageView, OrderIndexView, OrderPageView, IntakeIndexView, ClientIndexView, NotYetView, ClientPageView, CompanyIndexView, CompanyPageView, ProductIndexView, ProductPageView, OrderStatusView, CompanyOrderView, CompanyAssetsView, CompanyBillingView,ProjectvideoPageView
#ajax
from .views import ajaxProductImageDataAdd, ajaxSubProductImageTextDelete, ajaxSubProductImageTextUpdate, ajaxSubProductInfo, ajaxSubProductOrder, consolidateAjaxProjectVideos,loadAjaxProjectVideos, getAjaxEditProjectVideo, getAjaxSelectProjectVideo, getAjaxSelectVideo, product_csv_import, OrderAddView, ClientOrdersView, ClientAssetsView, ClientBillingView, ClientVideosView, ProductBasePageView, createAjaxOrder, CreateWizard, BetaTestView, removeAjaxLinkedProjectVideo, saveAjaxSelectProjectVideo, ajaxProductImageTextAdd


from apps.FormikoBot.views import AssetIndexView,AssetPageView, AssetCreateView, createAjaxPresetTask, updateAjaxPresetTask, selectAssetPresets, getAssetPreset, createAsset, \
    getAssetType, searchGlobalAssets, addAssetProductBase, getProductBaseAssetsView, removeAssetProductbase, \
    searchClientAssets, FormikaroSettings, FormikaroLogViewer, getProjectManagerAjax, getPresetTaskAjax, createAjaxTask

from .views import addAjaxAssetToClient, addAjaxAssetToCompany, changeAjaxStatusOrder, changeAjaxStatusOrderProduct, changeAjaxStatusProject, deleteAjaxOrderProduct, uploadAjaxOrders, deleteAjaxProductImageInfo
from .views import checkAjaxStatusProduct, saveAjaxProductTextInfo, deleteAjaxProductTextInfo, changeProductBaseIntake
#from .views import createOrderProductFolder, deleteProjectVideo, ProjectCreateView, ProjectIntakesView, ProjectVideosView, ProjectBillingView, ProjectIndexView, ProjectDashboardView, ProjectCreateView
from .views import createOrderProductFolder, ProjectCreateView, ProjectIntakesView, ProjectVideosView, ProjectShootsView, ProjectBillingView, ProjectIndexView, ProjectDashboardView, ProjectShootsView, deleteProjectVideo, ProjectPageView, getAddVideoTemplate, saveAjaxProject, saveAjaxProjectVideo, deleteAjaxVideo, deleteAjaxProjectVideo, saveAjaxProjectLineItem, deleteAjaxProjectLineItem, markUserNotificationsRead, getUserNotifications

from apps.FormikoBot.views import editAsset, deleteAsset, deleteTask, createPresetAsset, TaskIndexView, MyTaskIndexView, TaskAddView, ProjectTaskAddView,ProjectTaskStatusView , TaskEditPageView, TaskStatusView, MyTaskStatusView, TaskPageView, changeAjaxTask, updateRuntimeAjaxTask, updateCompleteAjaxTask
from apps.FileDelivery.views import DeliveryOverview

from .views import changeAjaxIntakeClient, getAjaxIntakeOrder, changeAjaxIntakeOrder, getAjaxIntakeProject, changeAjaxIntakeProject, changeAjaxIntakeRemark, VideoPageView, VideoIndexView
from .views import getAjaxEditOrderProdAsset, changeAjaxEditOrderProdAsset, renderAjaxOrderProduct
from apps.FormikoAudit.views import ProjectShootPDF

from .views import saveAjaxProjectShoot, deleteAjaxProjectShoot, getAddCrewTemplate, saveAjaxShootCrew, deleteAjaxShootCrew, getAddCameraTemplate, saveAjaxShootCamera, deleteAjaxShootCamera


app_name = 'FileCollector'
urlpatterns = [


    path('', IndexView.as_view(), name='index'),
    # path('test/', index2, name='index2'),
    path('beta/', BetaTestView.as_view(), name='beta'), #testing page only
    path('intakes/', IntakeIndexView.as_view(), name='intakes'),
    path('intakes/<int:intake_id>/', IntakePageView.as_view(), name='intake_detail'),
    path('change-intake-client/', changeAjaxIntakeClient, name='change-intake-client'),  #ajax
    path('get-intake-order-available/', getAjaxIntakeOrder, name='get-intake-order-available'),  #ajax
    path('change-intake-order/', changeAjaxIntakeOrder, name='change-intake-order'),  #ajax
    path('get-intake-project-available/', getAjaxIntakeProject, name='get-intake-project-available'),  #ajax
    path('change-intake-project/', changeAjaxIntakeProject, name='change-intake-project'),  #ajax
    path('change-intake-remark/', changeAjaxIntakeRemark, name='change-intake-remark'),  #ajax
    path('get-user-notifications/', getUserNotifications, name='get-user-notifications'),  #ajax
    path('mark-user-notifications-read/', markUserNotificationsRead, name='mark-user-notifications-read-ajax'),  #ajax

    

    path('wizard/new', CreateWizard.as_view(), name='create_wizard'),

    path('assets/', AssetIndexView.as_view(), name='assets'),
    path('assets/<int:asset_id>/', AssetPageView.as_view(), name='asset_detail'),
    path('assets/create', AssetCreateView.as_view(), name='create_asset'),
    path('assets/create/ajax', createAsset, name='create_asset_ajax'), #ajax
    path('assets/create/preset_ajax', createPresetAsset, name='create_presetasset_ajax'), #ajax
    path('assets/edit/ajax', editAsset, name='edit_asset_ajax'), #ajax
    path('assets/delete/ajax', deleteAsset, name='delete_asset_ajax'), #ajax
    path('tasks/delete/ajax', deleteTask, name='delete_task_ajax'), #ajax
    

    #path('assets/add/client/<int:client_id>/', AssetClientAddView.as_view(), name='add_asset_client'),
    path('selectAssetPresets/', selectAssetPresets, name='select_assetpresets'),   #ajax    
    path('getAssetPreset/', getAssetPreset, name='get_assetpreset'),   #ajax    
    path('getProductBaseAssets/ajax/', getProductBaseAssetsView.as_view(), name='get_productbase_assets_ajax'),   #ajax    
    path('removeAssetProductbase/ajax/', removeAssetProductbase, name='remove_asset_productbase'),   #ajax    
    
    #path('createAssetAjax', createAsset, name='create_asset_ajax'),   #ajax    
    path('addAssetProductBase', addAssetProductBase, name='add_asset_productbase'),   #ajax    
    path('getAssetType/', getAssetType, name='get_assettype'),   #ajax    
    path('searchGlobalAssets/', searchGlobalAssets, name='search_assets'),   #ajax    
    path('searchClientAssets', searchClientAssets, name='search_client_assets'),   #ajax    
    
    path('orders/', OrderIndexView.as_view(), name='orders'),
    path('orders/add', OrderAddView.as_view(), name='add_order'),
    path('selectclients/', views.selectClients, name='select_clients'),   #ajax
    
    path('orders/status/<str:status>/', OrderStatusView.as_view(), name='orders_by_status'),
    path('orders/<int:order_id>/', OrderPageView.as_view(), name='orders_detail'),
    path('check-video-render-progress', views.updateOrderVideosRenderProgressAjaxView, name='check-render-progress'),  #ajax
    path('render-order-product', views.renderAjaxOrderProduct, name='render_ajax_order_product'),
    path('createorder/', views.createOrder, name='create_order'),   # #ajax
    path('create-ajax-order/', createAjaxOrder, name='create_ajax_order'),  #ajax
    path('change-status-order/', changeAjaxStatusOrder, name='change_status_order'),  #ajax

    path('change-status-order-product/', changeAjaxStatusOrderProduct, name='change_status_order_product'),  #ajax
    path('get-assets-from-order-id/', getAjaxEditOrderProdAsset, name='get-assets-from-order-id'),  #ajax
    path('change-assets-from-orderprod-id/', changeAjaxEditOrderProdAsset, name='change-assets-from-orderprod-id'),  #ajax

    path('delete-order-product/', deleteAjaxOrderProduct, name='delete-order-product'),  #ajax
    path('upload-orders/', uploadAjaxOrders, name='upload-orders'),  #ajax
    path('create-order-product-folder/', createOrderProductFolder, name='create-order-product-folder'),  #ajax
    
    path('clients/', ClientIndexView.as_view(), name='clients'),
    
    path('clients/<int:client_id>/', ClientPageView.as_view(), name='client_detail'),
    path('clients/<int:client_id>/orders', ClientOrdersView.as_view(), name='client_orders'),
    path('clients/<int:client_id>/assets', ClientAssetsView.as_view(), name='client_assets'),
    path('clients/<int:client_id>/assets/create', AssetCreateView.as_view(), name='client_create_asset'), 
    #  zita added 
    path('clients/<int:client_id>/order/create', OrderAddView.as_view(), name='client_create_order'), 
    
    path('clients/<int:client_id>/billing', ClientBillingView.as_view(), name='client_billing'),
    path('clients/<int:client_id>/videos', ClientVideosView.as_view(), name='client_videos'),

    path('add_client_global_asset', addAjaxAssetToClient, name='add_client_global_asset'),   #ajax
    
    path('companies/', CompanyIndexView.as_view(), name='companies'),
    path('companies/<int:company_id>/', CompanyPageView.as_view(), name='company_detail'),
    path('companies/<int:company_id>/orders', CompanyOrderView.as_view(), name='company_orders'),
    path('companies/<int:company_id>/assets', CompanyAssetsView.as_view(), name='company_assets'),
    path('companies/<int:company_id>/assets/create', AssetCreateView.as_view(),name='company_create_asset'),
    
    path('add_company_global_asset', addAjaxAssetToCompany, name='add_company_global_asset'),   #ajax
    
    
    path('companies/<int:company_id>/billing', CompanyBillingView.as_view(), name='company_billing'),
    
    path('products/', ProductIndexView.as_view(), name='products'),
    path('products/<int:product_id>/', ProductPageView.as_view(), name='product_detail'),
    path('productbase/<int:productbase_id>/', ProductBasePageView.as_view(), name='productbase_detail'),
    #path('productbase/<int:productbase_id>/add/asset', AssetAddView.as_view(), name='productbase_add_asset'),

    path('check_status_product', checkAjaxStatusProduct, name='check_status_product'),   #ajax
    path('save_product_text_info', saveAjaxProductTextInfo, name='save_product_text_info'),   #ajax
    path('delete_product_text_info', deleteAjaxProductTextInfo, name='delete_product_text_info'),   #ajax
    path('change_product_base_intake', changeProductBaseIntake, name='change_product_base_intake'),   #ajax
    path('delete_product_image_info', deleteAjaxProductImageInfo, name='delete_product_image_info'),   #ajax
    path('ajax_all_sub_product', ajaxSubProductInfo, name='ajax_all_sub_product'),   #ajax
    path('ajax_product_image_sub_update', ajaxSubProductImageTextUpdate, name='ajax_product_image_sub_update'),   #ajax
    path('ajax_product_image_sub_delete', ajaxSubProductImageTextDelete, name='ajax_product_image_sub_delete'),   #ajax
    path('product_image_data_add', ajaxProductImageDataAdd, name='product_image_data_add'),
    path('product_image_text_add', ajaxProductImageTextAdd, name='product_image_text_add'),
    path('sub_product_order', ajaxSubProductOrder, name='sub_product_order'),
    
    path('projects/', ProjectIndexView.as_view(), name='projects'),
    path('project/add/', ProjectCreateView.as_view(), name='project_add'),
    path('project/create', ProjectCreateView.as_view(), name='project_create'),
    path('projects/<int:project_id>/', ProjectDashboardView.as_view(), name='project_dashboard'),
    path('projects/<int:project_id>/detail', ProjectPageView.as_view(), name='project_detail'),
    path('projects/<int:project_id>/intakes', ProjectIntakesView.as_view(), name='project_intakes'),
    path('projects/<int:project_id>/videos', ProjectVideosView.as_view(), name='project_videos'),
    path('projects/<int:project_id>/shoots', ProjectShootsView.as_view(), name='project_shoots'),
    path('projects/get-select-project-video-ajax', getAjaxSelectProjectVideo, name='get-select-project-video-ajax'),  # ajax
    path('projects/get-select-video-ajax', getAjaxSelectVideo, name='get-select-video-ajax'), #ajax
    path('projects/save-select-project-video-ajax', saveAjaxSelectProjectVideo, name='save-select-project-video-ajax'),  # ajax
    path('projects/<int:project_id>/billing', ProjectBillingView.as_view(), name='project_billing'),
    path('projects/<int:project_id>/tasks/', ProjectTaskStatusView.as_view(), name='project_tasks'),

    path('projectvideo/<int:projectvideo_id>/', ProjectvideoPageView.as_view(), name='projectvideo'),

    path('change-status-project/', changeAjaxStatusProject, name='change_status_project'),  #ajax
    path('projects/delete-project-video', deleteProjectVideo, name='delete-project-video'), #ajax
    path('project/get-edit-pojectvideo-ajax/', getAjaxEditProjectVideo, name='get-edit-pojectvideo-ajax'), #ajax
    path('project/load-project-videos-ajax/', loadAjaxProjectVideos, name='load-project-videos-ajax'), #ajax

    path('project/get-add-video-template/', getAddVideoTemplate, name='get-add-video-template'), #ajax
    path('project/delete-video-ajax/', deleteAjaxVideo, name='delete-video-ajax'), #ajax
    path('project/save-project-ajax/', saveAjaxProject, name='save-project-ajax'), #ajax
    path('project/save-projectvideo-ajax/', saveAjaxProjectVideo, name='save-projectvideo-ajax'), #ajax
    path('project/delete-projectvideo-ajax/', deleteAjaxProjectVideo, name='delete-projectvideo-ajax'), #ajax
    path('project/save-project-lineitem-ajax/', saveAjaxProjectLineItem, name='save-project-lineitem-ajax'), #ajax 
    path('project/delete-projectlineitem-ajax/', deleteAjaxProjectLineItem, name='delete-projectlineitem-ajax'), #ajax
    path('project/save-project-shoot-ajax/', saveAjaxProjectShoot, name='save-project-shoot-ajax'), #ajax
    path('project/delete-projectshoot-ajax/', deleteAjaxProjectShoot, name='delete-projectshoot-ajax'), #ajax
    path('videos/consolidate-project-videos-ajax', consolidateAjaxProjectVideos, name='consolidate-project-videos-ajax'), #ajax
    path('videos/remove-linked-project-video-ajax', removeAjaxLinkedProjectVideo, name='remove-linked-project-video-ajax'),  # ajax
    path('project/get-add-crew-template/', getAddCrewTemplate, name='get-add-crew-template'), #ajax
    path('project/save-shootcrew-ajax/', saveAjaxShootCrew, name='save-shootcrew-ajax'), #ajax
    path('project/delete-shootcrew-ajax/', deleteAjaxShootCrew, name='delete-shootcrew-ajax'), #ajax
    path('project/get-add-camera-template/', getAddCameraTemplate, name='get-add-camera-template'), #ajax
    path('project/save-shootcamera-ajax/', saveAjaxShootCamera, name='save-shootcamera-ajax'), #ajax
    path('project/delete-shootcamera-ajax/', deleteAjaxShootCamera, name='delete-shootcamera-ajax'), #ajax


    path('videos/', VideoIndexView.as_view(), name='videos'),
    path('videos/<int:video_id>/', VideoPageView.as_view(), name='video_detail'),
    
    path('notyet/', NotYetView.as_view(), name='not_yet'),
    
    path('tasks/', TaskIndexView.as_view(), name='tasks'),
    path('tasks/<int:task_id>/', TaskPageView.as_view(), name='task_detail'),
    path('tasks/edit/<int:task_id>/', TaskEditPageView.as_view(), name='task_edit'),
    path('mytasks/', MyTaskIndexView.as_view(), name='mytasks'),
    path('mytasks/status/<str:status>/', MyTaskStatusView.as_view(), name='mytasks_by_status'),
    path('tasks/add', TaskAddView.as_view(), name='add_task'),
    path('projects/<int:project_id>/tasks/add', TaskAddView.as_view(), name='add_project_task'),
    path('projects/<int:project_id>/tasks/status/<str:status>/', ProjectTaskStatusView.as_view(), name='project_tasks_by_status'),
    path('tasks/status/<str:status>/', TaskStatusView.as_view(), name='tasks_by_status'),
    path('tasks/change-edit-task', changeAjaxTask, name='change-edit-task'), #ajax
    path('tasks/update-runtime-task', updateRuntimeAjaxTask, name='update-runtime-task'), #ajax

    path('tasks/update-complete-task', updateCompleteAjaxTask, name='update-complete-task'), #ajax

    path('tasks/get-project-managers', getProjectManagerAjax, name='get-project-managers'), #ajax
    path('tasks/get-preset-task', getPresetTaskAjax, name='get-preset-task'), #ajax
    path('tasks/create-task', createAjaxTask, name='create-task'), #ajax
    path('tasks/create-preset-task', createAjaxPresetTask, name='create-preset-task'), #ajax
    path('tasks/update-preset-task', updateAjaxPresetTask, name='update-preset-task'),  # ajax


    path('delivery/', DeliveryOverview.as_view(), name='proto_delivery_api'),
    
    path('settings/', FormikaroSettings.as_view(), name='settings'),
    path('log/', FormikaroLogViewer.as_view(), name='log_viewer'),

    #CSV import
    #path('admin/', admin.site.urls),
    path('upload-csv/', company_csv_import, name="company_csv_import"),
    path('import-product/', product_csv_import, name="product_csv_import"),

    #Notifications

    
]


