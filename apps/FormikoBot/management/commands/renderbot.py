import logging

from django.core.management import BaseCommand

from apps.FormikoBot.renderbot_utils.utils import is_valid_order_product, renderbot

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    local_parser = None

    def add_arguments(self, parser):
        self.local_parser = parser
        parser.add_argument(
            '-op', '--op', help="Order Product ID to be processed"
        )

    def handle(self, *args, **options):
        order_product_id = options.get('op', None)
        if order_product_id:
            is_valid_order, errors = is_valid_order_product(order_product_id)
            if errors:
                print(errors)
                return
            renderbot(order_product_id)
