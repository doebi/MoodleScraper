#!/usr/bin/env python
from requests import session
from bs4 import BeautifulSoup
import os, sys, itertools, re
import urllib
import ConfigParser
import datetime

# read config
config = ConfigParser.RawConfigParser()
config.read('scraper.conf')

username = config.get("scraper", "user");
password = config.get("scraper", "pwd");
root = config.get("scraper", "root");
baseurl = config.get("scraper", "baseurl");

sections = itertools.count()
files = itertools.count()

class colors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'

def login(user, pwd):
    authdata = {
        'action': 'login',
        'username': user,
        'password': pwd
    }
    with session() as ses:
        r = ses.post(baseurl + 'login/index.php', data=authdata)
        return ses


def getSemesters(ses):
    r = ses.get(baseurl + 'index.php')

    if(r.status_code == 200):
        soup = BeautifulSoup(r.text, 'html.parser')
        semesters = dict()
        temp = soup.find(id='cmb_mc_semester')

        for o in soup.find(id='cmb_mc_semester'):
            if o != unicode('\n'):
                if o.string != 'Alle Semester':
                    semesters[o['value']] = o.string
        return semesters
    else:
        print 'ERROR: ' + str(r.status) + ' ' + r.reason
	sys.exit()


def getInfo(tag):
    c = dict()
    c['url'] = tag['href']
    p = unicode(tag.string).split(',')
    if len(p) >= 3:
        q = p[0].split('.')
        c['course'] = q[0].strip()
        c['sem'] = q[1]
        c['key'] = q[2].strip()
        c['name'] = p[1].strip()
        c['type'] = p[2].strip().replace(' ', '-')
    elif len(p) == 1:
        c['course'] = p[0].strip()
        c['sem'] = 'X'
        c['key'] = p[0].strip()
        c['name'] = p[0].strip()
        c['type'] = 'Allgemein'
    return c


def getCoursesForSem(session, s):
    r = session.get(baseurl + 'index.php?role=0&cat=1&csem=0&sem=' + s)
    if(r.status_code == 200):
        soup = BeautifulSoup(r.text, 'html.parser')
        courses = list()
        for o in soup.find_all('h3'):
            if (len(o.find_all('a')) > 0):
                c = getInfo(o.contents[0])
                courses.append(c)
        return courses
    else:
        print 'ERROR: ' + str(r.status) + ' ' + r.reason
	sys.exit()


def saveFile(session, src, path, name):
    global files
    files.next()
    dst = path + name


    try:
        with open(dst):
            print '['+colors.OKBLUE+'skip'+colors.ENDC+'] |  |  +--%s' %name
            pass
    except IOError:
        with open(dst, 'wb') as handle:
            print '['+colors.OKGREEN+'save'+colors.ENDC+'] |  |  +--%s' %name
            r = session.get(src, stream=True)
            for block in r.iter_content(1024):
                if not block:
                    break
                handle.write(block)


def saveLink(session, url, path, name):
    global files
    files.next()
    fname = name.encode('utf-8').replace('/', '') + '.html'
    dst = path.encode('utf-8') + fname
    try:
        with open(dst):
            print '['+colors.OKBLUE+'skip'+colors.ENDC+'] |  |  +--%s' %name
            pass
    except IOError:
        with open(dst, 'wb') as handle:
            print '['+colors.OKGREEN+'save'+colors.ENDC+'] |  |  +--%s' %name
            r = session.get(url)
            soup = BeautifulSoup(r.text, 'html.parser')
            link = soup.find(class_='region-content').a['href']
            try:
                handle.write(u'<a href="' + link.decode('utf-8') + u'">' + name.decode('utf-8') + u'</a>')
            except UnicodeEncodeError:
                os.remove(dst)
                print '['+colors.FAIL+'fail'+colors.ENDC+'] |  |  +--%s' %name
                pass


def saveInfo(path, info, tab):
    if "Foren" not in info:
        global files
        files.next()
        name = u'info.txt'
        dst = path + name
        try:
            with open(dst):
                print '['+colors.OKBLUE+'skip'+colors.ENDC+'] ' + tab + '+--%s' %name
                pass
        except IOError:
            with open(dst, 'wb') as handle:
                print '['+colors.OKGREEN+'save'+colors.ENDC+'] ' + tab + '+--%s' %name
                handle.write(info.encode('utf-8'))


def downloadResource(session, res, path):
    try:
        src = res.a['href']
    except TypeError:
        return
    r = session.get(src)
    if(r.status_code == 200):
        headers = r.headers.keys()
        if ('content-disposition' in headers):
            #got a direct file link
            name = r.headers['content-disposition'].decode('utf-8').split(';')[1].split('=')[1].strip('"')
        else:
            #got a preview page
            soup = BeautifulSoup(r.text, 'html.parser')
            if ('content-type' in headers) and ('content-script-type' in headers) and ('content-style-type' in headers):
                #it's most obviously a website, which displays a download link
                src = soup.find(class_='region-content').a['href']
            else:
                #it's obviously an ugly frameset site
                src = soup.find_all('frame')[1]['src']
            name = os.path.basename(src)
        name = urllib.url2pathname(name.encode('utf-8'))
        saveFile(session, src, path, name)
    else:
        print 'ERROR: ' + str(r.status) + ' ' + r.reason
	sys.exit()


