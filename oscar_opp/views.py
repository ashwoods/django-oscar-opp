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
CheckoutSessionData = get_class(
    'checkout.utils', 'CheckoutSessionData')
# ShippingAddress = get_model('order', 'ShippingAddress')
# Country = get_model('address', 'Country')
Basket = get_model('basket', 'Basket')
# Repository = get_class('shipping.repository', 'Repository')
Selector = get_class('partner.strategy', 'Selector')
Source = get_model('payment', 'Source')
SourceType = get_model('payment', 'SourceType')
OrderTotalCalculator = get_class(
    'checkout.calculators', 'OrderTotalCalculator')
try:
    Applicator = get_class('offer.applicator', 'Applicator')
except ModuleNotFoundError:
    # fallback for django-oscar<=1.1
    Applicator = get_class('offer.utils', 'Applicator')

logger = logging.getLogger('opp.copy_and_pay')


class PaymentDetailsView(views.PaymentDetailsView):

    preview = True
    template_name = 'oscar_opp/payment_details.html'
    template_name_preview = 'oscar_opp/preview.html'

    def dispatch(self, request, *args, **kwargs):
        checkout_id = request.GET.get('id')
        order_number = request.GET.get('order')
        if checkout_id and order_number:
            # skip all checkout paths and continue handling payment
            return self.handle_payment(request, order_number, checkout_id)
        else:
            return super(PaymentDetailsView, self).dispatch(request, *args, **kwargs)

    def prepare(self):
        """
        Prepare a basket for order placement
        Using OPP - Copy and Pay some of the logic has to happen before OPP
        form generation, as the form is processed on the 3rd party and then
        redirects back, so we have to freeze to freeze the basket here.

        * Generate an order number
        * Freeze the basket so it cannot be modified any more (important when
           redirecting the user to another site for payment as it prevents the
           basket being manipulated during the payment process).
        * Prepare checkout form.

        """
        # We generate the order number first as this will be used
        # in payment requests (ie before the order model has been
        # created).  We also save it in the session for multi-stage
        # checkouts (eg where we redirect to a 3rd party site and place
        # the order on a different request).
        basket = self.request.basket
        order_number = self.generate_order_number(basket)

        self.checkout_session.set_order_number(order_number)
        logger.info("Order #%s: beginning submission process for basket #%d",
                    order_number, basket.id)

        # Freeze the basket so it cannot be manipulated while the customer is
        # completing payment on a 3rd party site.  Also, store a reference to
        # the basket in the session so that we know which basket to thaw if we
        # get an unsuccessful payment response when redirecting to a 3rd party
        # site.
        self.freeze_basket(basket)
        self.checkout_session.set_submitted_basket(basket)
        facade = Facade()
        facade.prepare_checkout(
            basket.total_incl_tax,
            basket.currency,
            order_number,
        )
        callback = "%s?order=%s" % (
            self.request.build_absolute_uri(reverse('checkout:preview')),
            order_number,
        )
        form = facade.get_form(
            callback=callback,
            locale='de',
        )
        return form

    def get_context_data(self, **kwargs):
        ctx = super(PaymentDetailsView, self).get_context_data(**kwargs)
        ctx['form'] = self.prepare()
        return ctx

    def handle_payment(self, request, order_number, checkout_id):

        self.checkout_session = CheckoutSessionData(request)
        basket = self.load_frozen_basket(
            basket_id=self.checkout_session.get_submitted_basket_id()
        )
        facade = Facade(checkout_id=checkout_id)
        status = facade.get_payment_status()

        #if status == '200':
        # Request was successful - record the "payment source".  As this
        # request was a 'pre-auth', we set the 'amount_allocated' - if we had
        # performed an 'auth' request, then we would set 'amount_debited'.
        source_type, _ = SourceType.objects.get_or_create(name='opp')
        source = source_type.sources.model(
             source_type=source_type,
             currency=facade.transaction.currency,
             amount_debited=facade.transaction.amount,
             reference=checkout_id)
        self.add_payment_source(source)
        # # Also record payment event
        self.add_payment_event(
            'payment',
            facade.transaction.amount,
            checkout_id)

        submission = self.build_submission(basket=basket)
        submission['site'] = request.site
        del submission['order_kwargs']
        del submission['payment_kwargs']
        return self.handle_order_placement(
            order_number=order_number,
            **submission)

    def load_frozen_basket(self, basket_id):
        # Lookup the frozen basket that this txn corresponds to
        try:
            basket = Basket.objects.get(id=basket_id, status=Basket.FROZEN)
        except Basket.DoesNotExist:
            return None

        # Assign strategy to basket instance
        if Selector:
            basket.strategy = Selector().strategy(self.request)

        # Re-apply any offers
        Applicator().apply(request=self.request, basket=basket)

        return basket
