from django.core.management.base import BaseCommand
from datetime import datetime
from apps.FileCollector.models import File, Intake, Client, Company, Order, OrderProduct
from apps.ProductManager.models import Product, ProductBase, ProductTextModel, Language, Resolution

import random
import string


def random_char(y):
    return ''.join(random.choice(string.ascii_letters) for x in range(y))


"""
Generates a sample productbase with all possible subsets

(After Effects)

"""

def gen_std_prod():

   
    productbase = ProductBase.objects.create(
        mode='AE',
        #name= random_char(5) + 'Standard Sample Product',
        name = 'Standard Sample Product',
    )
    
    producttext_en = ProductTextModel.objects.create (
        title = 'Standard Sample Product',
        desc_short = 'short description english',
        desc_long = 'long description english',
        language = Language.objects.get(abbreviation='en')
    )

    producttext_de = ProductTextModel.objects.create (
        title = 'Das ist ein Beispiel-Produkt',
        desc_short = 'Kurze Beschreibung auf Deutsch',
        desc_long = 'Lange Beschreibung auf Deutsch',
        language = Language.objects.get(abbreviation='de')
    )
    
    product1 = Product.objects.create(
        base = productbase,
		language = Language.objects.get(abbreviation='de'),
		resolution=Resolution.objects.get(name='720W'),
        variety='',
        version=1,
        runtime=20,
        price=29,
		preview="493443521",
        
    )
    
    product2 = Product.objects.create(
        base = productbase,
		language = Language.objects.get(abbreviation='de'),
		resolution=Resolution.objects.get(name='720H'),
        # product_name='Product 1',
        variety='',
        version=1,
        runtime=20,
        price=29,
		preview="493443521"
        
    )
    product3 = Product.objects.create(
        base = productbase,
		language = Language.objects.get(abbreviation='de'),
		resolution=Resolution.objects.get(name='720S'),
        # product_name='Product 1',
        variety='',
        version=1,
        runtime=20,
        price=29,
		preview="493443521"
        
    )
    product4 = Product.objects.create(
        base = productbase,
		language = Language.objects.get(abbreviation='de'),
		resolution=Resolution.objects.get(name='1080W'),
        # product_name='Product 1',
        variety='Blue',
        version=1,
        runtime=20,
		preview="493443521"
        
    )
    product5 = Product.objects.create(
        base = productbase,
		language = Language.objects.get(abbreviation='de'),
		resolution=Resolution.objects.get(name='1080H'),
        # product_name='Product 1',
        variety='Blue',
        version=1,
        runtime=20,
        price=29,
		preview="493443521"
        
    )
    product6 = Product.objects.create(
        base = productbase,
		language = Language.objects.get(abbreviation='de'),
		resolution=Resolution.objects.get(name='1080S'),
        # product_name='Product 1',
        variety='Blue',
        version=1,
        runtime=20,
        price=29,
		preview="493443521"
        
    )
    product7 = Product.objects.create(
        base = productbase,
		language = Language.objects.get(abbreviation='en'),
		resolution=Resolution.objects.get(name='720W'),
        # product_name='Product 1',
        variety='',
        version=1,
        runtime=20,
        price=29,
		preview="493443521"
        
    )
    product8 = Product.objects.create(
        base = productbase,
		language = Language.objects.get(abbreviation='en'),
		resolution=Resolution.objects.get(name='720H'),
        # product_name='Product 1',
        variety='',
        version=1,
        runtime=20,
		preview="493443521"
        
    )
    product9 = Product.objects.create(
        base = productbase,
		language = Language.objects.get(abbreviation='en'),
		resolution=Resolution.objects.get(name='720S'),
        # product_name='Product 1',
        variety='',
        version=1,
        runtime=20,
        price=29,
		preview="493443521"
        
    )
    product10 = Product.objects.create(
        base = productbase,
		language = Language.objects.get(abbreviation='en'),
		resolution=Resolution.objects.get(name='1080W'),
        # product_name='Product 1',
        variety='Gren',
        version=1,
        runtime=20,
        price=29,
		preview="493443521"
        
    )
    product11 = Product.objects.create(
        base = productbase,
		language = Language.objects.get(abbreviation='en'),
		resolution=Resolution.objects.get(name='1080H'),
        # product_name='Product 1',
        variety='Gren',
        version=1,
        price=29,
        preview="493443521"
        
    )
    product12 = Product.objects.create(
        base = productbase,
		language = Language.objects.get(abbreviation='en'),
		resolution=Resolution.objects.get(name='1080S'),
        # product_name='Product 1',
        variety='Gren',
        version=1,
        runtime=20,
        price=29,
		preview="493443521"
    )
    
    product1.get_new_fsin()
    product2.get_new_fsin()
    product3.get_new_fsin()
    product4.get_new_fsin()
    product5.get_new_fsin()
    product6.get_new_fsin()
    product7.get_new_fsin()
    product8.get_new_fsin()
    product9.get_new_fsin()
    product10.get_new_fsin()
    product11.get_new_fsin()
    product12.get_new_fsin()
    
    product1.product_texts.add(producttext_en, producttext_de)
    product2.product_texts.add(producttext_en, producttext_de)
    product3.product_texts.add(producttext_en, producttext_de)
    product4.product_texts.add(producttext_en, producttext_de)
    product5.product_texts.add(producttext_en, producttext_de)
    product6.product_texts.add(producttext_en, producttext_de)
    product7.product_texts.add(producttext_en, producttext_de)
    product8.product_texts.add(producttext_en, producttext_de)
    product9.product_texts.add(producttext_en, producttext_de)
    product10.product_texts.add(producttext_en, producttext_de)
    product11.product_texts.add(producttext_en, producttext_de)
    product12.product_texts.add(producttext_en, producttext_de)

        
class Command(BaseCommand):
    def handle(self, **options):
        gen_std_prod()
