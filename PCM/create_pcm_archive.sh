#!/bin/sh
# adapted version of the script taken from https://github.com/Bouni/kicad-jlcpcb-tools/blob/main/PCM/create_pcm_archive.sh
# heavily inspired by https://github.com/4ms/4ms-kicad-lib/blob/master/PCM/make_archive.sh

VERSION=$1

echo "Clean up old files"
rm -f PCM/*.zip
rm -rf PCM/archive


echo "Create folder structure for ZIP"
mkdir -p PCM/archive/resources

echo "Copy files to destination"
cp VERSION PCM/archive
cp -r plugins PCM/archive
cp PCM/icon.png PCM/archive/resources
cp PCM/metadata.template.json PCM/archive/metadata.json

echo "Write version info to file"
echo $VERSION > PCM/archive/VERSION

echo "Modify archive metadata.json"
sed -i "s/VERSION_HERE/$VERSION/g" PCM/archive/metadata.json
sed -i -E '/\"kicad_version\": \"[0-9]+\.[0-9]\",/ s/.$//g' PCM/archive/metadata.json
sed -i "/SHA256_HERE/d" PCM/archive/metadata.json
sed -i "/DOWNLOAD_SIZE_HERE/d" PCM/archive/metadata.json
sed -i "/DOWNLOAD_URL_HERE/d" PCM/archive/metadata.json
sed -i "/INSTALL_SIZE_HERE/d" PCM/archive/metadata.json

echo "Zip PCM archive"
cd PCM/archive
zip -r ../KiCAD-PCM-$VERSION.zip .
cd ../..

echo "Gather data for repo rebuild"
echo VERSION=$VERSION >> $GITHUB_ENV
echo DOWNLOAD_SHA256=$(shasum --algorithm 256 PCM/KiCAD-PCM-$VERSION.zip | xargs | cut -d' ' -f1) >> $GITHUB_ENV
echo DOWNLOAD_SIZE=$(ls -l PCM/KiCAD-PCM-$VERSION.zip | xargs | cut -d' ' -f5) >> $GITHUB_ENV
echo DOWNLOAD_URL="https:\/\/github.com\/ebastler\/connect-traces\/releases\/download\/$VERSION\/KiCAD-PCM-$VERSION.zip" >> $GITHUB_ENV
echo INSTALL_SIZE=$(unzip -l PCM/KiCAD-PCM-$VERSION.zip | tail -1 | xargs | cut -d' ' -f1) >> $GITHUB_ENV
echo KICAD_VERSION=$(grep -oP '(?<="kicad_version": ")[^"]*' PCM/metadata.template.json) >> $GITHUB_ENV
echo PROJECT_NAME=$(grep name PCM/metadata.template.json | head -1 | grep -oP '(?<="name": ")[^"]*') >> $GITHUB_ENV
