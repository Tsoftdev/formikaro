from rest_framework import status
from rest_framework.generics import GenericAPIView
from rest_framework.mixins import CreateModelMixin, RetrieveModelMixin, UpdateModelMixin, DestroyModelMixin
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet

from .models import ProductImage, ProductImageText
from .serializers import ProductImageSerializer, ProductImageTextSerializer, ProductImageBulkUpdateSerializer


class ProductImageViewSet(CreateModelMixin,
                          RetrieveModelMixin,
                          UpdateModelMixin,
                          DestroyModelMixin,
                          GenericViewSet):
    model = ProductImage
    serializer_class = ProductImageSerializer
    queryset = model.objects.all()
    parser_classes = [MultiPartParser, FormParser]
    permission_classes = [AllowAny, ]


class ProductImageTextViewSet(CreateModelMixin,
                              RetrieveModelMixin,
                              UpdateModelMixin,
                              DestroyModelMixin,
                              GenericViewSet):
    """
      API to upload, edit and delete ProductImageTexts
      Example POST is shown below where product_image is the Foreign Key of the Product Image associated with the text
          {
              "title": "Video Preview",
              "desc_short": "Short Description Optional",
              "language": "Language Foreign Key e.g. 1 could represent Dutch"
              "product_image": "Product Image Foreign Key e.g. 3 could represent an image for Product FKKCARGIXWEN1080W"
          }
      Example Response
          {
              "id": 1,
              "title": "Video Preview",
              "desc_short": "Short Description Optional",
              "desc_long": "Long Description Optional",
              "default": false,
              "language": 1,
              "product_image": 2
          }
      """
    model = ProductImageText
    queryset = model.objects.all()
    serializer_class = ProductImageTextSerializer
    permission_classes = [AllowAny, ]


class ProductImageDisplayOrderBulkUpdateAPIView(GenericAPIView):
    """
    API endpoint to bulk update ProductImage display_order
    Example POST
        [
            {"id": 5, "display_order": 2},
            {"id": 6, "display_order": 1},
            {"id": 7, "display_order": 400}
        ]
    Example Response (200 OK)
    "3 Records updated"

    Example Error Response (400 BAD REQUEST)
    A Bad Request returns the errors in a list corresponding to the list of items sent for example in the below sample
    the first item was missing the `display_order` field
        [
            {
                "display_order": [
                    "This field is required."
                ]
            },
            {},
            {}
        ]
    """
    serializer_class = ProductImageBulkUpdateSerializer
    queryset = ProductImage.objects.all()
    permission_classes = [AllowAny, ]

    def post(self, request, *args, **kwargs):
        product_images_list = self.request.data
        product_image_list_serializer = self.serializer_class(data=product_images_list, many=True)
        if product_image_list_serializer.is_valid():
            ids = [item['id'] for item in product_images_list]
            product_image_objs = ProductImage.objects.filter(id__in=ids)
            for img_obj in product_image_objs:
                values_to_update = list(filter(lambda item: item['id'] == img_obj.id, product_images_list))
                img_obj.display_order = values_to_update[0]['display_order']
                img_obj.save()
            return Response(status=status.HTTP_200_OK, data=f"{len(product_image_objs)} Records updated")
        else:
            return Response(status=status.HTTP_400_BAD_REQUEST, data=product_image_list_serializer.errors)
