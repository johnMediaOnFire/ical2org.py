from __future__ import print_function

import sys
import unittest

try:
    from ical2org import convert_ical
except ImportError as e:
    print >> sys.stderr, 'Import error:', str(e)
    sys.exit(1)

class TestIcal2Org(unittest.TestCase):
    def setUp(self):
        self.ics_string_tpl = """BEGIN:VCALENDAR
PRODID:-//Google Inc//Google Calendar 70.9054//EN
VERSION:2.0
CALSCALE:GREGORIAN
METHOD:PUBLISH
BEGIN:VTIMEZONE
TZID:{timezone}
END:VTIMEZONE
BEGIN:VEVENT
{event}
END:VEVENT
END:VCALENDAR
"""

    def test_zero_duration_event(self):
        """When the start and end times are the same, the "DTEND" line is not
        included.
        """
        ics_string = self.ics_string_tpl.format(timezone = "America/Los_Angeles",
                                                event = """DTSTART:20161022T230000Z
DTSTAMP:20160904T144133Z
CREATED:20160903T055100Z
DESCRIPTION:
LAST-MODIFIED:20160903T055101Z
SEQUENCE:0
STATUS:CONFIRMED
SUMMARY:Event 1
""")

        org_lines = convert_ical(ics_string)

        self.assertEqual(org_lines[2].strip(),
                         "<2016-10-22 Sat 16:00>--<2016-10-22 Sat 16:00>")

    def test_default_timezone(self):
        """The event time will use the default timezone from the calendar when
        not specified.

        """
        ics_string = self.ics_string_tpl.format(timezone = "America/Los_Angeles",
                                                event = """DTSTART:20161022T230000Z
DTEND:20161023T020000Z
DTSTAMP:20160904T144133Z
CREATED:20160903T055100Z
DESCRIPTION:
LAST-MODIFIED:20160903T055101Z
SEQUENCE:0
STATUS:CONFIRMED
SUMMARY:Event 1
""")

        org_lines = convert_ical(ics_string)

        self.assertEqual(org_lines[2].strip(),
                         "<2016-10-22 Sat 16:00>--<2016-10-22 Sat 19:00>")

    def test_specified_timezone(self):
        """The event time will use a specified timezone.
        """
        ics_string = self.ics_string_tpl.format(
            timezone = "America/Los_Angeles",
            event = """DTSTART;TZID=Europe/Paris:20161022T230000Z
DTEND;TZID=Europe/Paris:20161023T020000Z
DTSTAMP:20160904T144133Z
CREATED:20160903T055100Z
DESCRIPTION:
LAST-MODIFIED:20160903T055101Z
SEQUENCE:0
STATUS:CONFIRMED
SUMMARY:Event 1
""")

        org_lines = convert_ical(ics_string)

        self.assertEqual(org_lines[2].strip(),
                         "<2016-10-22 Sat 14:00>--<2016-10-22 Sat 17:00>")

    def test_weekly_duration_event_with_bydays(self):
        """When specific days are set for weekly recurring events, only events
        for the specified days will be generated.
        """
        ics_string = self.ics_string_tpl.format(timezone = "America/Los_Angeles",
                                                event = """
DTSTART;TZID=America/Los_Angeles:20161117T100000
DTEND;TZID=America/Los_Angeles:20161117T101500
RRULE:FREQ=WEEKLY;BYDAY=MO,TU,WE,TH,FR
CREATED:20161019T223911Z
LAST-MODIFIED:20161117T181500Z
DESCRIPTION:
SEQUENCE:1
STATUS:CONFIRMED
SUMMARY:Event 1
""")

        org_lines = convert_ical(ics_string)

        # This is gross, but I'm taking the easy path instead of doing
        # a bunch of date math.
        self.assertEqual(org_lines[3].strip(),
                         '<2016-11-17 Thu 10:00>--<2016-11-17 Thu 10:15>')
        self.assertEqual(org_lines[9].strip(),
                         '<2016-11-18 Fri 10:00>--<2016-11-18 Fri 10:15>')
        self.assertEqual(org_lines[15].strip(),
                         '<2016-11-21 Mon 10:00>--<2016-11-21 Mon 10:15>')
        self.assertEqual(org_lines[21].strip(),
                         '<2016-11-22 Tue 10:00>--<2016-11-22 Tue 10:15>')
        self.assertEqual(org_lines[27].strip(),
                         '<2016-11-23 Wed 10:00>--<2016-11-23 Wed 10:15>')
        self.assertEqual(org_lines[33].strip(),
                         '<2016-11-24 Thu 10:00>--<2016-11-24 Thu 10:15>')
        self.assertEqual(org_lines[39].strip(),
                         '<2016-11-25 Fri 10:00>--<2016-11-25 Fri 10:15>')
        self.assertEqual(org_lines[45].strip(),
                         '<2016-11-28 Mon 10:00>--<2016-11-28 Mon 10:15>')
        self.assertEqual(org_lines[51].strip(),
                         '<2016-11-29 Tue 10:00>--<2016-11-29 Tue 10:15>')
