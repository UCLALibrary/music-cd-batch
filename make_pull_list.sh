#!/bin/sh

if [ -z "$1" ]; then
  echo "Usage: $0 logfile"
  exit 1
fi

IN_FILE="$1"
# Assumes logfile has a .log extension, which I've been using
PULL_LIST=`basename ${IN_FILE} .log`_PULL.txt

# Generate the full pull list
egrep "Pull CD|REVIEW" ${IN_FILE} > ${PULL_LIST}

# Add counts of specific types
HELD_CNT=`grep "held by CLU" ${PULL_LIST} | wc -l`
NONE_CNT=`grep "no record created" ${PULL_LIST} | wc -l`
ORIG_CNT=`grep "original created" ${PULL_LIST} | wc -l`
WARN_CNT=`grep "MARC warning" ${PULL_LIST} | wc -l`
TOTAL=`expr ${HELD_CNT} + ${NONE_CNT} + ${ORIG_CNT} + ${WARN_CNT}`

# Append counts to the pull list
printf "\n" >> ${PULL_LIST}
printf "%3d\tHeld by CLU\n" ${HELD_CNT} >> ${PULL_LIST}
printf "%3d\tNo record created\n" ${NONE_CNT} >> ${PULL_LIST}
printf "%3d\tOriginal record created\n" ${ORIG_CNT} >> ${PULL_LIST}
printf "%3d\tOCLC records with warnings\n" ${WARN_CNT} >> ${PULL_LIST}
printf "%3d\tTotal to pull\n" ${TOTAL} >> ${PULL_LIST}

tail -5 ${PULL_LIST}

# Display MARC counts, for convenience, but don't add to the pull list
for MRC in *.mrc; do python marc_count.py $MRC; done
