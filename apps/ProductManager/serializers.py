from rest_framework import serializers
from rest_framework.fields import SerializerMethodField
from rest_framework.serializers import ModelSerializer

from .models import ProductImage, ProductImageText


class ProductImageTextSerializer(ModelSerializer):
    class Meta:
        model = ProductImageText
        fields = '__all__'


class ProductImageSerializer(ModelSerializer):
    product_image_texts = ProductImageTextSerializer(many=True, read_only=True)
    image_thumbnails = SerializerMethodField()
    
    class Meta:
        model = ProductImage
        fields = '__all__'

    @staticmethod
    def get_image_thumbnails(obj):
        thumbnails = obj.image.thumbnails.all()
        return [
            {'name': thumbnail.name, 'size': thumbnail.size, 'url': thumbnail.url}
            for thumbnail in thumbnails.values()
        ]


class ProductImageBulkUpdateSerializer(ModelSerializer):
    class Meta:
        model = ProductImage
        fields = ('id', 'display_order')
