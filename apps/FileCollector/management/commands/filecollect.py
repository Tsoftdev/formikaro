#!/usr/bin/env python3

#
# Copyright (c) 2020 Ioanes Sinderman / Filmagio Cine Produktion
#
# Version 0.55
# Date: 15.2.2021
#
# Wetransfer Upload based on Leonardo Taccari
#
# checks an IMAP box for wetransfer links. on
# 
#    check no alterations will be performed
#
#    download will search through the mails extracting usable wetransferlinks
#    and downloads them in a given folder (email address = subfolder)
#
# Steps:
#   checks inbox for wetransfer link
#   checks to who the intake may belong (reference client/orders)
#   write them in the db
#  
#
# 
# This Collector checks an email account for wetransfer links and downloads them on 
# a local drive
# 
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED
# TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR
# PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS
# BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
# CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
# SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
# CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.
#
#




"""
Download/upload files via wetransfer.com

transferwee is a script/module to download/upload files via wetransfer.com.

It exposes `download' and `upload' subcommands, respectively used to download
files from a `we.tl' or `wetransfer.com/downloads' URLs and upload files that
will be shared via emails or link.
"""

from typing import List
import os
import re
import sys
import urllib.parse
import zlib
import email, imaplib
import webbrowser
import time
from email.header import decode_header
from email.parser import Parser
from datetime import datetime
import requests
import zipfile
from pathlib import Path
from bs4 import BeautifulSoup as BSHTML
from django.conf import settings
from django.db.models import Q
from decouple import config

#django librarys
from django.core.management.base import BaseCommand
from django.core.exceptions import ObjectDoesNotExist
from datetime import datetime
from apps.FileCollector.models import File, Intake, Client, Company, Order, OrderProduct, ORDER_PENDING_STATUS, ORDER_PRODUCT_PENDING_STATUS
from apps.ProductManager.models import Product, ProductBase, ProductTextModel, Language, Resolution
 

#wetransfer definitions
WETRANSFER_API_URL = 'https://wetransfer.com/api/v4/transfers'
WETRANSFER_DOWNLOAD_URL = WETRANSFER_API_URL + '/{transfer_id}/download'
WETRANSFER_UPLOAD_EMAIL_URL = WETRANSFER_API_URL + '/email'
WETRANSFER_VERIFY_URL = WETRANSFER_API_URL + '/{transfer_id}/verify'
WETRANSFER_UPLOAD_LINK_URL = WETRANSFER_API_URL + '/link'
WETRANSFER_FILES_URL = WETRANSFER_API_URL + '/{transfer_id}/files'
WETRANSFER_PART_PUT_URL = WETRANSFER_FILES_URL + '/{file_id}/part-put-url'
WETRANSFER_FINALIZE_MPP_URL = WETRANSFER_FILES_URL + '/{file_id}/finalize-mpp'
WETRANSFER_FINALIZE_URL = WETRANSFER_API_URL + '/{transfer_id}/finalize'
WETRANSFER_DEFAULT_CHUNK_SIZE = 5242880
WETRANSFER_EXPIRE_IN = 604800

EMAIL_SERVER = config('FO_EMAIL_SERVER')
EMAIL_ACCOUNT = config('FO_EMAIL_ACCOUNT')
EMAIL_PASSWORD = config('FO_EMAIL_PASSWORD')

#imap mailbox folders needed for this process. if they don't exists the script will create them
IMAP_PROCESSED_FOLDER = config('IMAP_PROCESSED_FOLDER')
IMAP_INVALID_FOLDER = config('IMAP_INVALID_FOLDER')
IMAP_FORWARDED_FOLDER = config('IMAP_FORWARDED_FOLDER')

#BOT_QUEUE_FILE = '/home/worker/Projects/HormigaBot/hb_queue.txt'

#path where all the downloads will be put
INTAKE_FOLDER = settings.INTAKE_FOLDER  # '/home/worker/Projects/mount/intake'
INTAKE_FOLDER_UNASSIGNED = settings.INTAKE_FOLDER_UNASSIGNED
INTAKE_FOLDER_ORDER = settings.INTAKE_FOLDER_ORDER


