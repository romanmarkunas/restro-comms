from booking import Tables, Booking

class BookingService():
    """Booking service object to be used from endpoint layer"""

    def __init__(self):
        self.tables = Tables()

    def book(self, hour, pax, customer_number, alternatives):
        """Returns true if booking was successful, otherwise returns false and
        populates alternatives list with alternative free bookings

        hour - booking start hour in 24h system
        pax - number of people in booking
        customer_number - customer telephone number
        alternatives - list variable to store alternative booking options"""

        slot = hour - 12;
        initial_booking = Booking(customer_number, pax)

        if (self.tables.check_available(slot, initial_booking)):
            self.tables.book(slot, initial_booking)
            return True
        else:
            alt = self.__generate_alternatives(slot, initial_booking)
            self.__copy_list(alt, alternatives)
            return False

    def get_tables(self):
        tables_dict = []
        table_status = self.tables.get_tables()
        for i in range(0, Tables.SLOTS):
            table1booking = self.__booking_to_dict(table_status[0][i])
            table2booking = self.__booking_to_dict(table_status[1][i])
            tables_dict.append([table1booking, table2booking])
        return tables_dict

    def clear_bookings(self):
        self.__init__()

    def __generate_alternatives(self, slot, booking):
        current_pax = booking.pax
        alternatives = []

        while ((not alternatives) or (current_pax <= 0)):
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