def downloadSection(session, s, path):
    #print "download Section"
    global sections
    if s['id'] == 'section-0':
        try:
            info = s.find(class_='activity label modtype_label ').get_text()
        except AttributeError:
            pass
        else:
            saveInfo(path, info, u'')

        res = s.find_all(class_='activity resource modtype_resource ')
        for r in res:
            downloadResource(session, r, path)
        folders = s.find_all(class_='box generalbox foldertree')
        root = path
        for f in folders:
            res = f.find_all(class_='fp-filename-icon')
            label = res.pop(0).text
            path = root + u'/' + label.replace('/', '-')
            path = urllib.url2pathname(path.encode('utf-8'))
            if not os.path.exists(path):
                os.makedirs(path)
            print '       |  +--' + colors.BOLD + label + colors.ENDC
            for r in res:
                downloadResource(session, r, path + u'/')

    else:
        sections.next()
        s = list(s.children)[2]
        name = s.find(class_='sectionname').contents[0].replace('/', '-').strip().strip(':') + '/'
        info = ''
        info = s.find(class_='summary').get_text().strip()
        if len(info) > 0:
            if 'Thema' in name:
                #prof failed to add a proper section name <.<
                temp = info.split('\n')
                name = temp.pop(0).strip().strip(':').replace('/', '-')
                info = "\n".join(temp)
        root = path
        path = root + name.encode('utf-8') + '/'
        if not os.path.exists(path):
            try:
                os.makedirs(path)
            except OSError:
                #filename too long
                name = name.split(':')[0]
                path = root + name + '/'
                if not os.path.exists(path):
                    os.makedirs(path)
        print '       |  +--' + colors.BOLD + name + colors.ENDC

        if len(info) > 0:
            saveInfo(path, info, u'|  ')

        res = s.find_all(class_='activity resource modtype_resource ')
        for r in res:
            downloadResource(session, r, path)
        """
        links = s.find_all(class_='activity url modtype_url ')
        for l in links:
            ln = l.find(class_='instancename')
            ln.span.extract()
            saveLink(session, l.a['href'], path, ln.get_text())
        """

        #remove empty folders
        if os.listdir(path) == []:
            os.rmdir(path)


def downloadCourse(session, c, sem):
    global files
    global sections
    files = itertools.count()
    sections = itertools.count()
    name = c['key'].replace('/', '-') + u'/'
    path = root + sem.replace('/', '-') + u'/' + name
    path = urllib.url2pathname(path.encode('utf-8'))
    if not os.path.exists(path):
        os.makedirs(path)
    print '       +--' + colors.BOLD + name + colors.ENDC
    r = session.get(c['url'])
    if(r.status_code == 200):
        soup = BeautifulSoup(r.text, 'html.parser')
        if not os.path.exists(path + '.dump'):
            os.makedirs(path + '.dump')

        with open(path + '.dump/' + c['key'].replace('/', '-').encode('utf-8') + '-' + c['type'] + '-' + str(datetime.date.today()) + '-full.html', 'wb') as f:
            f.write(soup.encode('utf-8'))
        for s in soup.find_all(class_='section main clearfix'):
            downloadSection(session, s, path)
        #print 'Saved ' + str(files.next()) + ' Files in ' + str(sections.next()) + ' Sections'
    else:
        print 'ERROR: ' + str(r.status) + ' ' + r.reason
        sys.exit()




print colors.HEADER
print "      _____                    .___.__              "
print "     /     \   ____   ____   __| _/|  |   ____      "
print "    /  \ /  \ /  _ \ /  _ \ / __ | |  | _/ __ \     "
print "   /    Y    (  <_> |  <_> ) /_/ | |  |_\  ___/     "
print "   \____|__  /\____/ \____/\____ | |____/\___  >    "
print "           \/                   \/           \/     "
print "  _________                                         "
print " /   _____/ ________________  ______   ___________  "
print " \_____  \_/ ___\_  __ \__  \ \____ \_/ __ \_  __ \ "
print " /        \  \___|  | \// __ \|  |_> >  ___/|  | \/ "
print "/_______  /\___  >__|  (____  /   __/ \___  >__|    "
print "        \/     \/           \/|__|        \/        "
print colors.ENDC

#logging in
print "logging in..."
session = login(username, password)

#get semesters
print "getting Semesters..."
sems = getSemesters(session)
if not sems:
    print colors.FAIL + 'No semester found - Quitting!' + colors.ENDC
    sys.exit()
else:
    print colors.WARNING + 'Available semester:' + colors.ENDC
    for s in sorted(sems):
        print '[' + s + ']: ' + sems[s]

#input loop
ok = False
while not ok:
    s = raw_input(colors.WARNING + 'Select semester: ' + colors.ENDC)
    ok = s in sems.keys()

#get courses
print "getting Courses..."
courses = getCoursesForSem(session, s)
if not courses:
    print colors.FAIL + 'No courses in this semester - Quitting!' + colors.ENDC
    sys.exit()
else:
    print colors.WARNING + 'Available courses:' + colors.ENDC
    for c in courses:
        print '[' + str(courses.index(c)) + ']: ' + c['key'] + '.' + str(c['sem']) + ': ' + c['name'] + ' (' + c['type'] + ')'

#confirmation
c = raw_input(colors.WARNING + 'Choose number of course to download, (a) for all or (q) to quit: ' + colors.ENDC)
if c == 'a':
    for f in courses:
        try:
            downloadCourse(session, f, sems[s])
            print colors.WARNING + 'Successfully processed ' + str(files.next()) + ' Files in ' + str(sections.next()) + ' Sections!' + colors.ENDC
        except:
            print "Error while processing!"
    quit()

if c == 'q':
    print colors.FAIL + 'Oh no? - Quitting!' + colors.ENDC
    quit()

downloadCourse(session, courses.pop(int(c)), sems[s])
print colors.WARNING + 'Successfully processed ' + str(files.next()) + ' Files in ' + str(sections.next()) + ' Sections!' + colors.ENDC
