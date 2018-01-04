"""Contains all data structures concerning booking"""

# TODO - make all these thread-safe, Booking must be immutable
# TODO - split Tables into Table and Tables
# TODO - there is assumption that only one LVN can appear in all bookings

class Booking():
    """Data class, representing single table booking"""

    last_used_id = 0

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
            print("aaa")
            self.table1[slot] = booking
            self.table2[slot] = booking
        elif self.__free(self.table1, slot):
            print("bbb")
            self.table1[slot] = booking
        else:
            print("ccc")
            self.table2[slot] = booking

    def cancel_booking(self, booking_id):
        c1 = lambda slot, booking: (slot, self.__do_cancel(self.table1, slot))
        c2 = lambda slot, booking: (slot, self.__do_cancel(self.table2, slot))
        cancelled_booking1 = self.__on_first_with_id(booking_id, self.table1, c1)
        cancelled_booking2 = self.__on_first_with_id(booking_id, self.table2, c2)
        if cancelled_booking1 != None:
            return cancelled_booking1
        else:
            return cancelled_booking2

    def find_bookings(self, customer_number):
        slots1 = self.__do_find(self.table1, customer_number)
        slots2 = self.__do_find(self.table2, customer_number)
        in_2_not_in_1 = set(slots2) - set(slots1)
        return slots1 + list(in_2_not_in_1)

    def find_booking_by_id(self, booking_id):
        return_found = lambda slot, booking: (slot, booking)
        b1 = self.__on_first_with_id(booking_id, self.table1, return_found)
        b2 = self.__on_first_with_id(booking_id, self.table2, return_found)
        if b1 != None:
            return b1
        else:
            return b2

    def get_tables(self):
        return [tuple(self.table1), tuple(self.table2)]

    def __free(self, table, slot):
        return table[slot] == None

    def __do_cancel(self, table, slot):
        cancelled_booking = table[slot]
        table[slot] = None
        return cancelled_booking

    def __on_first_with_id(self, booking_id, table, slot_booking_fun):
        for slot, booking in enumerate(table):
            if booking != None and booking.id == booking_id:
                return slot_booking_fun(slot, booking)

    def __do_find(self, table, customer_number):
        bookings = []
        for slot, booking in enumerate(table):
            if booking != None and booking.customer_number == customer_number:
                bookings.append((slot, booking))
        return bookings

class WaitList():
    """List of bookings which may only be populated from end, but any item can
    be removed. Has search function that accepts predicate and can ignore
    first ignore_count values that yield True"""

    def __init__(self):
        self.wait_list = []

    def put(self, slot_booking_tuple):
        self.wait_list.append(slot_booking_tuple)

    def remove(self, index):
        del self.wait_list[index]

    def get_list(self):
        return tuple(self.wait_list)

    def find(self, search_predicate, ignore_count = 0):
        for index, val in enumerate(self.wait_list):
            if search_predicate(val) and ignore_count <= 0:
                return index
            ignore_count -= 1
        return None

    def get_wait_list(self):
        return self.wait_list
