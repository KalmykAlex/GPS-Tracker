import pytest
from tracker import get_gps_port


def test_port():
    port = get_gps_port('u-blox')
    assert port == '/dev/ttyACM0'

