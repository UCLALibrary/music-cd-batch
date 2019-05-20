# voyager-local-music-cd
Programs for Music CD batch processing

### Usage (preliminary internal notes)
1. Copy/paste data from Google sheet prepared by music library.  Make sure all lines make it - vi deletes some with special characters.
2. Data should be in file named this: batch_012_20181019.lst
3. Check for duplicate barcodes: ./find_dup_barcodes.sh upc_file.lst
4. If all clear: nohup ./get_music_data.pl upc_file.lst |& tee upc_file.out
