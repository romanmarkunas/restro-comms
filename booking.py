"""Contains all data structures concerning booking"""

class Booking():
    """Data class, representing single table booking"""

    last_used_id = 0;

    def __init__(self, customer_number, pax):
        Booking.last_used_id += 1
        self.id = Booking.last_used_id
        self.customer_number = customer_number
        self.pax = pax

class Tables():
    """Collection of table bookings throughout a day. For simplicity we decided
    that restraunt will only have 2 tables with max capacity 2 each. Also we
    decided that restraunt will be open on one single day between 12:00 and
    22:00, slot 12:00-13:00 being index 0 on the list and so on"""

    __PAX_PER_TABLE = 2
    __NO_TABLES = 2
    __MAX_PAX = __PAX_PER_TABLE * __NO_TABLES

    def __init__(self):
        self.table1 = 10*[None]
        self.table2 = 10*[None]

    def check_available(self, slot, booking):
        if (booking.pax > Tables.__MAX_PAX):
            return False
        elif (booking.pax <= Tables.__PAX_PER_TABLE):
            return self.__free(self.table1, slot) or self.__free(self.table2, slot)
        else:
            return self.__free(self.table1, slot) and self.__free(self.table2, slot)

    def book(self, slot, booking):
        if (booking.pax > Tables.__PAX_PER_TABLE):
            self.table1[slot] = booking
            self.table2[slot] = booking
        elif self.__free(self.table1, slot):
            self.table1[slot] = booking
        else:
            self.table2[slot] = booking

    def get_tables(self):
        return [tuple(self.table1), tuple(self.table2)]

    def __free(self, table, slot):
        return table[slot] == None
