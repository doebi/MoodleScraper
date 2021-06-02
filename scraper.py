#!/usr/bin/env python2
from requests import session
from bs4 import BeautifulSoup
import os, sys
import configparser as ConfigParser
import datetime
import json
import urllib
import zipfile


ERROR_LOGIN = 'Error on Login'
ERROR_LINK = 'Link provided is wrong'

# read config
config = ConfigParser.RawConfigParser()
config.read('scraper.conf')
baseurl = 0
root=''


class colors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    DANGER = '\033[31m'
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

        if r.status_code != 200:
            raise Exception(ERROR_LINK)

        soup = BeautifulSoup(r.text,'html.parser')

        user = soup.select_one('span[class*="userbutton"]')
        if(user!=None):
            return ses
        else:
            raise Exception(ERROR_LOGIN)


def exit_and_save():
    with open('scraper.conf', 'w') as configfile:
       config.write(configfile)
    sys.exit()

#Return a dictionary with the courses and respective links
def getCurrCourses(ses):
    page = ses.get(baseurl + 'index.php')
    soup = BeautifulSoup(page.text, 'html.parser')
    curr_courses = soup.select('div[class*="courses-view-course-item"]')
    result = dict()
    for course in curr_courses:
        tag_h = course.find('h4')
        course_link = tag_h.a['href']
        course_name = tag_h.a.text.replace(' ','_').replace('/', '-')
        result[course_name] = course_link
    
    return result


#Return a list of toupples containing the name and link of resource respectively
def getResources(ses, course_link):
    page = ses.get(course_link)
    soup = BeautifulSoup(page.text, 'html.parser')
    course_div = soup.select('div[class*="course-content"]')[0]
    resources = course_div.select('li[class*="activity resource"] div[class*="activityinstance"] a')
    resource_list = []
    for resource in resources:
        link = resource['href']
        name = resource.span.text
        resource_list.append((name,link))
    return resource_list





def saveFile(session, src, path, name):
    dst = path + name
    dst = dst.replace(':', '-').replace('"', '')


    try:
        with open(dst):
            print('['+colors.OKBLUE+'skip'+colors.ENDC+'] |  |  +--%s' %name)
            pass
    except IOError:
        with open(dst, 'wb') as handle:
            print('['+colors.OKGREEN+'save'+colors.ENDC+'] |  |  +--%s' %name)
            r = session.get(src, stream=True)
            for block in r.iter_content(1024):
                if not block:
                    break
                handle.write(block)


def saveLink(session, url, path, name):
    #global files
    #files.next()
    fname = name.replace('/', '') + '.html'
    dst = path + fname
    dst = dst.replace(':', '-').replace('"', '')
    try:
        with open(dst):
            print('['+colors.OKBLUE+'skip'+colors.ENDC+'] |  |  +--%s' %name)
            pass
    except IOError:
        with open(dst, 'wb') as handle:
            print('['+colors.OKGREEN+'save'+colors.ENDC+'] |  |  +--%s' %name)
            r = session.get(url)
            soup = BeautifulSoup(r.text, 'html.parser')
            link = soup.find(class_='region-content').a['href']
            try:
                handle.write(u'<a href="' + link.decode('utf-8') + u'">' + name.decode('utf-8') + u'</a>')
            except UnicodeEncodeError:
                os.remove(dst)
                print('['+colors.FAIL+'fail'+colors.ENDC+'] |  |  +--%s' %name)
                pass


def saveInfo(path, info, tab):
    if "Foren" not in info:
        #global files
        #files.next()
        name = u'info.txt'
        dst = path + name
        dst = dst.replace(':', '-').replace('"', '')
        try:
            with open(dst):
                print('['+colors.OKBLUE+'skip'+colors.ENDC+'] ',tab,'+--%s' %name)
                pass
        except IOError:
            with open(dst, 'wb') as handle:
                print('['+colors.OKGREEN+'save'+colors.ENDC+'] ',tab,'+--%s' %name)
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
            name = r.headers['content-disposition'].split(';')[1].split('=')[1].strip('"')
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
        name = urllib.request.url2pathname(name)
        saveFile(session, src, path, name)
    else:
        print(('ERROR: ',str(r.status),' ',r.reason))
    #sys.exit()

