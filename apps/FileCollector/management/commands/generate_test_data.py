from django.core.management.base import BaseCommand
from datetime import datetime
from apps.FileCollector.models import File, Intake, Client, Company, Order, OrderProduct
from apps.ProductManager.models import Product, ProductBase, ProductTextModel, Language, Resolution

import random
import string


def random_char(y):
    return ''.join(random.choice(string.ascii_letters) for x in range(y))


fileExt = ['.txt', '.pdf', '.mp4', '.wav', '.png', '.jpg']

FAKE_COMPANY = 'Fake 2 Inc.'

def generate_test_data():

    #set defaults if they are not alreay established
    # Language (de, en)
    if not Language.objects.filter(abbreviation='en'):
        Language.objects.create(abbreviation='en', name='English')
    if not Language.objects.filter(abbreviation='de'):
        Language.objects.create(abbreviation='de', name='Deutsch')
    
	# Resolutions (create the default ones)
    if not Resolution.objects.filter(name='720W'):
        Resolution.objects.create(name='720W', width=1280, height=720, description='1280x720 HD Widescreen')
    
    if not Resolution.objects.filter(name='720H'):
        Resolution.objects.create(name='720H', width=720, height=1280, description='720x1280 HD Portrait')

    if not Resolution.objects.filter(name='720S'):
        Resolution.objects.create(name='720S', width=720, height=720, description='720x1280 HD Square')
 
    if not Resolution.objects.filter(name='1080W'):
        Resolution.objects.create(name='1080W', width=1920, height=1080, description='1920x1080 FullHD Widescreen')
    
    if not Resolution.objects.filter(name='1080H'):
        Resolution.objects.create(name='1080H', width=1080, height=1920, description='1080x1920 FullHD Portrait')

    if not Resolution.objects.filter(name='1080S'):
        Resolution.objects.create(name='1080S', width=1080, height=720, description='1080x1080 FullHD Square')

	# Create a test company
    company = Company.objects.filter(name=FAKE_COMPANY).first()
    if not company:
        company = Company.objects.create(name=FAKE_COMPANY, street='Fakestreet',zip_code='314159', place='Faketown', country='Fakeland', description='this is a fake company, who would have guessed' )

	# ...and two clients belonging to the same company
    client1 = Client.objects.create(company=company, firstname='Bob', lastname='Bobsen', email='bob@fake.com', description='Bob is a fake employee at a fake company')
    client2 = Client.objects.create(company=company, firstname='Alice', lastname='Alison', email='alice@fake.com', description='Alice is a fake employee at a fake company')
	
	# This is the FSIN base the projects we are going to create depend on 
    baseFsin = 'FK' + random_char(8).upper()
	
    productbase = ProductBase.objects.create(
        fsin_base=baseFsin,
        mode='AE',
        name='Fake Test Product',
    )
    """
    producttext_en = ProductTextModel.objects.create (
        title = 'Test Product',
        desc_short = 'short description english',
        desc_long = 'long description english',
        language = Language.objects.get(abbreviation='en')
    )

    producttext_de = ProductTextModel.objects.create (
        title = 'Test Produkt',
        desc_short = 'kurze Beschreibung auf Deutsch',
        desc_long = 'lange Beschreibung auf Deutsch',
        language = Language.objects.get(abbreviation='de')
    )
    """
    product1 = Product.objects.create(
        fsin=baseFsin+'DE11080W',
        base = productbase,
		language = Language.objects.get(abbreviation='de'),
		resolution=Resolution.objects.get(name='720W'),
        # product_name='Product 1',
        variety='DE',
        version=1,
        runtime=60,
		vimeo_id="493443521"
        
    )
    #product1.product_texts.add(producttext_en, producttext_de)
    
    product2 = Product.objects.create(
        fsin=baseFsin+'EN1080W',
        base = productbase,
		language = Language.objects.get(abbreviation='en'),
		resolution=Resolution.objects.get(name='720W'),
        # product_name='Product 2',
        variety='EN',
        version=1,
        runtime=250,
		vimeo_id="493443521",
        
    )
    #product2.product_texts.add(producttext_en, producttext_de)
    
    # Generate Order and Order Products
    order1 = Order.objects.create(client=client1, status='ACTIVE')
    order2 = Order.objects.create(client=client2, status='COMPLETE')

    OrderProduct.objects.create(order=order1, product=product1)
    OrderProduct.objects.create(order=order1, product=product2)
    OrderProduct.objects.create(order=order2, product=product2)
    OrderProduct.objects.create(order=order2, product=product1)

    for i in range(100):
        newSender = random_char(10) + "@gmail.com"
        intake_order = order1 if i % 2 == 0 else order2
        newIntake = Intake(sender=newSender, created=datetime.now(), order=intake_order)
        newIntake.save()
        newIntakeId = newIntake.id
        r = list(range(10))
        random.shuffle(r)
        for i in r:
            newSize = random.randint(10, 150)
            newFileName = random_char(15) + random.choice(fileExt)
            newFile = File(filename=newFileName, size=newSize, created=datetime.now(), intake_id=newIntakeId)
            newFile.save()

    return newIntake


class Command(BaseCommand):
    def handle(self, **options):
        generate_test_data()
