#!/bin/bash

# variable initialization
compressedFileName=tmp/sealion-agent.tar.gz
compressedFileFolder=tmp/
folderPath=../sealion-agent/
outputFile=../release/sealion-agent.sh
installerFile=sealion-install.sh.in
ignoreFile=.tarignore
tagName="SEALION_TARFILE:"

# make tmp directory
mkdir -p tmp

# compress file
echo "Sealion Packager: Compressing file..."
    tar -czf $compressedFileName $folderPath -X $ignoreFile --exclude-vcs --exclude-backups
echo "Sealion Packager: File successfully compressed"

echo "Sealion Packager: Generating installer..."
    sed \
        -e 's/binary=./binary=1/'\
            $installerFile >$outputFile
    echo $tagName >>$outputFile
    cat $compressedFileName >>$outputFile
echo "Sealion Packager: Installer generated"

# delete tmp files
echo "Sealion Packager: Deleting temperory files..."
    rm -r $compressedFileFolder
    echo "Sealion Packager: Temprory files deleted"
echo "Sealion Packager: Done!!!"