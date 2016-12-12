# -*- coding: utf-8 -*-
import pytest
from decimal import Decimal as D


@pytest.mark.django_db
def test_facade(facade):
    facade.prepare_checkout(D(10), 'EUR')
    facade.get_form(locale='en')
