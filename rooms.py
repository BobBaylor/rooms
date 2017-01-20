#! /usr/bin/env python
#
# quickstart
# from  https://developers.google.com/google-apps/calendar/quickstart/python
# I had to use easy_tools to install instead of pip


# from __future__ import print_function  # sorry, I don't really like the future

lcUuseStr = """
 --Show room usage in Lone Clone Ski Cabin--
 Usage:
  rooms  [--year=<Y>] [--debug] [--offline] [--raw] [--nights] [--future] [--member=<M>] [--guests] [--whosup]
  rooms  -h | --help
  rooms  -v | --version

 Options:
  -h --help               Show this screen.
  -d --debug              show stuff
  -f --future             show the future
  -g --guests             show raw nights with guests
  -m --member <M>         show raw nights with guests for a single member
  -n --nights             show who slept where, each night
  -o --offline            don't get the live calendar. Use a test data set
  -r --raw                show the raw calendar events
  -v --version            show the version
  -w --whosup             show who's coming up in the coming 7 days
  -y --year <Y>           year season starts [default: 2016]
    """

import httplib2
import os
import sys

from apiclient import discovery
from oauth2client import client
from oauth2client import tools
from oauth2client.file import Storage
import docopt

import datetime

if False:
    import logging
    logger = logging.getLogger()
    # logger.setLevel(logging.INFO)
    logger.setLevel(logging.WARNING)
    logging.basicConfig()


# If modifying these scopes, delete your previously saved credentials
# at ~/.credentials/calendar-python-quickstart.json
SCOPES = 'https://www.googleapis.com/auth/calendar.readonly'
CLIENT_SECRET_FILE = 'client_secret.json'
APPLICATION_NAME = 'Google Calendar API Python Quickstart'


def get_credentials(opts):
    """Gets valid user credentials from storage.

    If nothing has been stored, or if the stored credentials are invalid,
    the OAuth2 flow is completed to obtain the new credentials.

    Returns:
        Credentials, the obtained credential.
    """
    home_dir = os.path.expanduser('~')
    credential_dir = os.path.join(home_dir, '.credentials')
    if not os.path.exists(credential_dir):
        os.makedirs(credential_dir)
    credential_path = os.path.join(credential_dir,'calendar-python-quickstart.json')
    if opts['--debug']:
        print '** using credentials at '+credential_path
    store = Storage(credential_path)
    credentials = store.get()
    if not credentials or credentials.invalid:
        flow = client.flow_from_clientsecrets(CLIENT_SECRET_FILE, SCOPES)
        flow.user_agent = APPLICATION_NAME
        if flags:
            credentials = tools.run_flow(flow, store, flags)
        else: # Needed only for compatibility with Python 2.6
            credentials = tools.run(flow, store)
        print 'Storing credentials to ' + credential_path
    return credentials

def get_events(cred, **kwargs):
    http = cred.authorize(httplib2.Http())
    service = discovery.build('calendar', 'v3', http=http)      # throws Warning and ImportError
    eventsResult = service.events().list(**kwargs).execute()
    ev = eventsResult.get('items',[])
    return ev


def gevent_to_member_name(e):
    mem = e['summary'].split()[0].replace(',','')
    return mem

