import pytest
from tracker_oop import GPS


def test_port():
    assert '/dev/tty' in GPS().get_gps_port('1546')
    with pytest.raises(TypeError):
        GPS().get_gps_port('1234')
        GPS().get_gps_port(1234)
