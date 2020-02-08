import sys
import time
sys.path.insert(1, '/home/pi/trackman/GPS-Tracker/lcd')
import lcddriver


class Lcd():

    def __init__(self):
        self.display_ = lcddriver.lcd()


    def display(self, text, line):
        """
        Parameters:(text to print, line number on which to print)
        Return: function to display text on lcd display
        """
        self.display_.lcd_display_string(text, line)


    def display_scrolling(self, text, line, num_scrolls=3, num_cols=16):
        """
        Parameters:(text to print, line number on which to print,
                    number of times to scroll, number of columns of lcd display)
        Return: function to display scrolling text on lcd display
        Execution time: 1 + (len(text)-16)*0.2 + 0.4
        """
        for _ in range(num_scrolls):
            if(len(text) > num_cols):
                self.display_.lcd_display_string(text[:num_cols], line)
                time.sleep(1)
                for i in range(len(text) - num_cols + 1):
                    str_to_print = text[i:i+num_cols]
                    self.display_.lcd_display_string(str_to_print, line)
                    time.sleep(0.2)
                time.sleep(0.4)
            else:
                self.display_.lcd_display_string(text, line)


    def clear(self):
        self.display_.lcd_clear()
