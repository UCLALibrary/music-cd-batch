# voyager-local-music-cd
Programs for Music CD batch processing

### Usage (preliminary internal notes)
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

