#!/bin/bash

# Check for required arguments
if [ "$#" -ne 1 ]; then
    echo "Usage: $0 FILE_ID"
    exit 1
fi

FILEID=$1

# Function to install necessary packages
install_packages() {
    sudo apt-get -q -y update > /dev/null 2>&1
    sudo apt-get -q -y install lilypond poppler-utils timidity lame > /dev/null 2>&1
    pip install -q pdf2image pydub
    wget -q https://github.com/musescore/MuseScore/releases/download/v4.1.1/MuseScore-4.1.1.232071203-x86_64.AppImage
    sudo mv MuseScore-4.1.1.232071203-x86_64.AppImage /usr/local/bin/mscore
    sudo chmod a+x /usr/local/bin/mscore

    # Create the Python module
    MODULE_NAME="colab_utils.py"
    cat > $MODULE_NAME << 'EOF'
import os
import shutil
import glob
from google.colab import drive
from IPython.display import display
from pdf2image import convert_from_path

def convert_pdf_to_images(pdf_file):
    images = convert_from_path(pdf_file)
    for img in images:
        display(img)

def copy_files_to_drive(base_name, dest_dir):
    files_to_copy = [f'{base_name}.pdf', f'{base_name}.midi', f'{base_name}.mp3']
    for file in files_to_copy:
        src_file = os.path.join('.', file)
        dest_file = os.path.join(dest_dir, file)
        shutil.copy(src_file, dest_file)
    print(f'Files copied to Google Drive directory: {dest_dir}')

def mount_google_drive():
    drive.mount('/content/drive', force_remount=True)
EOF

    # Notify the user
    echo "The script has completed its tasks. A Python module '$MODULE_NAME' has been created for further processing."
}

# Check if mscore is installed
if ! command -v mscore &> /dev/null; then
    echo 'Installing necessary packages...'
    install_packages
    echo 'Done'
fi

# Download the jianpu-ly.py script
wget -q -O jianpu-ly.py https://raw.githubusercontent.com/xmjiao/jianpu-ly/master/jianpu-ly.py

# Remove existing .ly files
rm -f *.ly

# Run the script to obtain the PDF, MIDI, and MP3 files
QT_QPA_PLATFORM=offscreen python ./jianpu-ly.py -b 1 -M -g ${FILEID}
