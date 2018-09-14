#!/bin/sh

if [ -z "$1" ]; then
  echo "Usage: $0 upc_file"
  exit 1
fi

IN_FILE="$1"
# for DUP in `awk -F'\t' '{print $3}' batch_007_20180911.lst | sort | uniq -d`; do grep $DUP batch_007_20180911.lst; done

for BARCODE in `awk -F'\t' '{print $3}' ${IN_FILE} | sort | uniq -d`; do 
  echo "Duplicate barcode: ${BARCODE}"
  grep ${BARCODE} ${IN_FILE}
done
