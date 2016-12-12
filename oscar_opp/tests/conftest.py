import pytest

from oscar_opp.copyandpay.gateway import Gateway
from oscar_opp.copyandpay.facade import Facade

@pytest.fixture
def gateway():
    return Gateway(
        "https://test.oppwa.com/v1/",
        "8a8294174b7ecb28014b9699220015cc",
        "sy6KJsT8",
        "8a8294174b7ecb28014b9699220015ca"
    )


@pytest.fixture
def facade():
    return Facade()
