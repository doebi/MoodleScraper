from requests import session
from bs4 import BeautifulSoup
import os, sys, itertools
import urllib
import ConfigParser

config = ConfigParser.RawConfigParser()
config.read('scraper.conf')
conf = dict(config.items('scraper'))

sections = itertools.count()
files = itertools.count()

class colors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'

def login(user, pwd):
    authdata = {
        'action': 'login',
        'username': user,
        'password': pwd
    }
    with session() as ses:
        r = ses.post(conf['baseurl'] + 'login/index.php', data=authdata)
        return ses


def getSemesters(ses):
    r = ses.get(conf['baseurl'] + 'index.php')

    if(r.status_code == 200):
        soup = BeautifulSoup(r.text)
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
    q = p[0].split('.')
    c['course'] = q[0].strip()
    c['sem'] = q[1]
    c['key'] = q[2].strip()
    c['name'] = p[1].strip()
    c['type'] = p[2].strip().replace(' ', '-')
    return c


def getCoursesForSem(session, s):
    r = session.get(conf['baseurl'] + 'index.php?role=0&cat=1&stg='+ conf['stg'] +'&csem=1&sem=' + s)
    if(r.status_code == 200):
        soup = BeautifulSoup(r.text)
        courses = list()
        for o in soup.find_all('h3'):
            c = getInfo(o.contents[0])
            courses.append(c)
        return courses
    else:
        print 'ERROR: ' + str(r.status) + ' ' + r.reason
	sys.exit()


def saveFile(session, src, path, name):
    global files
    files.next()
    dst = path + name.decode('utf-8')

    try:
        with open(dst):
            print '|  |  +--{:<50s}'.format(name) + '['+colors.OKBLUE+'skipped'+colors.ENDC+']'
            pass
    except IOError:
        with open(dst, 'wb') as handle:
            print '|  |  +--{:<50s}'.format(name) + '['+colors.OKGREEN+'downloading'+colors.ENDC+']'
            r = session.get(src, stream=True)
            for block in r.iter_content(1024):
                if not block:
                    break
                handle.write(block)


def saveLink(session, url, path, name):
    fname = name + '.html'
    dst = path + fname
    try:
        with open(dst):
            print u'|  |  +--{:<50s}'.format(fname) + u'['+colors.OKBLUE+'skipped'+colors.ENDC+']'
            pass
    except IOError:
        with open(dst, 'wb') as handle:
            print u'|  |  +--{:<50s}'.format(fname) + u'['+colors.OKGREEN+'saving'+colors.ENDC+']'
            r = session.get(url)
            soup = BeautifulSoup(r.text)
            link = soup.find(class_='region-content').a['href']
            handle.write(u'<a href="' + link + u'">' + name + u'</a>')


def saveInfo(path, info, tab):
    name = u'info.txt'
    dst = path + name
    try:
        with open(dst):
            print tab + u'|  +--{:<50s}'.format(name) + u'['+colors.OKBLUE+'skipped'+colors.ENDC+']'
            pass
    except IOError:
        with open(dst, 'wb') as handle:
            print tab + u'|  +--{:<50s}'.format(name) + u'['+colors.OKGREEN+'saving'+colors.ENDC+']'
            handle.write(info.encode('utf-8'))


def downloadResource(session, res, path):
    src = res.a['href']
    r = session.get(src)
    if(r.status_code == 200):
        headers = r.headers.keys()
        if ('content-disposition' in headers):
            #got a direct file link
            name = r.headers['content-disposition'].decode('utf-8').split(';')[1].split('=')[1].strip('"')
        else:
            #got a preview page
            soup = BeautifulSoup(r.text)
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
    global sections
    if s['id'] == 'section-0':
        try:
            info = s.find(class_='activity label modtype_label ').get_text()
        except AttributeError:
            print u'{:<50s}'.format(u'No info found! Your Prof is probably too lazy.') + u'['+colors.WARNING+'skipped'+colors.ENDC+']'
        else:
            saveInfo(path, info, u'')

    else:
        sections.next()
        s = list(s.children)[2]
        name = s.find(class_='sectionname').contents[0].replace('/', '-').strip() + '/'
        path += name
        print '|  +--' + name
        if not os.path.exists(path):
            os.makedirs(path)
        try:
            info = s.find(class_='summary').get_text()
        except AttributeError:
            print u'{:<53s}'.format(u'|  +--No info found! Your Prof is probably too lazy.') + u'['+colors.WARNING+'skipped'+colors.ENDC+']'
        else:
            saveInfo(path, info, u'|  ')
        res = s.find_all(class_='activity resource modtype_resource ')
        for r in res:
            downloadResource(session, r, path)
        links = s.find_all(class_='activity url modtype_url ')
        for l in links:
            ln = l.find(class_='instancename')
            ln.span.extract()
            saveLink(session, l.a['href'], path, ln.get_text())


def downloadCourse(session, c, sem):
    global files
    global sections
    files = itertools.count()
    sections = itertools.count()
    name = c['key'].replace('/', '-') + u'/'
    path = conf['root'] + sem.replace('/', '-') + u'/' + name
    path = urllib.url2pathname(path.encode('utf-8'))
    #TODO: secure pathnames
    if not os.path.exists(path):
        os.makedirs(path)
    print '+--' + name
    r = session.get(c['url'])
    if(r.status_code == 200):
        soup = BeautifulSoup(r.text)
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
session = login(conf['user'], conf['pwd'])

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
        print c['key'] + '.' + str(c['sem']) + ': ' + c['name'] + ' (' + c['type'] + ')'

#confirmation
c = raw_input(colors.WARNING + 'Proceed with downloading all courses? (y)' + colors.ENDC)
if c == 'y':
    for f in courses:
        downloadCourse(session, f, sems[s])
        print colors.WARNING + 'Successfully processed ' + str(files.next()) + ' Files in ' + str(sections.next()) + ' Sections!' + colors.ENDC
else:
    print colors.FAIL + 'Oh no? - Quitting!' + colors.ENDC