def main(opts):
    """
    Creates a Google Calendar API service object and outputs a list of
    date, who, where    inlaw, master, middle,  bunk,  loft
    who,                count,  count,  count, count, count

    """
    if opts['--offline']:
        datesRaw = [
            {'night':'2016-12-03', 'summary':'Logan', 'description':'master'},
            {'night':'2016-12-03', 'summary':'Bob', 'description':'inlaw'},     # test inlaw->in-law sub
            {'night':'2016-12-03', 'summary':'Mark', 'description':'bunk'},
            {'night':'2016-12-03', 'summary':'Jon', 'description':'middle'},
            {'night':'2016-12-04', 'summary':'Logan', 'description':'master'},
            {'night':'2016-12-04', 'summary':'Jon', 'description':'in-law'},
            {'night':'2016-12-05', 'summary':'Logan', 'description':'master'},
            {'night':'2016-12-05', 'summary':'Jon', 'description':'in-law'},
            {'night':'2016-12-06', 'summary':'Logan', 'description':'master'},
            {'night':'2016-12-06', 'summary':'James', 'description':'in-law'},
            {'night':'2016-12-07', 'summary':'Logan', 'description':'master'},
            {'night':'2016-12-08', 'summary':'Logan', 'description':'master'},
            {'night':'2016-12-09', 'summary':'Logan', 'description':'master'},
            {'night':'2016-12-11', 'summary':'Logan', 'description':'master'},
            {'night':'2016-12-11', 'summary':'James', 'description':'in-law'},
            {'night':'2016-12-12', 'summary':'Logan', 'description':'master'},
            {'night':'2016-12-12', 'summary':'James', 'description':'in-law'},
            {'night':'2016-12-13', 'summary':'Bob S +1', 'description':'master, middle'}, # test Bob S to BobS sub
            {'night':'2016-12-13', 'summary':'James', 'description':'in-law'},
            {'night':'2016-12-14', 'summary':'James', 'description':'in-law'},
            {'night':'2016-12-15', 'summary':'Logan', 'description':'master'}
            ]
    else:
        credentials = get_credentials(opts)
        day0 = datetime.datetime(int(opts['--year']),12,1).isoformat()+'Z'
        dayLast = datetime.datetime.utcnow().isoformat() + 'Z'
        if opts['--future']:
            dayLast = None
        if opts['--whosup']:
            dayThis = datetime.datetime.utcnow() + datetime.timedelta(days=7)
            dayLast = dayThis.isoformat() + 'Z'
        events = get_events(credentials,timeMin=day0,timeMax=dayLast, singleEvents=True, orderBy='startTime',calendarId="primary")
        datesRaw = []
        for event in events:
            e = {}
            e['night'] = event['start'].get('dateTime', event['start'].get('date'))[:10]  # {'night':'2016-12-15'}
            # summary is the member name, description has room assignment
            for k in ('summary','description','colorId'):
                try:
                    e[k] = event[k]
                except KeyError:
                    e[k] = ''
            datesRaw += [e]
    # datesRaw[] is a list of  {'night':'2016-12-15', 'summary':'Logan', 'description':'master'}
    for e in datesRaw:             # add day of week
        e['night'] = datetime.datetime.strptime(e['night'],'%Y-%m-%d').strftime('%a %m/%d')   # turn "2016-12-23" into "Fri 12/23"

    for e in datesRaw:             # fix spelling
        for field, wrong, right in [('description','inlaw','in-law'),('summary','Bob S','BobS ')]:
            if opts['--debug']:
                if wrong in e[field]:
                    print '** spellcheck:', e
            e[field] = e[field].replace(wrong,right)    #  in-law, not inlaw, e.g.

    if opts['--debug']:
        print '** datesRaw'
        print '{'+ '},\n{'.join([', '.join(["'%s':'%s'"%(n,e[n]) for n in ('night','summary','description')]) for e in datesRaw]) +'}'

    rooms =  ('in-law', 'master', 'middle',  'bunk',  'loft')
    memberCnts = {}
    for e in datesRaw:
        memberCnts[ gevent_to_member_name(e) ] = {t:0 for t in rooms+('total',)}              # init the memberCnts with the first name {rooms}

    for e in datesRaw:                                                       # add ['middle']='Logan' or blank for all rooms
        memberCnts[gevent_to_member_name(e)]['total'] = memberCnts[gevent_to_member_name(e)]['total']+1
        for r in rooms:
            if r in e['description'].lower():
                e[r] = gevent_to_member_name(e)   # just the first name
                memberCnts[ e[r] ][r] = memberCnts[ e[r] ][r]+1
            else:
                e[r] = ''
        # todo: limit this next thing to the next 7 days
        if all([not bool(e[r]) for r in rooms]):
            if not (opts['--future'] or opts['--whosup']):        # catch members in cabin but not assigned to any room
                print '** On %s where did %s sleep?'%(e['night'],e['summary'])
            if opts['--whosup']:            # show me the who's up
                print '   %s %s'%(e['night'],e['summary'])
    # datesRaw[] is now a list of  {'night':'2016-12-15', 'summary':'Logan', 'description':'master', 'master':'Logan', 'in-law':'', 'midle':'', ...}
    # memberCnts{} = {'Bob':{'in-law':1, 'master':0, 'middle':0,  'bunk':1,  'loft':0}, 'Mark:{'master':1,...},...}

    if opts['--raw']:
        print ''
        print '%10s %10s %-20s'%('','','Raw Calendar')+' '.join(['%10s'%r for r in rooms])
        for e in datesRaw:
            print '%10s %-10s %-20s'%(e['night'],e['summary'],e['description'])+' '.join(['%10s'%e[r] for r in rooms])

    gPeak = ['Fri','Sat']+['12/%2d'%x for x in range(18,32)]+['01/01','01/02','02/19',]
    if opts['--guests']:
        print ''
        print '%10s %20s %-20s'%('','','Guests Calendar')
        gFeeTot, gTot = 0, 0
        for e in datesRaw:
            if '+' in e['summary'] and 'Z+1' not in e['summary']: # guests but not Z+1 (Sam). Enter "Z +1" to indicate not Sam (chargable)
                gFee = 40 if any([x in e['night'] for x in gPeak]) else 35
                gFee *= int(e['summary'].split('+')[1])
                gFeeTot += gFee
                gTot += 1
                # if not any([c in e['summary'] for c in ('Erin','Jon','Bob ',)]):
                print '%10s %4d %-20s %-20s'%(e['night'],gFee,e['summary'],e['description'])
        print 'Total %d guests and $%d in fees'%(gTot,gFeeTot)

    if opts['--member']:
        print ''
        print '%10s %20s %-20s'%('','','Guests Calendar')
        for e in datesRaw:
            if '+' in e['summary'] and opts['--member'] in e['summary'].split():
                print '%10s %-20s %-20s'%(e['night'],e['summary'],e['description'])

    datesComb = [datesRaw[0]]  # colapse the raw calendar to show each night on one line
    for e in datesRaw[1:]:
        if datesComb[-1]['night'] not in e['night']:        # new date
            datesComb += [e]
        else:
            for r in rooms:
                sep = ',' if e[r] and datesComb[-1][r] else ''
                datesComb[-1][r] = datesComb[-1][r]+sep+e[r]
    # datesComb[] is {'night':'2016-12-15', 'summary':'Logan', 'description':'master', 'master':'Logan', 'in-law':'Bob', 'midle':'Mark', ...}

    if opts['--nights']:
        print '\n%10s '%('Nights')+' '.join(['%16s'%r for r in rooms])
        for e in datesComb:
            print '%10s '%(e['night'])+' '.join(['%16s'%e[r] for r in rooms])


    print '\n%4s%10s'%('','Counts')+' '.join(['%8s'%r for r in rooms])   # show how many times each member has slept in each room
    for c in memberCnts:
        print '%4d%10s'%(memberCnts[c]['total'],c)+' '.join(['%8s'%('%d'%memberCnts[c][r] if memberCnts[c][r] else '' ) for r in rooms])



if __name__ == '__main__':
    opts = docopt.docopt(lcUuseStr,version='0.0.9')
    # print(opts)
    main(opts)