#if an email is forwarded to the intake account it will be downloaded here

#needed for the verification/extraction of email
regex = re.compile(("([a-z0-9!#$%&'*+\/=?^_`{|}~-]+(?:\.[a-z0-9!#$%&'*+\/=?^_`"
                    "{|}~-]+)*(@|\sat\s)(?:[a-z0-9](?:[a-z0-9-]*[a-z0-9])?(\.|"
                    "\sdot\s))+[a-z0-9](?:[a-z0-9-]*[a-z0-9])?)"))

def uprint(*objects, sep=' ', end='\n', file=sys.stdout):
    enc = file.encoding
    if enc == 'UTF-8':
        print(*objects, sep=sep, end=end, file=file)
    else:
        f = lambda obj: str(obj).encode(enc, errors='backslashreplace').decode(enc)
        print(*map(f, objects), sep=sep, end=end, file=file)
        

def get_text(msg):
    if msg.is_multipart():
        return get_text(msg.get_payload(0)) #added True argument
    else:
        return msg.get_payload(None, True)



### CODE BELOW 3D PARTY
def download_url(url: str) -> str:
    """Given a wetransfer.com download URL download return the downloadable URL.
    The URL should be of the form `https://we.tl/' or
    `https://wetransfer.com/downloads/'. If it is a short URL (i.e. `we.tl')
    the redirect is followed in order to retrieve the corresponding
    `wetransfer.com/downloads/' URL.
    The following type of URLs are supported:
     - `https://we.tl/<short_url_id>`:
        received via link upload, via email to the sender and printed by
        `upload` action
     - `https://wetransfer.com/<transfer_id>/<security_hash>`:
        directly not shared in any ways but the short URLs actually redirect to
        them
     - `https://wetransfer.com/<transfer_id>/<recipient_id>/<security_hash>`:
        received via email by recipients when the files are shared via email
        upload
    Return the download URL (AKA `direct_link') as a str or None if the URL
    could not be parsed.
    """
    # Follow the redirect if we have a short URL
    if url.startswith('https://we.tl/'):
        r = requests.head(url, allow_redirects=True)
        url = r.url

    recipient_id = None
    params = urllib.parse.urlparse(url).path.split('/')[2:]

    if len(params) == 2:
        transfer_id, security_hash = params
    elif len(params) == 3:
        transfer_id, recipient_id, security_hash = params
    else:
        return None

    j = {
        "intent": "entire_transfer",
        "security_hash": security_hash,
    }
    if recipient_id:
        j["recipient_id"] = recipient_id
    s = _prepare_session()
    r = s.post(WETRANSFER_DOWNLOAD_URL.format(transfer_id=transfer_id),
               json=j)

    j = r.json()
    return j.get('direct_link')


def _file_unquote(file: str) -> str:
    """Given a URL encoded file unquote it.
    All occurences of `\', `/' and `../' will be ignored to avoid possible
    directory traversals.
    """
    return urllib.parse.unquote(file).replace('../', '').replace('/', '').replace('\\', '')


