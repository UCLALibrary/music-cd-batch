# music-cd-batch
Programs for Music CD batch processing

## Developer Information

### Overview of environment

The development environment requires:
* git (at least version 2)
* docker (current version recommended: 20.10.12)
* docker-compose (at least version 1.25.0; current recommended: 1.29.2)

#### Docker container

This uses Debian 11 (Bullseye) in a Docker container running Python 3.11.  All code
runs in the container, so local version of Python does not matter.  All Python packages
are installed in the container.

### Setup

1. Build using docker-compose.

   ```$ docker-compose build```

2. Bring the system up, with container running in the background.

   ```$ docker-compose up -d```

3. Run commands in the container.

   ```
   # Open a shell in the container
   $ docker-compose exec batchcd bash

   # Open a Python shell in the container
   $ docker-compose exec batchcd python
   
   # Run the program (TODO: Update program name(s))
   $ docker-compose exec batchcd python search_worldcat.py batch_016_20240229.tsv
   ```

### Testing

Tests focus on code which has significant side effects or implements custom logic.
Run tests in the container:

```$ docker-compose exec batchcd python -m unittest discover -s tests```


## Usage (OBSOLETE: internal notes from old process, to be kept / edited later)
1. Copy/paste data from Google sheet prepared by music library.  Make sure all lines make it - vi deletes some with special characters.
2. Data should be in file named like this, same as the sheet of data used: batch_012_20181019.lst
3. Check for duplicate barcodes: ./find_dup_barcodes.sh upc_file.lst
4. If all clear: nohup ./get_music_data.pl upc_file.lst |& tee upc_file.out
5. Once done: ./make_pull_list.sh upc_file.out
6. Log into BatchCat PC and go to the UCLA_Loader directory.
7. Run: get_meher.bat (retrieve batch* from server)
8. Run: load_generic.bat with the oclc.mrc file
9. Run: check_meher_log.bat on the log file from the load in the previous step
10. Put all in K:\WorkGroups\Meher CDs\
11. On the server: Move batch* done/