def downloadExtract(session, res, path):
    try:
        src = res.a['href']
    except TypeError:
        return
    page_download = session.get(src)
    if(page_download.status_code == 200):
        soup = BeautifulSoup(page_download.text, 'html.parser')
        button_div= soup.find(class_='box generalbox folderbuttons py-3')
        id_input = button_div.find('input', {'name': 'id'}).get('value')
        session_input = button_div.find('input', {'name': 'sesskey'}).get('value')
        form_link = button_div.find('form').get('action')
        args = {'id':id_input,'sesskey':session_input}
        #print(id_input,session_input,form_link)

        resource = session.post(form_link,data=args)
        final_path = path+"the.zip"
        with open(final_path, 'wb') as handle:
            handle.write(resource.content)

        zip_ref = zipfile.ZipFile(final_path)
        zip_ref.extractall(path)
        zip_ref.close()
        os.remove(final_path)
        #saveFile(session, resource.content, path, "the.zip")
    else:
        print(('ERROR: ',str(page_download.status),' ',page_download.reason))

#def downloadFolder(session, res, path):
#    try:
#        src = res.a['href']
#    except TypeError:
#        return
#    page_download = session.get(src)
#    if(page_download.status_code == 200):
#        soup = BeautifulSoup(page_download.text, 'html.parser')
#        folders = soup.find_all(class_='box generalbox foldertree py-3')
#        print(len(folders))
#        for f in folders:
#            downloadResource(session, f, path)
#    else:
#        print(('ERROR: ',str(page_download.status),' ',page_download.reason))

def downloadSection(session, s, path):
    #print("download Section")
    if s['id'] == 'section-0':
        try:
            info = s.find(class_='activity label modtype_label ').get_text()
        except AttributeError:
            pass
        else:
            saveInfo(path, info, u'')
        
        res = s.select('[class*="activity resource modtype_resource"]')
        for r in res:
            downloadResource(session, r, path)

        folders = s.find_all(class_='activity folder modtype_folder')
        root = path
        for f in folders:
            res = f.find_all(class_='instancename')
            label = str(res.pop(0).contents[0])#.text
            path = root + '/' + label.replace('/', '-')
            path = path.replace(':', '-').replace('"', '').replace(' ','_')
            if not os.path.exists(path):
                os.makedirs(path)
            print('       |  +--',colors.BOLD,label,colors.ENDC)
            downloadExtract(session, f, path + '/')

    else:
        #s = list(s.children)[2]
        name = s.find(class_='sectionname').contents[0].replace('/', '-').strip().strip(':') + '/'
        info = s.find(class_='summary').get_text().strip()
        if len(info) > 0:
            if 'Thema' in name:
                #prof failed to add a proper section name <.<
                temp = info.split('\n')
                name = temp.pop(0).strip().strip(':').replace('/', '-')
                info = "\n".join(temp)
        root = path
        path = root + name + '/'
        path = path.replace(':', '-').replace('"', '')
        if not os.path.exists(path):
            try:
                os.makedirs(path)
            except OSError:
                #filename too long
                name = name[:60]
                path = root + name + '/'
                path = path.replace(':', '-').replace('"', '')
                if not os.path.exists(path):
                    os.makedirs(path)
        print('       |  +--',colors.BOLD,name,colors.ENDC)

        if len(info) > 0:
            saveInfo(path, info, u'|  ')

        res = s.select('[class*="activity resource modtype_resource"]')
        for r in res:
            downloadResource(session, r, path)
        """
        links = s.find_all(class_='activity url modtype_url ')
        for l in links:
            ln = l.find(class_='instancename')
            ln.span.extract()
            saveLink(session, l.a['href'], path, ln.get_text())
        """

        folders = s.find_all(class_='activity folder modtype_folder')
        root = path[:-1]
        for f in folders:
            res = f.find_all(class_='instancename')
            label = str(res.pop(0).contents[0])#.text
            path_ = root + label.replace('/', '-').replace(':', '-').replace('"', '').replace(' ','_')
            if not os.path.exists(path_):
                os.makedirs(path_)
            print('       |  +--',colors.BOLD,label,colors.ENDC)
            downloadExtract(session, f, path_ + '/')

        #remove empty folders
        if os.listdir(path) == []:
            os.rmdir(path)


def check_courses_selected(courses):
    if config.has_option('scraper','curses'):
        curses_list = json.loads(config.get("scraper","curses"))
        if(len(curses_list)>0):
            return curses_list
    else:
        curses_list = []
    courses_to_download = enumerate(courses.keys())
    for val,name in courses_to_download:
        print(val,'-',name)

    print('\nType the number of the courses that you want to save for future searches.')
    print('Type one at a time and press enter')
    print('If you want all courses type "a", to finish selection type "q"')

    _input = input()
    while _input != 'q':
        if _input == 'a':
            curses_list = list(courses.keys())
            break
        try:
            input_int = int(_input)
            if(input_int < len(courses)):
                for num,name in enumerate(courses.keys()):
                    #print(name,num)
                    if num == input_int:
                        curses_list.append(name)
                        break
        except:
            None
        
        _input = input()
    
    print(curses_list)
    str_courses = json.dumps(curses_list)
    config.set('scraper','curses',str_courses)

    return curses_list


