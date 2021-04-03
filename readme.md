# exif deduplicator
Is a project that is intended to sort out the mess i made on my harddrives. I want to sort 
pictures into a nested folder structure like this `year/month/day/filename.extension` without duplicates.

Since there are currently countless folders on my drives which contain the same files in different folders I 
started out with globbing through a filelist and pushing it to a RabbitMq Queue.

Start by running `docker-compose -f docker-compose.yml up -d` this will start rabbitmq

There is a datafolder in the root of this directory, it contains a source and a target folder, both are mounted as
volumes in the docker-compose files. You should change the volume mappings according to your own wishes. 

The project is split into a couple of steps:
1. sending the file list to the first queue
    * this is done by running `python filelist.py` from within the src directory or
    * by running `make filelist`
   
2. scanning the exifdata for all the files from the filelist
   * done by running `python exifscanner.py` or `make exifscanner`  
3. moving the files based on their original capture time (if available, leaves them untouched in the source folder otherwise)
   * done by running `python filemover.py` or `make filemover`
4. scan the duplicates, files with the same filename (and inherentlcy the same capturedate) will be scanned for likeness.
   * exact duplicates will be posted to a seperate queue for the next process
   * start using `python duplicate_scanner.py` or `make duplicate-scanner`
5. remove duplicates, *originals will be removed* in this step
   * start using `python duplicate_remover.py` or `make duplicate-remover`
