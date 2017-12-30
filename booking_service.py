from booking import Tables, Booking, WaitList

class BookingService():
    """Booking service object to be used from endpoint layer"""

    def __init__(self):
        self.tables = Tables()
        self.wait_list = WaitList()

    def book(self, hour, pax, customer_number, alternatives):
        """Returns true if booking was successful, otherwise returns false and
        populates alternatives list with alternative free bookings

        hour - booking start hour in 24h system
        pax - number of people in booking
        customer_number - customer telephone number
        alternatives - list variable to store alternative booking options"""

        slot = self.__hour_to_slot(hour)
        initial_booking = Booking(customer_number, pax)

        if (self.tables.check_available(slot, initial_booking)):
            self.tables.book(slot, initial_booking)
            return True
        else:
            alt = self.__generate_alternatives(slot, initial_booking)
            self.__copy_list(alt, alternatives)
            return False

    def find(self, booking_id):
        booking_tuple = self.tables.find_booking_by_id(booking_id)
        return (self.__slot_to_hour(booking_tuple[0]), booking_tuple[1])

    def cancel(self, booking_id):
        """Returns tuple with slot and cancelled booking if cancellation is
        successful, otherwise returns None"""

        booking_tuple = self.tables.cancel_booking(booking_id)
        # print("booking_tuple" + booking_tuple)
        # return self.__slot_to_hour(booking_tuple[0]), booking_tuple[1]

    def put_to_wait(self, hour, pax, customer_number):
        slot = self.__hour_to_slot(hour)
        booking = Booking(customer_number, pax)
        self.wait_list.put(slot, booking)

    def get_tables(self):
        tables_dict = []
        table_status = self.tables.get_tables()
        for i in range(0, Tables.SLOTS):
            table1booking = self.__booking_to_dict(table_status[0][i])
            table2booking = self.__booking_to_dict(table_status[1][i])
            tables_dict.append([table1booking, table2booking])
        return tables_dict

    def get_wait_list(self):
        wait_list_dict = []
        wait_list_status = self.wait_list.get_wait_list()
        for i in wait_list_status:
            booking = self.__booking_to_dict(i)
        return wait_list_dict

    def clear_bookings(self):
        self.__init__()

    def __hour_to_slot(self, hour):
        return hour - 12

    def __slot_to_hour(self, slot):
        return slot + 12

    def __generate_alternatives(self, slot, booking):
        current_pax = booking.pax
        alternatives = []

        while ((not alternatives) and (current_pax > 0)):
            for alt_slot in range(max(0, slot - 1), min(slot + 2, 12)):
                alt_booking = Booking(booking.customer_number, current_pax)
                alternatives.append((alt_slot, alt_booking))
            alternatives = self.__filter_unavailable(alternatives)
            current_pax -= 1

        self.__sort_slot_closer_to_init(alternatives, slot)
        return alternatives

    def __filter_unavailable(self, bookings):
        available = []
        for booking in bookings:
            if (self.tables.check_available(booking[0], booking[1])):
                available.append(booking)
        return available

    def __sort_slot_closer_to_init(self, bookings, initial_slot):
        bookings.sort(key = lambda t: abs(t[0] - initial_slot))

    def __copy_list(self, src, dst):
        del dst[:]
        for item in src:
            dst.append(item)

    def __booking_to_dict(self, booking):
        if booking == None:
            return {}
        else:
            return {
                "id" : booking.id,
                "pax" : booking.pax,
                "lvn" : booking.customer_number
            }
