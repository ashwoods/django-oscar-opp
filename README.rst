
Django oscar Open Payment Platform (OPP)
========================================

**WORK IN PROGRESS** This code is still alpha

A django oscar payment plugin modeled after `django-oscar-paypal` and `django-oscar-datacash`
that allows using any OPP compliant payment provider as a oscar payment backend.

Currently it only supports the `Copy and Pay` method that uses an OPP form and doesn't handle
any credit card information on the server.


Install
-------

Install into your python environment of choice using pip from
the parent folder:

    pip install django-oscar-opp


Settings
--------

OPP_USERID
OPP_ENTITYID
OPP_PASSWORD
OPP_BASEURL

Implement the view logic or configure your checkout app to point to the opp views:

Example::

    from oscar.apps.checkout import app
    from oscar_opp import views


    class CheckoutApplication(app.CheckoutApplication):
        # Replace the payment details view with our own
        payment_details_view = views.PaymentDetailsView

    application = CheckoutApplication()

