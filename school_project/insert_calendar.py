# -*- coding: utf-8 -*-
import os, sys, django
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'school_project.settings')
django.setup()

from school_app.models import AcademicCalendarEvent, District

# ── Change district_id here if needed ──
DISTRICT_ID = 1  # Tonk

district = District.objects.get(id=DISTRICT_ID)
print(f"Inserting events for district: {district.name_english}")

# Clear existing events for this district before inserting
AcademicCalendarEvent.objects.filter(district=district).delete()


events = [
    {"start": "2025-01-08", "end": "2025-01-10", "type": "teaching", "title": "<b>अध्याय 01 एवं 03</b><br>01-वास्तविक संख्याएँ <br>03–दो चर वाले रैखिक समीकरण "},
    {"start": "2025-01-11", "end": "2025-01-11", "type": "exam",     "title": "<p  ><b> अध्याय 01 एवं 03 का मूल्यांकन (प्रथम)</b><br>-अभिभावक-शिक्षक मीटिंग में लक्ष्य 2025 की जानकारी </p>"},
    {"start": "2025-01-13", "end": "2025-01-13", "type": "teaching", "title": "<b>अध्याय 02,05</b> <br>02 - बहुपद<br>05 – समान्तर श्रेणी"},
    {"start": "2025-01-15", "end": "2025-01-16", "type": "teaching", "title": "<b>अध्याय 02 एवं 05</b><br>02-बहुपद<br>05–समान्तर श्रेणी"},
    {"start": "2025-01-20", "end": "2025-01-20", "type": "exam",     "title": "<p  >अध्याय 02 एवं 05 का मूल्यांकन (द्वितीय)</p>"},
    {"start": "2025-01-21", "end": "2025-01-24", "type": "teaching", "title": "<b>अध्याय 04, 07,14</b> <br>04- द्विघात समीकरण <br>07- निर्देशांक ज्यामिति<br>14-प्रायिकता"},
    {"start": "2025-01-25", "end": "2025-01-25", "type": "exam",     "title": "<p  >अध्याय 04, 07, 14 का मूल्यांकन (तृतीय)</p>"},
    {"start": "2025-01-27", "end": "2025-01-31", "type": "teaching", "title": "<b>अध्याय 10,11,13</b><br>10 - वृत <br>11 - वृतों से संबंधित क्षेत्रफल <br>13 - सांख्यिकी"},
    {"start": "2025-02-01", "end": "2025-02-01", "type": "exam",     "title": "<p  >अध्याय 10, 11, 13 का मूल्यांकन (चतुर्थ)</p>"},
    {"start": "2025-02-07", "end": "2025-02-08", "type": "teaching", "title": "<b> अध्याय  06,08,09,12</b><br>06 - त्रिभुज <br>08 - त्रिकोणमिति का परिचय <br>09 - त्रिकोणमिति का अनुप्रयोग <br>12 - पृष्ठीय क्षेत्रफल एवं आयतन"},
    {"start": "2025-02-10", "end": "2025-02-14", "type": "teaching", "title": "<b>अध्याय  06,08,09,12</b><br>06 - त्रिभुज <br>08 - त्रिकोणमिति का परिचय <br>09 - त्रिकोणमिति का अनुप्रयोग <br>12 - पृष्ठीय क्षेत्रफल एवं आयतन"},
    {"start": "2025-02-15", "end": "2025-02-15", "type": "exam",     "title": "<p  >- अध्याय 06,08,09 एवं 12 का मूल्यांकन (पंचम)</p>"},

    {"start": "2025-12-03", "end": "2025-12-06", "type": "teaching", "title": "<b>अध्याय 01 एवं 03</b><br>01-वास्तविक संख्याएँ <br>03–दो चर वाले रैखिक समीकरण "},
    {"start": "2025-12-08", "end": "2025-12-08", "type": "exam",     "title": "<p  ><b> अध्याय 01 एवं 03 का मूल्यांकन (प्रथम)</b></p>"},
    {"start": "2025-12-09", "end": "2025-12-13", "type": "teaching", "title": "<b>अध्याय 02,05</b> <br>02 - बहुपद<br>05 – समान्तर श्रेणी"},
    {"start": "2025-12-15", "end": "2025-12-15", "type": "exam",     "title": "<p  ><b> अध्याय 02 एवं 05 का मूल्यांकन (द्वितीय)</b></p>"},
    {"start": "2025-12-16", "end": "2025-12-20", "type": "teaching", "title": "<b>अध्याय 04, 07,14</b> <br>04- द्विघात समीकरण <br>07- निर्देशांक ज्यामिति<br>14-प्रायिकता"},
    {"start": "2025-12-22", "end": "2025-12-22", "type": "teaching", "title": "<b>अध्याय 04, 07,14</b> <br>04- द्विघात समीकरण <br>07- निर्देशांक ज्यामिति<br>14-प्रायिकता"},
    {"start": "2025-12-23", "end": "2025-12-23", "type": "exam",     "title": "<p  ><b>  अध्याय 04, 07, 14 का मूल्यांकन (तृतीय)</b></p>"},

    {"start": "2026-01-06", "end": "2026-01-10", "type": "teaching", "title": "<b>अध्याय 10,11,13</b><br>10 - वृत <br>11 - वृतों से संबंधित क्षेत्रफल <br>13 - सांख्यिकी"},
    {"start": "2026-01-12", "end": "2026-01-15", "type": "teaching", "title": "<b>अध्याय 10,11,13</b><br>10 - वृत <br>11 - वृतों से संबंधित क्षेत्रफल <br>13 - सांख्यिकी"},
    {"start": "2026-01-16", "end": "2026-01-16", "type": "exam",     "title": "<p  ><b>अध्याय 10, 11, 13 का मूल्यांकन (चतुर्थ)</b></p>"},
    {"start": "2026-01-17", "end": "2026-01-17", "type": "teaching", "title": "<b> अध्याय  08,09</b><br>08 - त्रिकोणमिति का परिचय <br>09 - त्रिकोणमिति का अनुप्रयोग "},
    {"start": "2026-01-19", "end": "2026-01-23", "type": "teaching", "title": "<b> अध्याय  08,09</b><br>08 - त्रिकोणमिति का परिचय <br>09 - त्रिकोणमिति का अनुप्रयोग "},
    {"start": "2026-01-24", "end": "2026-01-24", "type": "exam",     "title": "<p  ><b>अध्याय 08,09  का मूल्यांकन (पंचम)</b></p>"},
    {"start": "2026-01-27", "end": "2026-01-31", "type": "teaching", "title": "<b>अध्याय  06,12</b><br>06 - त्रिभुज <br>12 - पृष्ठीय क्षेत्रफल एवं आयतन"},
    {"start": "2026-02-02", "end": "2026-02-02", "type": "exam",     "title": "<p  ><b>अध्याय 06,12  का मूल्यांकन (षष्टम)</b></p>"},
    {"start": "2026-02-05", "end": "2026-02-05", "type": "exam",     "title": "<p  ><b>प्रीबोर्ड परीक्षा (सम्पूर्ण पाठ्यक्रम)</b></p>"},
]

objs = [
    AcademicCalendarEvent(
        district=district,
        title=e["title"],
        start_date=e["start"],
        end_date=e["end"],
        event_type=e["type"],
    )
    for e in events
]
AcademicCalendarEvent.objects.bulk_create(objs)
print(f"Inserted {len(objs)} events successfully.")
