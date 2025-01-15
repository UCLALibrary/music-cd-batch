# music-cd-batch
Programs for Music CD batch processing

# Developer Information

## Build (first time) / rebuild (as needed)

`docker compose build`

This builds a Docker image, `music-cd-batch-batchcd:latest`, which can be used for developing, testing, and running code.

## Dev container

This project comes with a basic dev container definition, in `.devcontainer/devcontainer.json`. It's known to work with VS Code,
and may work with other IDEs like PyCharm.  For VS Code, it also installs the Python, Black (formatter), and Flake8 (linter)
extensions.

The project's directory is available within the container at `/home/batchcd/process_files`.

### Rebuilding the dev container

VS Code builds its own container from the base image. This container may not always get rebuilt when the base image is rebuilt
(e.g., if packages are changed via `requirements.txt`).

If needed, rebuild the dev container by:
1. Close VS Code and wait several seconds for the dev container to shut down (check via `docker ps`).
2. Delete the dev container.
   1. `docker images | grep vsc-music` # vsc-music-cd-batch-LONG_HEX_STRING-uid
   2. `docker image rm -f vsc-music-cd-batch-LONG_HEX_STRING-uid`
3. Start VS Code as usual.

## Running code

Running code from a VS Code terminal within the dev container should just work, e.g.: `python make_music_records.py` (or whatever the specific program is).

Otherwise, run a program via docker compose.  From the project directory:

```
# Open a shell in the container
$ docker compose run batchcd bash

# Open a Python shell in the container
$ docker compose run batchcd python

# Run the program against a full file of data
$ docker compose run batchcd python make_music_records.py batch_016_20240229.tsv

# Run the program against a file of data, starting with record 5 and ending with record 10
$ docker compose run batchcd python make_music_records.py -s 5 -e 10 batch_016_20240229.tsv
```

Some data sources require API keys. Get a copy of `api_keys.py` from a teammate and put it in the top level directory of the project.

### Input and General Flow

The program requires a tab-delimited file with one header row, with column names:
- UPC
- call number
- barcode
- title

The data rows are provided by Music library staff. They transcribe the UPC and title from each CD, then add a local call number and barcode.

The program searches Worldcat, Discogs, and MusicBrainz for each UPC.  If no usable Worldcat records are found via a "standard number" search by UPC,
the program obtains catalog numbers from Discogs and MusicBrainz for the UPC and then searches Worldcat again, this time using the
"music publisher number" index, for each catalog number found.

As a sanity check, the "official" title provided for each CD by Music library staff is compared with titles from records found in the above sources.
Worldcat records are only used when titles are similar enough, to reduce false positive matches.

#### Command-line arguments

```
make_music_records.py [-h] [-s START_INDEX] [-e END_INDEX] [--log-level {DEBUG,INFO,WARNING,ERROR,CRITICAL}] music_data_file
```

### Output

Given an input file `batch_016_20240229.tsv`, the program will generate a log file and up to two files of MARC records.
- Log file: `batch_016_20240229.log`: Contains details about each search, evaluation of data found, and more.
- MARC file: `batch_016_20240229_oclc.mrc`: Contains the "best" OCLC Worldcat record found (if any) for each search term.
- MARC file: `batch_016_20240229_orig.mrc`: Contains minimal records created from Discogs or MusicBrainz data, if no usable Worldcat record was found.

Log files and MARC files are appended to, if the program is run multiple times with the same input file. This allows for resuming an
interrupted run.  Be sure there's no overlap, or MARC files could contain duplicate records.

### Testing

Tests focus on code which has significant side effects or implements custom logic.
Run tests in the container:

```$ docker compose run batchcd python -m unittest discover -s tests```


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
