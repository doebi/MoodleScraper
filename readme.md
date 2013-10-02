```
      _____                    .___.__              
     /     \   ____   ____   __| _/|  |   ____      
    /  \ /  \ /  _ \ /  _ \ / __ | |  | _/ __ \     
   /    Y    (  <_> |  <_> ) /_/ | |  |_\  ___/     
   \____|__  /\____/ \____/\____ | |____/\___  >    
           \/                   \/           \/     
  _________                                         
 /   _____/ ________________  ______   ___________  
 \_____  \_/ ___\_  __ \__  \ \____ \_/ __ \_  __ \ 
 /        \  \___|  | \// __ \|  |_> >  ___/|  | \/ 
/_______  /\___  >__|  (____  /   __/ \___  >__|    
        \/     \/           \/|__|        \/        
```

MoodleScraper is a tool for scraping resources from Moodle.


Description
-----------

This script downloads all resources for your specified moodle instance and saves it in a neat folder structure.

```
+--Semester/
|  +--Class/
|  |  +--Section/
|  |  |  +--Resource.src
```


Prerequisites
-------------

The script uses python-requests and BeautifulSoup4.

```
pip install requests
pip install beautifulSoup4
```

Configuration
-------------

copy scraper.conf.sample to scraper.conf and change all values to your needs
save and enjoy ;)

Usage
-----

```
python scraper.py
```

Follow the Dialog.


Disclaimer
----------

There is no warranty, expressed or implied, associated with this product.
Use at your own risk.
