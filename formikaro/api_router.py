from django.urls import path
from rest_framework.routers import DefaultRouter

from apps.ProductManager.views import ProductImageViewSet, ProductImageTextViewSet,\
    ProductImageDisplayOrderBulkUpdateAPIView

router = DefaultRouter()
router.register(prefix='product-images', viewset=ProductImageViewSet, basename='product-images')
router.register(prefix='product-image-texts', viewset=ProductImageTextViewSet, basename='product-image-texts')

app_name = "api"
urlpatterns = router.urls
urlpatterns += [
    path("product-images-bulk-update/", ProductImageDisplayOrderBulkUpdateAPIView.as_view())
]
