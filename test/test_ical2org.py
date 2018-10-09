from __future__ import print_function

import datetime
from freezegun import freeze_time
import pytz
import sys
import unittest

try:
    import ical2org
except ImportError as e:
    print('Import error:', str(e), file=sys.stderr)
    sys.exit(1)

class TestIcal2Org(unittest.TestCase):
    def setUp(self):
        self.ics_string_tpl = """\
BEGIN:VCALENDAR
PRODID:-//Google Inc//Google Calendar 70.9054//EN
VERSION:2.0
CALSCALE:GREGORIAN
METHOD:PUBLISH
X-WR-CALNAME:Personal
X-WR-TIMEZONE:America/Los_Angeles
BEGIN:VTIMEZONE
TZID:America/Los_Angeles
X-LIC-LOCATION:America/Los_Angeles
BEGIN:DAYLIGHT
TZOFFSETFROM:-0800
TZOFFSETTO:-0700
TZNAME:PDT
DTSTART:19700308T020000
RRULE:FREQ=YEARLY;BYMONTH=3;BYDAY=2SU
END:DAYLIGHT
BEGIN:STANDARD
TZOFFSETFROM:-0700
TZOFFSETTO:-0800
TZNAME:PST
DTSTART:19701101T020000
RRULE:FREQ=YEARLY;BYMONTH=11;BYDAY=1SU
END:STANDARD
END:VTIMEZONE
BEGIN:VTIMEZONE
TZID:America/Chicago
X-LIC-LOCATION:America/Chicago
BEGIN:DAYLIGHT
TZOFFSETFROM:-0600
TZOFFSETTO:-0500
TZNAME:CDT
DTSTART:19700308T020000
RRULE:FREQ=YEARLY;BYMONTH=3;BYDAY=2SU
END:DAYLIGHT
BEGIN:STANDARD
TZOFFSETFROM:-0500
TZOFFSETTO:-0600
TZNAME:CST
DTSTART:19701101T020000
RRULE:FREQ=YEARLY;BYMONTH=11;BYDAY=1SU
END:STANDARD
END:VTIMEZONE
BEGIN:VEVENT
{event}
END:VEVENT
END:VCALENDAR
"""

    def current_datetime(self, timezone):
        """Generate the datetime object and dates for now.
        """
        dt = datetime.datetime.now(tz = pytz.timezone(timezone))
        return {
            "COMPACT": dt.strftime("%Y%m%d"),
            "DASHED": dt.strftime("%Y-%m-%d"),
            "datetime": dt,
            "DOW": dt.strftime("%a")
        }

    def earliest_datetime(self, timezone):
        """Since the code only looks back a specific period, find the earliest
        date it will generate.
        """
        dt = datetime.datetime.now(tz = pytz.timezone(timezone)) - datetime.timedelta(days = WINDOW)
        return {
            "COMPACT": dt.strftime("%Y%m%d"),
            "DASHED": dt.strftime("%Y-%m-%d"),
            "datetime": dt,
            "DOW": dt.strftime("%a")
        }

    @freeze_time("2016-10-22 19:00:00")
    def test_zero_duration_event(self):
        """When the start and end times are the same, the "DTEND" line is not
        included.
        """
        ics_string = self.ics_string_tpl.format(timezone = "America/Los_Angeles",
                                                event = """\
DTSTART:20161022T230000Z
DTSTAMP:20160904T144133Z
CREATED:20160903T055100Z
DESCRIPTION:
LAST-MODIFIED:20160903T055101Z
SEQUENCE:0
STATUS:CONFIRMED
SUMMARY:Event 1
""")

        org_lines = ical2org.convert_ical(ics_string)

        self.assertEqual(org_lines[2].strip(),
                         "<2016-10-22 Sat 16:00>--<2016-10-22 Sat 16:00>")

    @freeze_time("2016-10-22 19:00:00")
    def test_default_timezone(self):
        """The event time will use the default timezone from the calendar when
        not specified.

        """
        ics_string = self.ics_string_tpl.format(timezone = "America/Los_Angeles",
                                                event = """\
DTSTART:20161022T190000Z
DTEND:20161022T200000Z
DTSTAMP:20160904T144133Z
CREATED:20160903T055100Z
DESCRIPTION:
LAST-MODIFIED:20160903T055101Z
SEQUENCE:0
STATUS:CONFIRMED
SUMMARY:Event 1
""")

        org_lines = ical2org.convert_ical(ics_string)

        self.assertEqual(org_lines[2].strip(),
                         "<2016-10-22 Sat 12:00>--<2016-10-22 Sat 13:00>")

    @freeze_time("2016-10-22 19:00:00")
    def test_specified_timezone(self):
        """The event time will use a specified timezone.
        """
        ics_string = self.ics_string_tpl.format(
            timezone = "America/Los_Angeles",
            event = """\
DTSTART;TZID=Europe/Paris:20161022T230000Z
DTEND;TZID=Europe/Paris:20161023T020000Z
DTSTAMP:20160904T144133Z
CREATED:20160903T055100Z
DESCRIPTION:
LAST-MODIFIED:20160903T055101Z
SEQUENCE:0
STATUS:CONFIRMED
SUMMARY:Event 1
""")

        org_lines = ical2org.convert_ical(ics_string)

        self.assertEqual(org_lines[2].strip(),
                         "<2016-10-22 Sat 14:00>--<2016-10-22 Sat 17:00>")

    @freeze_time("2016-11-17 19:00:00")
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

        org_lines = ical2org.convert_ical(ics_string)

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


    @freeze_time("2018-10-07 00:00:00")
    def test_single_zulu_event(self):
        """A single event with Z dates will show up at the correct time in the
        calendar.
        """
        ics_string = self.ics_string_tpl.format(timezone = "America/Los_Angeles",
                                                event = """\
DTSTART:20181008T020000Z
DTEND:20181008T022000Z
DTSTAMP:20181008T121345Z
UID:c4s3ep9j68pjcb9k75j3ib9k6tim6bb1ckr32b9n60pj2p1l6ormcd32c4@google.com
CREATED:20181007T155551Z
DESCRIPTION:
LAST-MODIFIED:20181007T155551Z
LOCATION:
SEQUENCE:0
STATUS:CONFIRMED
SUMMARY:SpaceX launch
TRANSP:OPAQUE
BEGIN:VALARM
ACTION:DISPLAY
DESCRIPTION:This is an event reminder
TRIGGER:-P0DT0H5M0S
END:VALARM
""")
        org_lines = ical2org.convert_ical(ics_string)

        self.assertEqual(org_lines[2].strip(),
                         "<2018-10-07 Sun 19:00>--<2018-10-07 Sun 19:20>")