def download(url: str, folder: str= 'unknown', filename: str = '') -> None:
    """Given a `we.tl/' or `wetransfer.com/downloads/' download it.
    First a direct link is retrieved (via download_url()), the filename can be
    provided via the optional `file' argument. If not provided the filename
    will be extracted to it and it will be fetched and stored on the current
    working directory.
    """
    dl_url = download_url(url)
    if not filename:
        filename = _file_unquote(urllib.parse.urlparse(dl_url).path.split('/')[-1])

    r = requests.get(dl_url, stream=True)
    
    # The part below in this function has been adapted to meet FORMIKARO requirements:
    # setting up folder
    # folderpath = INTAKE_FOLDER + INTAKE_SLASH + folder + INTAKE_SLASH;
    
    
    print("going to create path: ", folder)
    if not os.path.isdir(folder):
        os.makedirs(folder);
    
    file = Path(folder) / filename
    
    #if file already exists
    if os.path.isfile(file):
        now=datetime.now()
        filenameonly = os.path.basename(file)
        fileext =  os.path.splitext(file)[1]
        filename=filenameonly+'_'+now.strftime("%y%m%d%H%M%S")+fileext
        #file = INTAKE_FOLDER + INTAKE_SLASH + folder + INTAKE_SLASH + filename;
        file = Path(folder) / filename
        
    print("This will be filename: ", filename)
    print("This will be file: ", file)
    
    with open(file, 'wb') as f:
        for chunk in r.iter_content(chunk_size=1024):
            f.write(chunk)
            
    if os.path.isfile(file):
        #this is a very preliminary check just to see if the file has been created
        return file;
    else:
        return False;
            
            


def _file_name_and_size(file: str) -> dict:
    """Given a file, prepare the "name" and "size" dictionary.
    Return a dictionary with "name" and "size" keys.
    """
    filename = os.path.basename(file)
    filesize = os.path.getsize(file)

    return {
        "name": filename,
        "size": filesize
    }


def _prepare_session() -> requests.Session:
    """Prepare a wetransfer.com session.
    Return a requests session that will always pass the required headers
    and with cookies properly populated that can be used for wetransfer
    requests.
    """
    s = requests.Session()
    r = s.get('https://wetransfer.com/')
    m = re.search('name="csrf-token" content="([^"]+)"', r.text)
    s.headers.update({
        'x-csrf-token': m.group(1),
        'x-requested-with': 'XMLHttpRequest',
    })

    return s


def _prepare_email_upload(filenames: List[str], message: str,
                          sender: str, recipients: List[str],
                          session: requests.Session) -> str:
    """Given a list of filenames, message a sender and recipients prepare for
    the email upload.
    Return the parsed JSON response.
    """
    j = {
        "files": [_file_name_and_size(f) for f in filenames],
        "from": sender,
        "message": message,
        "recipients": recipients,
        "ui_language": "en",
    }

    r = session.post(WETRANSFER_UPLOAD_EMAIL_URL, json=j)
    return r.json()


def _verify_email_upload(transfer_id: str, session: requests.Session) -> str:
    """Given a transfer_id, read the code from standard input.
    Return the parsed JSON response.
    """
    code = input('Code:')

    j = {
        "code": code,
        "expire_in": WETRANSFER_EXPIRE_IN,
    }

    r = session.post(WETRANSFER_VERIFY_URL.format(transfer_id=transfer_id),
                     json=j)
    return r.json()


def _prepare_link_upload(filenames: List[str], message: str,
                         session: requests.Session) -> str:
    """Given a list of filenames and a message prepare for the link upload.
    Return the parsed JSON response.
    """
    j = {
        "files": [_file_name_and_size(f) for f in filenames],
        "message": message,
        "ui_language": "en",
    }

    r = session.post(WETRANSFER_UPLOAD_LINK_URL, json=j)
    return r.json()


def _prepare_file_upload(transfer_id: str, file: str,
                         session: requests.Session) -> str:
    """Given a transfer_id and file prepare it for the upload.
    Return the parsed JSON response.
    """
    j = _file_name_and_size(file)
    r = session.post(WETRANSFER_FILES_URL.format(transfer_id=transfer_id),
                     json=j)
    return r.json()


