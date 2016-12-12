# -*- coding: utf-8 -*-

from decimal import Decimal as D

from django.conf import settings
from django.template.loader import get_template

from ..exceptions import OpenPaymentPlatformError
from ..models import Transaction
from .gateway import Gateway


class Facade(object):

    def __init__(self, checkout_id=None):
        self.gateway = Gateway(
            host=settings.OPP_BASEURL,
            auth_userid=settings.OPP_USERID,
            auth_entityid=settings.OPP_ENTITYID,
            auth_password=settings.OPP_PASSWORD
        )
        if checkout_id:
            self.transaction = Transaction.objects.get(
                correlation_id=checkout_id
            )
        else:
            self.transaction = None

    def prepare_checkout(self, amount, currency):
        if not self.transaction:
            response = self.gateway.get_checkout_id(
                amount=D(10),
                currency='EUR',
                payment_type='DB'
            )
            self.transaction = Transaction(
                amount=amount,
                currency=currency,
                raw_request=response.request.body,
                raw_response=response.content,
                response_time=response.elapsed.total_seconds() * 1000

            )
            if response.ok:
                self.transaction.checkout_id = response.json().get('id')
            else:
                # add error handling
                pass
            self.transaction.save()

        else:
            raise OpenPaymentPlatformError(
                "This instance is already linked to a Transaction"
            )

    def get_form(self, locale, address=None):
        ctx = {
            'checkout_id': self.transaction.checkout_id,
            'locale': locale,
            'address': address,
        }
        template = get_template('oscar_opp/form.html')
        return template.render(ctx)
