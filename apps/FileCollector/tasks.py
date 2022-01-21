import json
import logging

import requests
from django.conf import settings

from celery import shared_task
from django.core.management import call_command
from django.db import transaction, DatabaseError

from .models import Order, Client, Company, OrderProduct
from apps.ProductManager.models import Product, Resolution
from apps.FormikoBot.models import Asset, AssetType

from django.utils.timezone import make_aware
from django.utils import dateformat, formats, timezone
import pytz
import datetime

logger = logging.getLogger(__name__)


@shared_task(name='apps.FileCollector.tasks.call_doorman')
def call_doorman():
    return call_command('doorman')


@shared_task(name='apps.FileCollector.tasks.call_filecollector')
def call_filecollector():
    return call_command('filecollect')


@shared_task(name='apps.FormikoBot.tasks.call_assembler')
def call_assembler():
    return call_command('assembler', '--prepare')

# this function prepares the json received from the shop and returns a custom_json 
# in the format ASSET_# : VALUE
def processShopJSON(shop_json):
    if not shop_json:
        return False

    this_json = {}
    # raw_json = str(shop_json)
    # raw_json = raw_json.replace("\'", "\"")
    # raw_json = raw_json.replace("null", "\"null\"") # this is a hack! the api should deliver json conform values instead
    # raw_json = raw_json.replace("None", "\"None\"")

    try:
        this_jsons = shop_json  # json.loads(raw_json)
        custom_json = {}
        k = 0

        for i in range(len(this_jsons)):
            label = this_jsons[i]['label'].upper()

            if label.find('RESOLUTION') == -1 and label.find('AUFLÖSUNG') == -1 and label.find('MUSIC') == -1 and label.find('MUSIK') == -1:
                key = "TEXT_" + str(k + 1)
                custom_json[key] = this_jsons[i]['value']
                k = k + 1
    except:
        return False

    return custom_json


