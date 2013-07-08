from requests import session
from bs4 import BeautifulSoup
import os, sys, itertools

#======= CONFIG =======#
#your user name
user = 'myuser'
#your password
pwd = 'super-secrept-password'
#path where you want to save your scraped data
root = 'mydata/'
#url of your moodle setup
baseurl = 'http://moodle.school.tld/'
#name of your course
stg = 'SEv'
#======= CONFIG =======#



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
        r = ses.post(baseurl + 'login/index.php', data=authdata)
        return ses


def getSemesters(ses):
    r = ses.get(baseurl + 'index.php')

    if(r.status_code == 200):
        soup = BeautifulSoup(r.text)
        semesters = dict()
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
    r = session.get(baseurl + 'index.php?role=0&cat=1&stg='+ stg +'&csem=1&sem=' + s)
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
    dst = path + name
    try:
        with open(dst):
            print u'|  |  +--{:<50s}'.format(name) + u'['+colors.OKBLUE+'skipped'+colors.ENDC+']'
            pass
    except IOError:
        with open(dst, 'wb') as handle:
            print u'|  |  +--{:<50s}'.format(name) + u'['+colors.OKGREEN+'downloading'+colors.ENDC+']'
            r = session.get(src, stream=True)
            for block in r.iter_content(1024):
                if not block:
                    break
                handle.write(block)


def downloadResource(session, res, path):
    src = res.a['href']
    r = session.get(src)
    if(r.status_code == 200):
        headers = r.headers.keys()
        if ('content-disposition' in headers):
            name = r.headers['content-disposition'].decode('utf-8').split(';')[1].split('=')[1].strip('"')
        else:
            soup = BeautifulSoup(r.text)
            if ('content-type' in headers) and ('content-script-type' in headers) and ('content-style-type' in headers):
                src = soup.find(class_='region-content').a['href']
            else:
                src = soup.find_all('frame')[1]['src']
            name = os.path.basename(src).replace('%20', ' ').replace('%28', '(').replace('%29', ')')
        saveFile(session, src, path, name)
    else:
        print 'ERROR: ' + str(r.status) + ' ' + r.reason
	sys.exit()


def downloadSection(session, s, path):
    global sections
    if s['id'] == 'section-0':
        #TODO: save info as textfile
        a = 2 + 3
    else:
        sections.next()
        s = list(s.children)[2]
        name = s.find(class_='sectionname').contents[0].replace('/', '-') + '/'
        path += name
        print '|  +--' + name
        if not os.path.exists(path):
            os.makedirs(path)
        res = s.find_all(class_='activity resource modtype_resource')
        for r in res:
            downloadResource(session, r, path)



def downloadCourse(session, c, sem):
    global files
    global sections
    files = itertools.count()
    sections = itertools.count()
    name = c['key'].replace('/', '-') + '/'
    path = root + sem.replace('/', '-') + '/' + name
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
session = login(user, pwd)

#get semesters
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
