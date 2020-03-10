import pytest
from mock import Mock
from tracker_oop import GPS, RFID
from mfrc522 import SimpleMFRC522


class TestGPS:

    def test_port(self):
        assert '/dev/tty' in GPS().get_gps_port('1546')
        with pytest.raises(TypeError):
            GPS().get_gps_port('1234')
            GPS().get_gps_port(1234)


class TestRFID:

    good_ids = [780870559455, 142189814135]
    wrong_ids = [123412341234, 836205736274]
    invalid_ids = [12341234123, '123412341234',
                   12341234.1234, [123412341234]]

    def __init__(self):
        self.rfid = RFID()

    def setup_method(self):
        print('setting up')
        self.rfid.shutdown.clear()

    def teardown_method(self):
        print('tearing down')
        self.rfid.shutdown.set()

    @pytest.fixture
    def mock_rfid_reader(self):
        return Mock(spec=SimpleMFRC522)

    def test_rfid_journey(self, mock_rfid_reder):
        for _id in self.good_ids:
            mock_rfid_reder.return_value = _id
            self.rfid.run()
            assert self.rfid.start_signal.is_set() is True
            assert self.rfid.stop_signal.is_set() is False
            assert self.rfid.ui_event_invalid_card.is_set() is False
            assert self.rfid.ui_event_wrong_card.is_set() is False

        for _id in self.wrong_ids + self.invalid_ids:
            mock_rfid_reder.return_value = _id
            self.rfid.run()
            assert self.rfid.start_signal.is_set() is False
            assert self.rfid.stop_signal.is_set() is False
            assert self.rfid.ui_event_invalid_card.is_set() is True
            assert self.rfid.ui_event_wrong_card.is_set() is False

