#django librarys
from django.core.management.base import BaseCommand
from django.core.exceptions import ObjectDoesNotExist
from datetime import datetime
from apps.FileCollector.models import File, Intake, Client, Company, Order, OrderProduct
from apps.ProductManager.models import Product, ProductBase, ProductTextModel, Language, Resolution

def check_assets(id=''):
    if not id:
        return False
    


class Command(BaseCommand):
    help = 'Checks if the assets of a Company really exist and or if there are maybe others'

    def add_arguments(self, parser):
        parser.add_argument('Company_ids', nargs='+', type=int)
   
        parser.add_argument(
            '--create',
            action='store_true',
            help='This creates the folder structure for the base',
        )
     def handle(self, **options):
        check_assets()
