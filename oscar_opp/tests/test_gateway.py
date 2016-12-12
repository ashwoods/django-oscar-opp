# -*- coding: utf-8 -*-


def test_get_checkout_id(gateway):
    response = gateway.get_checkout_id(
        amount=20,
        currency='EUR',
        payment_type='DB'
    )
    assert response.status_code == 200
    assert response.json().get('id')


# def test_get_payment_status(checkout_id):
#     pass
