#!/usr/bin/env python3

#
# Copyright (c) 2020 Ioanes Sinderman / Filmagio Cine Produktion
#
# just a handler command to call the fovo api (get_order_products)
#
# receives all pending shop orders from shop.filmagio.com
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

from pathlib import Path
import os
import re
import sys

from decouple import config

#django librarys
from django.core.management.base import BaseCommand
from django.core.exceptions import ObjectDoesNotExist
from datetime import datetime
from django.core.exceptions import ObjectDoesNotExist

from apps.FileCollector.tasks import get_shop_orders

from notifications.signals import notify


class Command(BaseCommand):
     def handle(self, **options):
          #notify.send(user, recipient=user, verb='you reached level 10')
        #get_shop_orders()
