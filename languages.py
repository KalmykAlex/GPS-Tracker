
# Message names format:
# msg_<s/d>_<short_description>
# s - static (not scrolling) (max len 16 chars)
# d - dynamic (scrolling) (unlimited len)

class English:

    def __init__(self):
        self.msg_s_updating_time = 'Updating Time   '
        self.msg_s_starting = 'Starting        '
        self.msg_s_gps_signal_found = 'GPS signal found'
        self.msg_d_waiting_for_signal = 'Waiting for stronger GPS signal...'
        self.msg_s_gps_signal_loss = 'GPS signal loss '
        self.msg_d_connect_gps = 'Please connect the GPS Sensor'
        self.msg_d_gps_time_updated = 'Done - GPS Time Updated'
        self.msg_d_timestamp = '{} 20{} UTC'  #{hh:mm} 20{YY-MM-DD} UTC
        self.msg_s_tracker = 'Tracker         '
        self.msg_s_weak_gps = 'Weak GPS Signal!'
        self.msg_s_active_route = 'Route: ACTIVE   '
        self.msg_s_inactive_route = 'Route: INACTIVE '
        self.msg_s_swipe_to_start = 'Swipe to start  '
        self.msg_s_distance = 'dist: {} km    '
        self.msg_s_wait = 'WAIT!          '
        self.msg_d_unexpected_termination = 'Unexpected shutdown detected. Resuming last route.'
        self.msg_s_card_read = 'Card Read!      '
        self.msg_s_id = 'ID: {}'
        self.msg_s_error = 'ERROR!           '
        self.msg_s_invalid_card = 'Invalid Card!   '
        self.msg_s_end_of_route = 'End of Route! '
        self.msg_s_warning = 'WARNING!        '
        self.msg_d_wrong_card = 'Wrong Card to end journey!'


class Romanian:

    def __init__(self):
        self.msg_s_updating_time = 'Actualizare Timp'
        self.msg_s_starting = 'Porneste        '
        self.msg_s_gps_signal_found = 'Semnal GPS gasit'
        self.msg_d_waiting_for_signal = 'Se cauta semnal GPS mai puternic...'
        self.msg_s_gps_signal_loss = 'Fara semnal GPS '
        self.msg_d_connect_gps = 'Conectati senzorul GPS'
        self.msg_d_gps_time_updated = 'Gata - Timp Actualizat'
        self.msg_d_timestamp = '{} 20{} UTC'  #{hh:mm} 20{YY-MM-DD} UTC
        self.msg_s_tracker = 'Trackerul       '
        self.msg_s_weak_gps = 'Semanal GPS Slab'
        self.msg_s_active_route = 'Ruta: ACTIVA    '
        self.msg_s_inactive_route = 'Ruta: INACTIVA  '
        self.msg_s_swipe_to_start = 'Da cu cardu\' ba'
        self.msg_s_distance = 'dist: {} km    '
        self.msg_s_wait = 'ASTEAPTA!       '
        self.msg_d_unexpected_termination = 'Intrerupere alimentare detectata. Se reia ultima ruta.'
        self.msg_s_card_read = 'Citire Card!    '
        self.msg_s_id = 'ID: {}'
        self.msg_s_error = 'EROARE!         '
        self.msg_s_invalid_card = 'Card Invalid!   '
        self.msg_s_end_of_route = 'Starsitul Rutei!'
        self.msg_s_warning = 'ATENTIE!        '
        self.msg_d_wrong_card = 'Pentru a finaliza ruta este nevoie de alt card!'