"""Contains all data structures concerning booking"""

# TODO - make all these thread-safe, Booking must be immutable

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

    PAX_PER_TABLE = 2
    NO_TABLES = 2
    MAX_PAX = PAX_PER_TABLE * NO_TABLES
    SLOTS = 10

    def __init__(self):
        self.table1 = Tables.SLOTS*[None]
        self.table2 = Tables.SLOTS*[None]

    def check_available(self, slot, booking):
        if (booking.pax > Tables.MAX_PAX):
            return False
        elif (booking.pax <= Tables.PAX_PER_TABLE):
            return self.__free(self.table1, slot) or self.__free(self.table2, slot)
        else:
            return self.__free(self.table1, slot) and self.__free(self.table2, slot)

    def book(self, slot, booking):
        if (booking.pax > Tables.PAX_PER_TABLE):
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

class WaitList():
    """List of bookings which may only be populated from end, but any item can
    be removed"""

    def __init__(self):
        self.waitList = []

    def put(self, booking):
        self.waitList.append(booking)

    def remove(self, index):
        del self.waitList[index]

    def get_list(self):
        return tuple(self.waitList)

    def find_first(self, searchPredicate):
        for index, val in enumerate(self.waitList):
            if searchPredicate(val):
                return index
        return None