def _upload_chunks(transfer_id: str, file_id: str, file: str,
                   session: requests.Session,
                   default_chunk_size: int = WETRANSFER_DEFAULT_CHUNK_SIZE) -> str:
    """Given a transfer_id, file_id and file upload it.
    Return the parsed JSON response.
    """
    f = open(file, 'rb')

    chunk_number = 0
    while True:
        chunk = f.read(default_chunk_size)
        chunk_size = len(chunk)
        if chunk_size == 0:
            break
        chunk_number += 1

        j = {
            "chunk_crc": zlib.crc32(chunk),
            "chunk_number": chunk_number,
            "chunk_size": chunk_size,
            "retries": 0
        }

        r = session.post(
            WETRANSFER_PART_PUT_URL.format(transfer_id=transfer_id,
                                           file_id=file_id),
            json=j)
        url = r.json().get('url')
        requests.options(url,
                             headers={
                                 'Origin': 'https://wetransfer.com',
                                 'Access-Control-Request-Method': 'PUT',
                             })
        requests.put(url, data=chunk)

    j = {
        'chunk_count': chunk_number
    }
    r = session.put(
        WETRANSFER_FINALIZE_MPP_URL.format(transfer_id=transfer_id,
                                           file_id=file_id),
        json=j)

    return r.json()


def _finalize_upload(transfer_id: str, session: requests.Session) -> str:
    """Given a transfer_id finalize the upload.
    Return the parsed JSON response.
    """
    r = session.put(WETRANSFER_FINALIZE_URL.format(transfer_id=transfer_id))

    return r.json()


def upload(files: List[str], message: str = '', sender: str = None,
           recipients: List[str] = []) -> str:
    """Given a list of files upload them and return the corresponding URL.
    Also accepts optional parameters:
     - `message': message used as a description of the transfer
     - `sender': email address used to receive an ACK if the upload is
                 successfull. For every download by the recipients an email
                 will be also sent
     - `recipients': list of email addresses of recipients. When the upload
                     succeed every recipients will receive an email with a link
    If both sender and recipient parameters are passed the email upload will be
    used. Otherwise, the link upload will be used.
    Return the short URL of the transfer on success.
    """

    # Check that all files exists
    for f in files:
        if not os.path.exists(f):
            raise FileNotFoundError(f)

    # Check that there are no duplicates filenames
    # (despite possible different dirname())
    filenames = [os.path.basename(f) for f in files]
    if len(files) != len(set(filenames)):
        raise FileExistsError('Duplicate filenames')

    transfer_id = None
    s = _prepare_session()
    if sender and recipients:
        # email upload
        transfer_id = \
            _prepare_email_upload(files, message, sender, recipients, s)['id']
        _verify_email_upload(transfer_id, s)
    else:
        # link upload
        transfer_id = _prepare_link_upload(files, message, s)['id']

    for f in files:
        file_id = _prepare_file_upload(transfer_id, f, s)['id']
        _upload_chunks(transfer_id, file_id, f, s)

    return _finalize_upload(transfer_id, s)['shortened_url']




### CODE BELOW FO

def getDownloadLink(email_text):
    #email_text = email_text.decode("utf-8")
    
    #download_link = re.findall(r'(wetransfer.com/downloads\S+)', email_text)
    download_list = re.findall(r'((wetransfer.com\/downloads\/)([a-zA-Z0-9=])+\/([a-zA-Z0-9=])+\/([a-zA-Z0-9]){6})', email_text)
    #print("DL LIST ", download_list)
    if download_list:
        return str(download_list[0][0]);
    else:
        return False;
      
    #client_folder = re.findall(r'hat dir einige Dateien gesendet', email_text)
            
    #extract the 'Reply-To:' Email address from the mail body so we know how to name our folder
    #replyTo = re.findall('Reply-To: ([^<>@\s]+@[^<>\s]+)', raw_email.decode("utf-8"))
    #senderAddress = replyTo[0]
    
    #:return download_link;
#def write_bot_queue(file_list = []):
#    # w+ = FIFO a+ = LIFO
#    with open(BOT_QUEUE_FILE, 'w+') as f:
#        for item in file_list:
#            f.write("%s\n" % item)

#def write_file_to_bot_queue(file):
#    #w+ = FIFO a+ = LIFO
#    with open(BOT_QUEUE_FILE, 'a+') as f:
#        f.write("%s\n" % file)



