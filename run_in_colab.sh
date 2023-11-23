#!/bin/bash

# Check for required arguments
if [ "$#" -lt 1 ]; then
    echo "Usage: $0 [OPTIONS]... FILE_ID"
    exit 1
fi

# Function to install necessary packages
install_packages() {
    sudo apt-get -q -y update > /dev/null 2>&1
    sudo apt-get -q -y install poppler-utils timidity lame > /dev/null 2>&1
    # Install Microsoft fonts
    echo ttf-mscorefonts-installer msttcorefonts/accepted-mscorefonts-eula select true | sudo debconf-set-selections
    sudo apt-get -q -y install ttf-mscorefonts-installer > /dev/null 2>&1
    wget -q -O /tmp/arial-unicode-ms.zip "https://cofonts.com/download/Arial-Unicode-MS-Font"
    sudo unzip -q /tmp/arial-unicode-ms.zip -d /usr/share/fonts/truetype
    sudo fc-cache -f
    rm -f /tmp/arial-unicode-ms.zip
    pip install -q pdf2image pydub
    wget -q -O - https://gitlab.com/lilypond/lilypond/-/releases/v2.24.3/downloads/lilypond-2.24.3-linux-x86_64.tar.gz | \
        sudo tar -f - -xz -C /usr/local --strip-components=1
    wget -q https://github.com/musescore/MuseScore/releases/download/v4.1.1/MuseScore-4.1.1.232071203-x86_64.AppImage
    sudo mv MuseScore-4.1.1.232071203-x86_64.AppImage /usr/local/bin/mscore
    sudo chmod a+x /usr/local/bin/mscore
}

# Create MuseScore configuration file
mkdir -p ~/.config/MuseScore
cat > ~/.config/MuseScore/MuseScore4.ini << 'EOF'
[application]
[application.playback]
metronomeEnabled=true
EOF

# Create the Python module
cat > colab_utils.py << 'EOF'
import glob
import os
from pdf2image import convert_from_path
import shutil
from google.colab import drive

def convert_pdf_to_images():
    # Find the first .ly file in the current directory
    ly_files = glob.glob("./*.ly")
    if not ly_files:
        raise FileNotFoundError("No .ly files found in the current directory.")

    # Get path of the first .ly file
    ly_path = ly_files[0]

    # Extract basename without extension
    base_name = os.path.splitext(os.path.basename(ly_path))[0]

    # Convert the PDF file into images
    images = convert_from_path(f'{base_name}.pdf')

    return images, base_name

def copy_files_to_gdrive(base_name, dest_dir):
    # Check if destination directory exists, create if it doesn't
    if not os.path.exists(dest_dir):
        os.makedirs(dest_dir)

    # Construct the source and destination file paths for the PDF, MIDI, and MP3 files and copy them
    for ext in ['.pdf', '.midi', '.mp3']:
        file = f'{base_name}{ext}'
        src_file = os.path.join('.', file)
        dest_file = os.path.join(dest_dir, file)
        shutil.copy(src_file, dest_file)
        print(f'File "{file}" has been copied to "{dest_dir}" in Google Drive.')

    print('Go to https://drive.google.com/drive/my-drive and navigate to the `tmp` folder to access the files.')

def mount_google_drive():
    drive.mount('/content/drive', force_remount=True)
EOF

# Check if mscore is installed
if ! command -v mscore &> /dev/null; then
    echo 'Installing necessary packages...'
    install_packages
    echo 'Done'
fi

# Download the jianpu2ly.py script
wget -q -O jianpu2ly.py https://raw.githubusercontent.com/xmjiao/jianpu2ly/master/jianpu2ly.py

# Remove existing .ly files
rm -f *.ly

# Run the script to obtain the PDF, MIDI, and MP3 files
QT_QPA_PLATFORM=offscreen python ./jianpu2ly.py -M -g "$@"