# The FOVO-API core
# It collects orders from shop.filmagio.com and write them in the database
# For each order we generate multiple OrderProducts. The FSIN(SKU) is either supplied
# or - if the resolution is given as an extra parameter - assembled into a valid FSIN
# there are not many checks however if the resolution is unvalid or the labled incorrectly
# it is ignored an the product is not found
@shared_task(name='apps.FileCollector.tasks.get_shop_orders')
def get_shop_orders():
    try:
        logger.info('Authenticating to orders API')
        auth_data = {'UserName': settings.ORDERS_API_USER, 'Password': settings.ORDERS_API_PASSWORD}
        headers = {
            'accept': 'application/json',
            'content-type': 'application/json'
        }
        auth_response = requests.post(settings.SHOP_ORDERS_AUTH_API, json=auth_data, headers=headers)
        bearer_token = json.loads(auth_response.text).get('token')
        headers.update({'authorization': 'Bearer {}'.format(bearer_token)})
        logger.info('Getting orders from the shop')
        response = requests.get(settings.SHOP_PENDING_ORDERS_API, headers=headers)
        orders = json.loads(response.text)

        # get all resolutions for cross referencing
        resolutions = Resolution.objects.all()

        for order in orders:
            try:
                order_was_processed_before = Order.objects.filter(
                    shop_order_id=order['orderId'], shop_unique_token=order['guid']
                ).exists()
                if order_was_processed_before:
                    # skip order and go to the next one
                    continue
                logger.info('Processing Order GUID {}'.format(order.get('guid', 'No GUID SET')))

                with transaction.atomic():
                    customer_data = order['customer']
                    customer_billing_details = customer_data['billingAddress']
                    company_name = customer_billing_details.get('company')
                    company_name = company_name if company_name else 'No Company Name Supplied'
                    clientQueryset = Client.objects.filter(email=customer_data['userEmail'])
                    if not clientQueryset:
                        address2 = customer_billing_details['address2']
                        default_company_data = {
                            'street': '{add1}{add2}'.format(
                                add1=customer_billing_details['address1'], add2=address2 if address2 else '',
                            ),
                            'place': customer_billing_details['city'],
                            'zip_code': customer_billing_details['zipPostalCode'],
                            'country': customer_billing_details['country'],
                            'email': customer_billing_details['email'],
                            'phone_number': customer_billing_details['phone']
                        }
                        client_company, created = Company.objects.get_or_create(
                            name=company_name, defaults=default_company_data
                        )
                        client_name = customer_data.get('userFirstname', None)
                        client = Client.objects.create(
                            email=customer_data['userEmail'], company=client_company,
                            shop_username=customer_data.get('userName', 'No UserName Supplied'),
                            firstname=client_name if client_name else 'First Name Not Supplied',
                            lastname=customer_data['userLastname'], shop_customer_id=customer_data['customerId']
                        )
                    else:
                        client = clientQueryset.first()
                        client.shop_username = customer_data['userName']
                        client.shop_customer_id = customer_data['customerId']
                        client.save()

                    # a little hack to adapt the timestamp to include the timezone (as we are in the same that's no problem for now)
                    placed_time = order['orderedOn'] + '+00:00'
                    formikaro_database_order = Order.objects.create(
                        shop_order_id=order['orderId'], shop_unique_token=order['guid'], client=client,
                        billing_address=customer_billing_details, placed=placed_time,
                        payment_reference_number=order['paymentRefNum']
                    )
                    formikaro_database_order.write_log(message='Received via API')
                    order_items = order['orderItems']

                    for item in order_items:
                        if item['orderItemId']:
                            orderItemId =  item['orderItemId']
                        else:
                            orderItemId = 0

                        item_resolution = ''
                        item_music_asset = ''
                        # here we need to check if the fsin has to be assembled from the given variations
                        # if we get a resolution we assume it's part of the fsin
                        # we assume that the resolution is in the first 3 attributes that have been provided
                        if item['orderItemAttributes']:
                            for i in range(len(item['orderItemAttributes'])):
                                label = item['orderItemAttributes'][i]['label'].upper()
                                if label.find('RESOLUTION') != -1 or label.find('AUFLÖSUNG') != -1:
                                    item_resolution = item['orderItemAttributes'][i]['value']
                                    # print("\nFound a Resolution: [%s] [%s]" % (item['orderItemAttributes'][i]['value'], item['orderItemAttributes']))
                                elif label.find('MUSIC') != -1 or label.find('MUSIK') != -1:
                                    item_music_asset = item['orderItemAttributes'][i]['value']
                                    # print("\nFound a Resolution: [%s] [%s]" % (item['orderItemAttributes'][i]['value'], item['orderItemAttributes']))

                        # if a resolution is given..
                        if item_resolution:
                            # let's first check if there isn't already one resolution in this fsin (there can be only one)
                            # iE so we don't end up with something like THISFSIN1080W1080W
                            # if item['sku'].find("1080W") != -1:
                            resolutionExists = False

                            for resolution in resolutions:

                                if item['sku'].find(resolution.name) != -1:
                                    #print("found Resolution: %s %s %s" % (item['sku'], resolution.name, item['sku'].find(resolution.name)))
                                    resolutionExists = True
                                    break;

                            if resolutionExists:
                                logger.error(
                                    'Resolution already in FSIN, so no assembly taking place [%s]' % item['sku'].find(
                                        item_resolution))
                                item_fsin = item['sku']
                            else:
                                item_fsin = item['sku'] + item_resolution
                                logger.info('ASSEMBLED FSIN: [%s]' % item_fsin)

                        else:
                            item_fsin = item['sku']

                        unitprice = float(item['unitPrice'])
                        discount = float(item['discount'])

                        item_product = Product.objects.get(fsin=item_fsin)
                        new_order_product = OrderProduct.objects.create(
                            order=formikaro_database_order, product=item_product, discount=discount,
                            unitprice=unitprice, orderItemId=orderItemId, json=item['orderItemAttributes'])

                        # here comes the AssetConverter
                        # it interprets the json from the shop and creates the assets accordingly
                        clean_json = {}
                        clean_json = processShopJSON(item['orderItemAttributes'])

                        # print("JSON: %s " % clean_json)
                        # print("CLIENT: %s" % formikaro_database_order.client)



                        # this is  a very simple interpretation of how assets are created from json
                        # at this point it only allows for TEXTs and doesn't perform _any_ checks at all
                        # the numbering is done according to the position in the json.
                        # First one is TEXT_1, second TEXT_2, ...
                        # Again: no checks are performed at all if the assets exist and if the content matches

                        text_asset = AssetType.objects.get(name='TEXT')
                        trigger_asset = AssetType.objects.get(name='TRIGGER')
                        # TRIGGER ASSETS
                        # here we write a music trigger asset
                        if item_music_asset:
                            trigger_value = item_music_asset.upper()
                            if trigger_value.find('ON') or trigger_value.find('AN'):
                                value = '1'
                            else:
                                value = '0'
                            new_asset = Asset.objects.create(name='MUSIC_TRIGGER', value=value, assettype=trigger_asset,
                                                             client_owner=formikaro_database_order.client)
                            # link newly created asset to order product
                            new_order_product.assets.add(new_asset.id)

                        if clean_json:
                            # TEXT ASSETS
                            for key, value in clean_json.items():
                                # value = clean_json[i]
                                # print("Asset #%s\t%s\t%s" % (i, key, value))
                                new_asset = Asset.objects.create(name=key, value=value, assettype=text_asset,
                                                             client_owner=formikaro_database_order.client)
                                # link newly created asset to order product
                                new_order_product.assets.add(new_asset.id)


            except DatabaseError as ex:
                logger.error('Failed to Process Order {order_guid}. FSIN {fsin}. Error details: {ex}'.format(
                    order_guid=order['guid'], fsin=item['sku'], ex=ex
                ))
            except Exception as ex:
                logger.error('Failed to Process Order {order_guid}. FSIN {fsin}. Error details: {ex}'.format(
                    order_guid=order['guid'], fsin=item['sku'], ex=ex
                ))

    except ConnectionError as connection_exception:
        logger.error('Could not connect to Orders API. Network Error details: {ex}'.format(ex=connection_exception))
    except json.JSONDecodeError as json_exception:
        logger.error('Failed to decode data received from the API. Error details: {ex}'.format(ex=json_exception))
    except Exception as general_exception:
        logger.error('Error Fetching Shop Orders {}'.format(general_exception))
    logger.info('Getting orders from the shop, COMPLETE')