#this is a very dirty solution to the decoding problem of the imap quoted printable
#but as we just need one tag to extract the order id this has to do it for now
def get_message_text(msg_str):
    if not msg_str: return ''
    
    msg_str = msg_str.replace('3D', '')
    msg_str = msg_str.replace('=0D', '')
    msg_str = msg_str.replace('\\r', '')
    msg_str = msg_str.replace('\\n', '')
      
    BS = BSHTML(msg_str, 'html.parser')

    email_order = BS.find_all(class_="message_content")
    if email_order:
        order_id = email_order[0].contents[0]
        if order_id:
            return order_id
        
    return ''

def processInbox(onlycheck: True):
    
    start_time = time.time()
    newFiles = []
    #flags for creating the necessary imap folders
    createIMAP_PROCESSED_FOLDER = True;
    createIMAP_INVALID_FOLDER = True;
    
    # connect to host using SSL
    imap = imaplib.IMAP4_SSL(EMAIL_SERVER)

    ## IMAP: https://www.devdungeon.com/content/read-and-send-email-python
    
    ## login to server
    imap.login(EMAIL_ACCOUNT, EMAIL_PASSWORD)
    
    status, messages = imap.select('Inbox')
    messages = int(messages[0])
    print(">total number of messages: ", messages)
    
    response_code, folders = imap.list('Inbox')
    #print(">[CHECK] if necessary mailboxes exists...");
    #print(">RC: ", response_code)  # OK
    #print('>Available folders(mailboxes) to select:')
    for folder_details_raw in folders:
        folder_details = folder_details_raw.decode().split()
        
        #check if we find the folders needed for further processing
        if (folder_details[-1].find(IMAP_PROCESSED_FOLDER) != -1):
            createIMAP_PROCESSED_FOLDER = False;
        if (folder_details[-1].find(IMAP_INVALID_FOLDER) != -1):
            createIMAP_INVALID_FOLDER = False;
            
        #print(f'- {folder_details[-1]}');
    
    if onlycheck == False:
        if(createIMAP_PROCESSED_FOLDER):
            print(">[ACTION] Didn't find IMAP_PROCESSED_FOLDER, will try to create folder: ", IMAP_PROCESSED_FOLDER)
            imap.select('INBOX')  # Default is `INBOX`
            response_code, response_details = imap.create('INBOX.'+IMAP_PROCESSED_FOLDER)
            print(response_code)  # `OK` on success or `NO` on failure
            print(response_details)  # Create completed/Mailbox already exists
    
        if(createIMAP_INVALID_FOLDER):
            print(">[ACTION] Didn't find IMAP_INVALID_FOLDER, will try to create folder: ", IMAP_INVALID_FOLDER)
            imap.select('INBOX')  # Default is `INBOX`
            response_code, response_details = imap.create('INBOX.'+IMAP_INVALID_FOLDER)
            print(response_code)  # `OK` on success or `NO` on failure
            print(response_details)  # Create completed/Mailbox already exists
    

    
    #imap.select('INBOX')  # Default is `INBOX`

    # Search for emails in the mailbox that was selected.
    # First, you need to search and get the message IDs.
    # Then you can fetch specific messages with the IDs.
    # Search filters are explained in the RFC at:
    # https://tools.ietf.org/html/rfc3501#section-6.4.4
    
    #We just look for unseen messages, as a seen message mean that another instance of 
    #the script is already working on it
    search_criteria = '(UNSEEN)' #'ALL'
    charset = None  # All
    respose_code, message_numbers_raw = imap.search(charset, search_criteria)
    #print(f'Search response: {respose_code}')  # e.g. OK
    #print(f'Message numbers: {message_numbers_raw}')  # e.g. ['1 2'] A list, with string of message IDs
    message_numbers = message_numbers_raw[0].split()
    
    #counter for emails processed
    num = 0
   
    #counter for downloads processed
    numDownload = 0
    #counter for expired download links
    numExpiredDownload = 0
    #counter for accomplished downloads
    numAccomplishedDownload = 0
    #counter for all files downloaded
    numFilesDownload = 0
    
    print(">[START] Message loop... with # messages ", message_numbers);
    # Fetch full message based on the message numbers obtained from search
    
    for message_number in message_numbers:
        
        
        #if we only check, we'll peek into the mailbox so we don't set the 'seen' flag. draw back: we won't get the whole message
        if onlycheck == True: 
            response_code, message_data = imap.fetch(message_number, '(BODY.PEEK[HEADER] FLAGS)')
        else:
            response_code, message_data = imap.fetch(message_number, '(RFC822)');
        
        if response_code != 'OK':
            print("ERROR getting message", message_number);

        
        else:
            
            parsed_email = email.message_from_bytes(message_data[0][1])
            order_id = ''
            shop_order_id = 0
            order_message = None
            message_text = str(get_message_text(str(message_data[0][1])))
            order_message = message_text
            if order_message:
                if order_message.isnumeric():
                    shop_order_id = int(order_message)
                    print("\tMSG #%s\tWe received an order id: [%s] " % (int(message_number), order_id))
                elif order_message:
                    print("\tMSG #%s\tWe didn't receive an id but possible a message: [%s] (which we ignore for now)" % (int(message_number), order_message))
            else:
                print("\tMSG #%s\tNo order id or message received" % int(message_number))
            
            
            #counter for emails processed
            num = num + 1
        
            #print(f'Fetch response for message {message_number}: {response_code}')
            
            #this strips the message content down to the bare minimum in order to extract the link we crave
            try:
                msg = get_text(parsed_email).decode("utf-8")
            except UnicodeError:
                msg = str(get_text(parsed_email))
            
            
            downloadLink = getDownloadLink(msg);

            #extract the 'Reply-To:' Email address from the mail body so we know how to name our folder
            replyTo = re.findall('Reply-To: ([^<>@\s]+@[^<>\s]+)', str(parsed_email))
            if replyTo:
                senderAddress = replyTo[0];
            else:
                senderAddress = IMAP_FORWARDED_FOLDER;
         
            #
            #DATABASE CHECKs
            #
            this_order = None
            #so here's the magic to link the intake to the order. 
            
            sorting_message = ''
            this_client = None
            #so here's the magic to link the intake to the order. 
            
            #First: Let's see if there is a order in the system matching this order_id
            try:
                this_client = Client.objects.filter(email=senderAddress).first()
            except:
                print("Didn't find any client matching the senderAddress")
            
            try:
                this_order = Order.objects.filter(shop_order_id=shop_order_id).first()
                if this_order:
                    print("Found an order through shop_order_id [%s] [%s]" % (shop_order_id, this_order))
                    sorting_message += 'Found an order through shop_order_id [%s] [%s]\n' % (shop_order_id, this_order)
            
                #if the order is not linked through shop_order_id...
            except:
                if not this_order and not this_client:
                    print("Didn't find any order matching shop_order_id [%s] or any client matching [%s] " % (shop_order_id, senderAddress))
                    sorting_message += 'Did not find any shop_order_id [' + str(shop_order_id) + '] or client matching [' + senderAddress + ']\n'

            if this_order:
                #if we have an order let's check if it corresponds with the senderAddress
                if this_order.client.email  == senderAddress:
                    print(">sender email matching with order client: %s - %s " % (this_order.client.email, senderAddress))
                    sorting_message += 'Found matching email to linked order [' + str(this_client) + '] ID:[' + str(this_order.id) + ']\n'
                    # LINK verified! so this_order is the correct one
                    
                
                #if the senderaddress mismatches the client we would assume through the shop_order_id,
                #we'll see if this client has orders open
                else:
                    print(">Sender email mismatching")
                    sorting_message += 'Sender email mismatching\n'
                    if this_client:
                        needs_intake = False
                        #this will iterate all open orders of this client checking the oldest with status PENDING that need an intake
                        open_orders = Order.objects.filter(Q(client=this_client) & Q(status=ORDER_PENDING_STATUS)).order_by('created') # -create_time would give the youngest
                        print("Looking for orders of client %s to match intake" % this_client)
                    
                        for order in open_orders:
                            needs_intake = False
                            print("\tOrder [%s]:\t%s" % (order.id, order.created))
                            for product in order.order_products.all():
                                print("\t\tOrderProduct %s\t%s\t%s" % (product, product.product.base.needs_intake, product.status))
                            
                                #if this product needs an intake we'll link it to the oldest one
                                if product.product.base.needs_intake and product.status == ORDER_PRODUCT_PENDING_STATUS:
                                    needs_intake = True        
                        
                            # this order needs an intake so let's link it
                            # check here if they need intake and the time in order to link them...
                            if needs_intake:
                                print("We will link this intake to order: %s " % order.id)
                                sorting_message += 'We found an OrderProduct that matches this intake: Order:%s OrderProduct:%s' % (order.id, product.id)
                                
                                # LINK verified! 
                                this_order = order
                                # let's get out of here
                                break
                                
                        if not needs_intake:
                            print("We didn't find any possible product that could use this intake")
                            sorting_message += 'We didn\'t find any possible product that could use this intake\n'
                        
            #this is the case if we don't get an order through the shop_order_id but we want to see if a client has open orders            
            else:
                if this_client:
                    print("No order found but we have a client: %s" % this_client)
                    sorting_message += 'Found no order but a client: %s\n' % this_client
                else:
                #here we are: having an order but no client to link it to...
                    print("No client present")
                    sorting_message += 'No client or order found\n'
            
      
            newIntake = Intake(sender=senderAddress,shop_order_id=shop_order_id, order=this_order, client=this_client, created=datetime.now())
            
            #we can only call write_log now as it's always saving the object and would create a new entry before we are ready
            newIntake.write_log(sorting_message, False) # we don't want the intake to save yet as we are not sure if this intake is valid
            
            #print(">Adding to db %s - %s " % (order_id, type(order_id)))
            #Make new Intake (not saved yet, we only do this once a link is found)
            
            #if a download link has been found we will now check and try to download...
            if downloadLink:
            
                if onlycheck == True:
                    print(">[CHECK ONLY] Going to download file now ", downloadLink)
                    print(">from: ", senderAddress)
                    #imap.store(message_number, '+FLAGS','(\Unseen)')
                else: 
                    print(">[ACTION] Going to download file now ", downloadLink)
                    print(">from: ", senderAddress)
                
                    #calling the wetransfer download function and passing the link as well as the folder name
                    start_time_download = time.time()
                    imap.store(message_number, '+FLAGS', '\Seen');
                
                    # check who's intake this may be:
                    newIntake.save() #now we can save 
                    designated_folder = newIntake.get_path()
        
                    print("Designated_folder: ", designated_folder )
                
                    print("DOWNLOADING NOW: \nfrom %s \nto %s" % (downloadLink, designated_folder) )
                    newFile = download(downloadLink, designated_folder)
                    if newFile:
            
                        #create a new intake in the database
                        
                        newIntake.save()
                        newIntakeId = newIntake.id
                        newIntake.write_log('Created. Wetransfer Message [%s]' % order_message)
                    
                        #so now let's have look what file(s) we got:
                        filename, file_extension = os.path.splitext(newFile)
                        count = 1
                        #if we got a zip, let's unpack it
                        if zipfile.is_zipfile(newFile):
                            print("We have a zip file...")
                            #extracting the files
                            #with zipfile.ZipFile(newFile, 'r') as zip_ref:
                            #    zip_ref.extractall(designated_folder)
                            with zipfile.ZipFile(newFile) as zip:
                                for zip_info in zip.infolist():
                                    if zip_info.filename[-1] == '/':
                                        continue
                                    zip_info.filename = os.path.basename(zip_info.filename)
                                    print("File [%s]: %s" % (count, zip_info.filename))        
                                    count=count+1
                                
                                    #this is the short path we are saving in the db  (excl. the intake drive)
                                    newFilePath =  Path(designated_folder) / zip_info.filename
                                
                                    #this is the path for extraction
                                    newAbsFilePath = Path(INTAKE_FOLDER) / designated_folder
                                
                                    print("File new path: ", newAbsFilePath)
                                
                                    #extract file
                                    zip.extract(zip_info, newAbsFilePath)
                                
                                    #prepare data for DB
                                    new_path = Path(newAbsFilePath) / zip_info.filename
                                    newSize = os.path.getsize(new_path)
                                    newFileType = Path(zip_info.filename).suffix
                                    newFileName = zip_info.filename
                                
                                    #create new File object
                                    newFile_in_DB = File(filename=newFileName, filepath=newAbsFilePath,filetype=newFileType, size=newSize, created=datetime.now(), intake_id=newIntakeId)
                                    #save in Database
                                    newFile_in_DB.save()
                                    newIntake.write_log('Added file (from zip) [%s] intake.id [%s]' % (newFileName, newIntakeId))
                                    #increase counter of downloaded files
                                    numFilesDownload = numFilesDownload +1
                        
                            print("Extraction complete...")
                            print("delete zip file")
                            os.remove(newFile);
                    
                        else:
                        #if it's any other file let's write this in the database
                            newSize = os.path.getsize(newFile)
                            newFileType = Path(newFile).suffix
                            newFileName = os.path.basename(newFile)
                                
                            newFile_in_DB = File(filename=newFileName, size=newSize, filepath=newFile,filetype=newFileType,  created=datetime.now(), intake_id=newIntakeId)
                            newFile_in_DB.save()
                            newIntake.write_log('Added file [%s] intake.id [%s]' % (newFileName, newIntakeId))
                    
                        print(">Successfully downloaded: ", newFile);
                        numAccomplishedDownload = numAccomplishedDownload + 1
                    #dowiloaded...
                    else:
                        print(">Download did not work")
                        numExpiredDownload = numExpiredDownload +1

                print(">Runtime of download --- %s seconds ---" % (time.time() - start_time))
                
                #MISSING: check if processed box exists
                
                #DEBUG (deactivated so we can test more often)
                imap.copy(message_number, 'INBOX.'+IMAP_PROCESSED_FOLDER)
                # Delete an email from inbox
                imap.store(message_number, '+FLAGS', '\Deleted')
                # Expunge after marking emails deleted
                
                numDownload = numDownload +1
            else:
                if onlycheck == True:
                    print(f'>Message {num} would have been marked as invalid | from {senderAddress} | dl {downloadLink}');
                else:
                    print(f'>Message {num} marked as invalid | from {senderAddress} | dl {downloadLink}');
                    #copying message in to invalid folder
                    response_code, response_details = imap.create('INBOX.'+IMAP_INVALID_FOLDER)
                    print(response_code)  # `OK` on success or `NO` on failure
                    imap.copy(message_number, 'INBOX.invalid')
                    # Delete an email from inbox
                    imap.store(message_number, '+FLAGS', '\Deleted');
                
   
    print("\tNumber of total processed files:\t", num) 
    print("\tNumber of total downloaded files:\t", numFilesDownload)
    print("\tNumber of found download links:\t\t", numDownload) 
    print("\tNumber of accomplished download:\t", numAccomplishedDownload) 
    print("\tNumber of expired downloads:\t\t", numExpiredDownload) 
    print("\tRuntime of Inbox --- %s seconds ---" % (time.time() - start_time))
    imap.expunge()
    imap.close()
    imap.logout()

    return ">End of Process";

class Command(BaseCommand):
     def handle(self, **options):
        #senderAddress='filmanto@gmail.com'
        #shop_order_id = 98
        #new_intake = Intake(sender=senderAddress);
        #designated_folder = new_intake.get_path()
        #print("Folder: %s [%s]" % (designated_folder, new_intake.client))
        
        #debug start

            
            
            
        #print("Sorting message: ", sorting_message)
                
        #debug end
        
        processInbox(False)
        
