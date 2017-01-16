from __future__ import unicode_literals
from decimal import Decimal as D
import logging

from django.views.generic import RedirectView, View
from django.conf import settings
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django.contrib import messages
from django.contrib.auth.models import AnonymousUser
from django.core.urlresolvers import reverse
from django.http import HttpResponseRedirect
from django.utils.http import urlencode
from django.utils import six
from django.utils.translation import ugettext_lazy as _

import oscar
from oscar.apps.payment.exceptions import UnableToTakePayment
from oscar.core.exceptions import ModuleNotFoundError
from oscar.core.loading import get_class, get_model
from oscar.apps.shipping.methods import FixedPrice, NoShippingRequired
from oscar.apps.checkout import views, exceptions
from oscar.apps.payment.forms import BankcardForm
from oscar.apps.payment.models import SourceType
from oscar.apps.order.models import BillingAddress


from .copyandpay.facade import Facade


# # Load views dynamically
# PaymentDetailsView = get_class('checkout.views', 'PaymentDetailsView')
# CheckoutSessionMixin = get_class('checkout.session', 'CheckoutSessionMixin')
#
# ShippingAddress = get_model('order', 'ShippingAddress')
# Country = get_model('address', 'Country')
# Basket = get_model('basket', 'Basket')
# Repository = get_class('shipping.repository', 'Repository')
# Selector = get_class('partner.strategy', 'Selector')
Source = get_model('payment', 'Source')
SourceType = get_model('payment', 'SourceType')
# try:
#     Applicator = get_class('offer.applicator', 'Applicator')
# except ModuleNotFoundError:
#     # fallback for django-oscar<=1.1
#     Applicator = get_class('offer.utils', 'Applicator')
#
# logger = logging.getLogger('paypal.express')


class PaymentDetailsView(views.PaymentDetailsView):

    preview = True
    template_name = 'oscar_opp/payment_details.html'
    template_name_preview = 'oscar_opp/preview.html'

    def get_context_data(self, **kwargs):
        ctx = super(PaymentDetailsView, self).get_context_data(**kwargs)
        # Ensure newly instantiated instances of the bankcard and billing
        # address forms are passed to the template context (when they aren't
        # already specified).
        facade = Facade()
        facade.prepare_checkout(D(10), 'EUR')
        ctx['form'] = facade.get_form(locale='de')
        return ctx

    def handle_payment(self, order_number, total, **kwargs):

        facade = Facade()
        ref = facade.get_token(order_number, total.incl_tax)

        # Request was successful - record the "payment source".  As this
        # request was a 'pre-auth', we set the 'amount_allocated' - if we had
        # performed an 'auth' request, then we would set 'amount_debited'.

        source_type, _ = SourceType.objects.get_or_create(name='opp')
        source = source_type.sources.model(
            source_type=source_type,
            currency=total.currency,
            amount_debeted=total.incl_tax,
            reference=ref)
        self.add_payment_source(source)

        # Also record payment event
        self.add_payment_event(
            'pre-auth', total.incl_tax, reference=ref)