def check_auth_info():
    global baseurl
    global root
    if config.has_option('scraper','user'):
        username = config.get("scraper", "user")
        
    else:
        print('Please type your username below.')
        username = input()
        config.set('scraper','user',username)

    if config.has_option('scraper','pwd'):
        pwd = config.get("scraper", "pwd")
        
    else:
        print('Please type your password below.',colors.DANGER,'THE PASSWORD WILL BE SAVED AS PLAIN TEXT',colors.ENDC)
        pwd = input()
        config.set('scraper','pwd',pwd)

    if config.has_option('scraper','root'):
        root = config.get("scraper", "root")
    else:
        root = ''

    if config.has_option('scraper','baseurl'):
        baseurl = config.get("scraper", "baseurl")
        
    else:
        print('Please the type the url below.')
        baseurl = input()
        config.set('scraper','baseurl',baseurl)

    session = 0
    try:
        session = login(username, pwd)
    except Exception as e:
        if e.__str__() == ERROR_LINK:
            config.set('scraper','user',username)
            config.set('scraper','pwd',pwd)
            print(colors.DANGER,'Error connecting to website, either the website is unresponsive or the link provided is wrong.',colors.ENDC)
            print(colors.WARNING,'BaseURL:' + baseurl,colors.ENDC)
            print('To change the link, change the property "baseurl" in scraper.conf.')
            exit_and_save()
        elif e.__str__() == ERROR_LOGIN:
            config.remove_option('scraper','user')
            config.remove_option('scraper','pwd')
            config.set('scraper','baseurl',baseurl)
            print(colors.DANGER,'Error on authentication. Either the password or login are wrong.',colors.ENDC)
            return check_auth_info()
        else:
            print(colors.DANGER,'Uknown Error ocurred while loginng in, exiting...')
            sys.exit()
    
    config.set('scraper','root',root)
            
    return session
    


def downloadCourse(session, name_course,link_course):
    name = name_course.replace('/', '-') + u'/'
    path = root + name
    path = path.replace(':', '-').replace('"', '').replace(' ','_')
    if not os.path.exists(path):
        os.makedirs(path)
    print('       +--',colors.BOLD,name,colors.ENDC)
    r = session.get(link_course)
    if(r.status_code == 200):
        soup = BeautifulSoup(r.text, 'html.parser')
        if not os.path.exists(path + '.dump'):
            os.makedirs(path + '.dump')

        dst = path + '.dump/' + name_course.replace('/', '-') + '-' + str(datetime.date.today()) + '-full.html'
        dst = dst.replace(':', '-').replace('"', '')
        
        with open(dst, 'wb') as f:
            f.write(soup.encode('utf-8'))
        for s in soup.find_all(class_='section main clearfix'):
            #test_download_folder(session,s, path)
            downloadSection(session, s, path)

        #print('Saved ',str(files.next()),' Files in ',str(sections.next()),' Sections')
    else:
        print('ERROR: ',str(r.status),' ',r.reason)
        exit_and_save()




print(colors.HEADER)
print("      _____                    .___.__              ")
print("     /     \   ____   ____   __| _/|  |   ____      ")
print("    /  \ /  \ /  _ \ /  _ \ / __ | |  | _/ __ \     ")
print("   /    Y    (  <_> |  <_> ) /_/ | |  |_\  ___/     ")
print("   \____|__  /\____/ \____/\____ | |____/\___  >    ")
print("           \/                   \/           \/     ")
print("  _________                                         ")
print(" /   _____/ ________________  ______   ___________  ")
print(" \_____  \_/ ___\_  __ \__  \ \____ \_/ __ \_  __ \ ")
print(" /        \  \___|  | \// __ \|  |_> >  ___/|  | \/ ")
print("/_______  /\___  >__|  (____  /   __/ \___  >__|    ")
print("        \/     \/           \/|__|        \/        ")
print(colors.ENDC)

#logging in
print("logging in...")
session = check_auth_info()
#exit_and_save()



print("getting Courses...")
courses = getCurrCourses(session)
if len(courses) == 0:
    print(colors.FAIL,'No courses found - Quitting!',colors.ENDC)
    exit_and_save()
#else:
    #print(colors.WARNING,'Available Courses:',colors.ENDC)
    #for name in courses.keys():
        #print('[',name,']: ',courses[name])


curses_list = check_courses_selected(courses)



for name,link in courses.items():
    if name not in curses_list:
        continue
    try:
        downloadCourse(session, name, link)
    except Exception as e:
        print(colors.DANGER,"Error while processing!",colors.ENDC)
        raise e

exit_and_save()

