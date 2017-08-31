from icalendar import Calendar, Event
from datetime import datetime, timedelta
from bs4 import BeautifulSoup
import sys,os,traceback
import requests
import argparse

def display(cal):
    return cal.to_ical().decode("utf-8").replace('\r\n', '\n').strip()

def save(output, input):
	print("Saving " + input + " as " + output)
	with open(output, 'wb') as handle:
		response = requests.get(input, stream=True)
		if not response.ok:
			print("oh no! network pipe failed!")
		for block in response.iter_content(1024):
			handle.write(block)

def downloadCalendar(year, month):
    localfile = "calendar_html/" + year + "-" + month + ".html"
    if os.path.isfile(localfile):
        return
    url = "https://www.utdallas.edu/calendar/getEvents.php?month=" + month + "&year=" + year + "&type=month"
    save(localfile,url)

def download(url, type_):
    localfile = type_ + "/" + url[-10:] + ".html"
    if os.path.isfile(localfile):
        return
    save(localfile,url)

Calendars = {}

def process_calendar(year,month):
    soup = BeautifulSoup (open("calendar_html/" + year + "-" + month + ".html"), 'html.parser')
    for web_day in soup.find_all(name="div",id="cal-events-display-grey"):
        day = web_day.find(id="green-box-day").text
        for event in web_day.find_all("li"):
            time_range = event.find(class_="events-time").text
            event_title = event.find(class_="eventTitle").text
            link = "https://www.utdallas.edu/calendar/" + event.find(class_="eventTitle").attrs.get('href')

            event = Event()

            #Handle Date/time Range
            def strToDatetime(timestr):
                hour = int(timestr[:timestr.index(":")])
                minute = int(timestr[timestr.index(":")+1:timestr.index(" ")])
                if timestr.find("p") >= 0 and hour != 12:
                    hour = (hour+12)%24
                return datetime(int(year),int(month),int(day),hour,minute)

            try:
                start_time = time_range[:time_range.index("-")-1]
                end_time = time_range[time_range.index("-")+2:]

                dtstart = strToDatetime(start_time)
                dtend = strToDatetime(end_time)
            except ValueError:

                dtstart = strToDatetime(start_time)
                dtend = strToDatetime(start_time) + timedelta(minutes=30)
            if dtstart == dtend:
                dtend += timedelta(minutes=30)

            #Handle event details
            download(link,"event")
            try:
                esoup = BeautifulSoup (open("event/" + link[-10:] + ".html"), 'html.parser',from_encoding='UTF-8')
                htmlbody = str(esoup.find(id="event_detail"))
                #page-content
                htmlbody = htmlbody.replace("<a href=\"/","<a href=\"https://www.utdallas.edu/") #Fix relative URIs
                htmlbody = htmlbody.replace(str(esoup.find('a',text='Questions? Email me.')),"") #Get rid of cloudflare email redirects
                htmlbody += "<br /><a href=" + link + ">See this on the original comet calendar page.</a>"
                tags = str(esoup.find(class_='linker').text)[10:].split(', ')
                tags = ["TAG#" + e + "%" for e in tags]
                tags.insert(0,"AUTHOR#" + esoup.find_all('span', class_='linker')[1].find('a').text)

            except (UnicodeDecodeError, AttributeError):
                print(event_title + ": " + time_range + " (" + link + " )")
                traceback.print_exc(file=sys.stdout)
                htmlbody = "<br /><a href=" + link + ">See this on the original comet calendar page.</a><br /><span style=\"font-size: 0.2em;\">Sorry about this.</span>"
                tags = ["MISC#Unknown"]
            tags.insert(0,"MISC#All Calendars")
            event.add('summary',event_title)
            event.add('description',"htmlbody")
            event.add('dtstart',dtstart)
            event.add('dtend', dtend)
            event['language'] = 'en-us:HTML'
            event['X-ALT-DESC;FMTTYPE=text/html'] = htmlbody

            try:
                event.add('location', esoup.find(class_='location').find('span').text)
            except: pass

            # try:
            #     print(display(event))
            # except: pass
            #print(Calendars.keys())
            for tag in tags:
                if not Calendars.get(tag):
                    Calendars[tag] = Calendar()
                    Calendars[tag].add('X-WR-CALNAME',tag)
                    Calendars[tag].add('METHOD','PUBLISH')
                    Calendars[tag].add('SUMMARY',tag)

                Calendars[tag].add_component(event)
            #input()

parser = argparse.ArgumentParser(description='Parses ranges')
parser.add_argument('YearStart', type=int)
parser.add_argument('YearEnd', type=int)
parser.add_argument('--MonthStart', default=1, type=int)
parser.add_argument('--MonthEnd', default=1, type=int)
args = parser.parse_args()


if not os.path.exists("calendars/"): os.makedirs("calendars/")
if not os.path.exists("event/"): os.makedirs("event/")
if not os.path.exists("calendar_html/"): os.makedirs("calendar_html/")

for process_year in range(args.YearStart,args.YearEnd+1):
    print(process_year)
    for process_month in range(args.MonthStart,args.MonthEnd+1):
        print(process_month)
        downloadCalendar(str(process_year),str(process_month))
        process_calendar(str(process_year),str(process_month))

for key in Calendars.keys():
    if not os.path.exists("calendars/" + key.split("#")[0]): os.makedirs("calendars/" + key.split("#")[0])
    file = open("calendars/" + key.split("#")[0] + "/" + "".join([c for c in key.split("#")[1] if c.isalpha() or c.isdigit() or c==' ']).rstrip().replace(" ","_") +'.ics', 'w', encoding="utf-8")
    try:
        file.write(display(Calendars.get(key)))
    except:
        traceback.print_exc(file=sys.stdout)
    finally:
        file.close()
