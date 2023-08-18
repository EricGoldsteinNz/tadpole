import os
import sys
import shutil
import hashlib
import zipfile
from PyQt5.QtGui import *
from PyQt5.QtCore import *
import struct
import zlib
import frogtool
import requests
import json
import logging


try:
    from PIL import Image
    from PIL import ImageDraw
    image_lib_avail = True
except ImportError:
    Image = None
    ImageDraw = None
    image_lib_avail = False

systems = {  
    "FC":     ["rdbui.tax", "fhcfg.nec", "nethn.bvs",1],
    "SFC":    ["urefs.tax", "adsnt.nec", "xvb6c.bvs",2],
    "MD":     ["scksp.tax", "setxa.nec", "wmiui.bvs",3],
    "GB":     ["vdsdc.tax", "umboa.nec", "qdvd6.bvs",4],
    "GBC":    ["pnpui.tax", "wjere.nec", "mgdel.bvs",5],
    "GBA":    ["vfnet.tax", "htuiw.nec", "sppnp.bvs",6], 
    "ARCADE": ["mswb7.tax", "msdtc.nec", "mfpmp.bvs",7]
}


class Exception_InvalidPath(Exception):
    pass    


class Exception_StopExecution(Exception):
    pass   
    
class InvalidURLError(Exception):
    pass
   
def changeBootLogo(index_path, newLogoFileName):
    # Confirm we arent going to brick the firmware by finding a known version
    bisrvHash = bisrv_getFirmwareVersion(index_path)
    sfVersion = versionDictionary.get(bisrvHash)
    print(f"Found Version: {sfVersion}")
    if sfVersion == None:
        return False  
    # Load the new Logo    
    newLogo = QImage(newLogoFileName)
    # Convert to RGB565
    rgb565Data = QImageToRGB565Logo(newLogo)
    # Change the boot logo
    file_handle = open(index_path, 'rb')  # rb for read, wb for write
    bisrv_content = bytearray(file_handle.read(os.path.getsize(index_path)))
    file_handle.close()
    logoOffset = findSequence(offset_logo_presequence, bisrv_content)
    bootLogoStart = logoOffset + 16
    
    for i in range(0, 512*200):
        data = rgb565Data[i].to_bytes(2, 'little')
        bisrv_content[bootLogoStart+i*2] = data[0]
        bisrv_content[bootLogoStart+i*2+1] = data[1]
    print("Patching CRC")    
    bisrv_content = patchCRC32(bisrv_content)
    print("Writing bisrv to file")
    file_handle = open(index_path, 'wb')  # rb for read, wb for write
    file_handle.write(bisrv_content)    
    file_handle.close()

def patchCRC32(bisrv_content):
    x = crc32mpeg2(bisrv_content[512:len(bisrv_content):1])    
    bisrv_content[0x18c] = x & 255
    bisrv_content[0x18d] = x >> 8 & 255
    bisrv_content[0x18e] = x >> 16 & 255
    bisrv_content[0x18f] = x >> 24
    return bisrv_content

def crc32mpeg2(buf, crc=0xffffffff):
    for val in buf:
        crc ^= val << 24
        for _ in range(8):
            crc = crc << 1 if (crc & 0x80000000) == 0 else (crc << 1) ^ 0x104c11db7
    return crc
     
def QImageToRGB565Logo(inputQImage):
    print("Converting supplied file to boot logo format")
    # Need to increase the size to 512x200
    inputQImage = inputQImage.scaled(512, 200, Qt.IgnoreAspectRatio, Qt.SmoothTransformation)
    inputQImage = inputQImage.convertToFormat(QImage.Format_RGB16)
    rgb565Data = []
    for y in range(0, 200):
        for x in range(0, 512):
            pixel = inputQImage.pixelColor(x,y)
            pxValue = ((pixel.red() & 248) << 8) + ((pixel.green() & 252) << 3) + (pixel.blue() >> 3)
            rgb565Data.append(pxValue)
    print("Finished converting image to boot logo format")
    return rgb565Data   


# hash, versionName
versionDictionary = {
    "031edd7d41651593c5fe5c006fa5752b37fddff7bc4e843aa6af0c950f4b9406": "04.20"
}


def getThumbnailFromZXX(filepath):
    """
    file_handle = open(filepath, 'rb') #rb for read bytes
    zxx_content = bytearray(file_handle.read(os.path.getsize(filepath)))#can probably reduce this to 208*104*2
    file_handle.close()
    thumbnailQImage = QImage()
    for y in range (0, 208):
        for x in range (0, 104):
            #TODO
            intColor = 
            thumbnailQImage.setPixel(x,y,)
            
    return thumbnailQImage"""
    return False


def changeZXXThumbnail(romPath, imagePath):
    tempPath = f"{romPath}.tmp"
    converted = frogtool.rgb565_convert(imagePath, tempPath, (144, 208))
    if not converted:
        return False
    # copy the rom data to the temp
    try:
        temp_file_handle = open(tempPath, "ab")
        zxx_file_handle = open(romPath, "rb")
        romData = bytearray(zxx_file_handle.read())
        temp_file_handle.write(romData[59904:])
        temp_file_handle.close()
        zxx_file_handle.close()
    except (OSError, IOError):
        print(f"! Failed appending zip file to ")
        return False
    try:
        shutil.move(tempPath,romPath)
    except (OSError, IOError) as error:
        print(f"! Failed moving temp files. {error}")
        return False
    return True

"""
This is a rewrtite attempt at changing the cover art inplace rather thancopy and replace
"""
def changeZXXThumbnail2(romPath, imagePath):
    coverData = getImageData565(imagePath, (144, 208))
    if not coverData:
        return False
    # copy the rom data to the temp
    try:
        zxx_file_handle = open(romPath, "r+b")
        zxx_file_handle.seek(0)
        zxx_file_handle.write(coverData)
        zxx_file_handle.close()
    except (OSError, IOError):
        print(f"! Failed appending zip file to ")
        return False
    return True


def getImageData565(src_filename, dest_size=None):
    if not image_lib_avail:
        print("! Pillow module not found, can't do image conversion")
        return False
    try:
        srcimage = Image.open(src_filename)
    except (OSError, IOError):
        print(f"! Failed opening image file {src_filename} for conversion")
        return False

    # convert the image to RGB if it was not already
    image = Image.new('RGB', srcimage.size, (0, 0, 0))
    image.paste(srcimage, None)

    if dest_size and image.size != dest_size:
        image = image.resize(dest_size)

    image_height = image.size[1]
    image_width = image.size[0]
    pixels = image.load()

    if not pixels:
        print(f"! Failed to load image from {src_filename}")
        return False
    rgb565Data = []
    for h in range(image_height):
        for w in range(image_width):
            pixel = pixels[w, h]
            if not type(pixel) is tuple:
                print(f"! Unexpected pixel type at {w}x{h} from {src_filename}")
                return False
            r = pixel[0] >> 3
            g = pixel[1] >> 2
            b = pixel[2] >> 3
            rgb = (r << 11) | (g << 5) | b
            rgb565Data.append(struct.pack('H', rgb))
    return rgb565Data


offset_logo_presequence = [0x62, 0x61, 0x64, 0x5F, 0x65, 0x78, 0x63, 0x65, 0x70, 0x74, 0x69, 0x6F, 0x6E, 0x00, 0x00, 0x00]
offset_buttonMap_presequence = [0x00, 0x00, 0x00, 0x71, 0xDB, 0x8E, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00]
offset_buttonMap_postsequence = [0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x01, 0x00, 0x00, 0x00, 0x01, 0x00, 0x00, 0x00, 0x02, 0x00, 0x00, 0x00, 0x02, 0x00, 0x00, 0x00]


def bisrv_getFirmwareVersion(index_path):
    print(f"trying to read {index_path}")
    try:
        file_handle = open(index_path, 'rb')  # rb for read, wb for write
        bisrv_content = bytearray(file_handle.read(os.path.getsize(index_path)))
        file_handle.close()
        
        # Only really worthwhile doing this for big bisrv.asd files...
        if (len(bisrv_content)> 12640000):
            # First, replace CRC32 bits with 00...
            bisrv_content[396] = 0x00
            bisrv_content[397] = 0x00
            bisrv_content[398] = 0x00
            bisrv_content[399] = 0x00
          
        # Next identify the boot logo position, and blank it out too...
            badExceptionOffset = findSequence(offset_logo_presequence, bisrv_content)
            if (badExceptionOffset > -1):  # Check we found the boot logo position
                bootLogoStart = badExceptionOffset + 16
                for i in range(bootLogoStart, bootLogoStart + 204800):
                    bisrv_content[i] = 0x00
            else:  # If no boot logo found exit
                return False

            # Next identify the emulator button mappings (if they exist), and blank them out too...
            preButtonMapOffset = findSequence(offset_buttonMap_presequence, bisrv_content)
            if preButtonMapOffset > -1:
                postButtonMapOffset = findSequence(offset_buttonMap_postsequence, bisrv_content, preButtonMapOffset)
                if postButtonMapOffset > -1:
                    for i in range(preButtonMapOffset + 16, i < postButtonMapOffset):
                        bisrv_content[i] = 0x00
                else:
                    return False
            else:
                return False

        # If we're here, we've zeroed-out all of the bits of the firmware that are
        # semi-user modifiable (boot logo, button mappings and the CRC32 bits); now
        # we can generate a hash of what's left and compare it against some known
        # values...
          
        sha256hasher = hashlib.new('sha256')
        sha256hasher.update(b"Nobody inspects the spammish repetition")
        bisrvHash = sha256hasher.hexdigest()
        print(f"Hash: {bisrvHash}")
        return bisrvHash
   
        # else:
        #      return False
        
    except (IOError, OSError):
        print("! Failed reading bisrv.")
        print("  Check the SD card and file are readable, and the file is not open in another program.")
        raise Exception_InvalidPath

class Exception_InvalidConsole(Exception):
    pass

class Exception_InvalidGamePosition(Exception):
    pass


"""
index_path should be the Drive of the Frog card only. It must inlude the semicolon if relevant. ie "E:"
console must be a supported console from the tadpole_functions systems array.
position is a 0-based index of the short. values 0 to 3 are considered valid.
game should be the file name including extension. ie Final Fantasy Tactics Advance (USA).zgb
"""


def changeGameShortcut(index_path, console, position, game):
    # Check the passed variables for validity
    if not(0 <= position <= 3):
        raise Exception_InvalidPath
    if not (console in systems.keys()):
        raise Exception_InvalidConsole
        
    try:
        trimmedGameName = frogtool.strip_file_extension(game)
        print(f"Filename trimmed to: {trimmedGameName}")
        #Read in all the existing shortcuts from file
        xfgle_filepath = os.path.join(index_path, "Resources", "xfgle.hgp")
        xfgle_file_handle = open(xfgle_filepath, "r")
        lines = xfgle_file_handle.readlines()
        xfgle_file_handle.close()
        prefix = 9
        if console == "ARCADE":  # Arcade lines must be prefixed with "6", all others can be anything.
            prefix = 6
        # Overwrite the one line we want to change
        lines[4*systems[console][3]+position] = f"{prefix} {game}*\n"
        # Save the changes out to file
        xfgle_file_handle = open(xfgle_filepath, "w")
        for line in lines:
            xfgle_file_handle.write(line)
        xfgle_file_handle.close()       
    except (OSError, IOError):
        print(f"! Failed changing the shortcut file")
        return False
  
    return -1
    

def findSequence(needle, haystack, offset = 0):
    # Loop through the data array starting from the offset
    for i in range(len(haystack) - len(needle) + 1):
        readpoint = offset + i
        # Assume a match until proven otherwise
        match = True
        # Loop through the target sequence and compare each byte
        for j in range(len(needle)):
            if haystack[readpoint + j] != needle[j]:
                # Mismatch found, break the inner loop and continue the outer loop
                match = False
                break
        # If match is still true after the inner loop, we have found a match
        if match:
            # Return the index of the first byte of the match
            return readpoint
    # If we reach this point, no match was found
    return -1
    

froggyFoldersAndFiles = ["/bios", "/Resources", "/bios/bisrv.asd"]
    
"""
This function is used to check if the supplied drive has relevant folders and files for an SF2000 SD card. 
This should be used to prevent people from accidentally overwriting their other drives.
If the correct files are found it will return True.
If the correct files are not found it will return False.
The drive should be supplied as "E:"
"""


def checkDriveLooksFroggy(drivePath):
    for file in froggyFoldersAndFiles:
        if not os.path.exists(os.path.join(drivePath, file)):
            print(f"missing file {drivePath}/{file}")
            return False
    return True


def get_background_music(url="https://api.github.com/repos/EricGoldsteinNz/SF2000_Resources/contents/BackgroundMusic"):
    """gets index of background music from provided GitHub API URL"""
    music = {}
    response = requests.get(url)

    if response.status_code == 200:
        data = json.loads(response.content)
        for item in data:
            music[item['name'].replace(".bgm", "")] = item['download_url']
        return music
    raise ConnectionError("Unable to obtain music resources. (Status Code: {})".format(response.status_code))


"""
This function downloads a file from the internet and renames it to pagefile.sys to replace the background music.
"""


def changeBackgroundMusic(drive_path: str, url: str = "", file: str = "") -> bool:
    """
    Changes background music to music from the provided URL or file

    Params:
        url (str):  URL to music file to use for replacement.
        file (str):  Full path to a local file to use for replacement.

    Returns:
        bool: True if successful, False if not.

    Raises:
        ValueError: When both url and file params are provided.
    """
    if url and not file:
        return downloadAndReplace(drive_path, "/Resources/pagefile.sys", url)
    elif file and not url:
        try:
            shutil.copyfile(os.path.join(drive_path, "Resources", "pagefile.sys"), file)
            return True
        except:
            return False
    else:
        raise ValueError("Provide only url or path, not both")


def changeConsoleLogos(drivePath, url=""):
    return downloadAndReplace(drivePath, "/Resources/sfcdr.cpl", url)    


def downloadAndReplace(drivePath, fileToReplace, url=""):
    try:
        # retrieve bgm from GitHub resources
        content = ""
        if not url == "":
            print(f"Downloading {fileToReplace} from {url}")
            content = requests.get(url).content

        if not content == "":
            #write the content to file
            bgmPath = os.path.join(drivePath, fileToReplace)
            file_handle = open(bgmPath, 'wb') #rb for read, wb for write
            file_handle.write(content)
            file_handle.close()
        print ("Finished download and replace successfully")
        return True
    except (OSError, IOError) as error:
        print("An error occured while trying to download and replace a file.")
        return False
      
def downloadDirectoryFromGithub(location, url):
    response = requests.get(url) 
    if response.status_code == 200:
        data = json.loads(response.content)
        for item in data:
            if item["type"] == "dir":
                #create folder then recursively download
                foldername = item["name"]
                print(f"creating directory {location}/{foldername}")
                os.makedirs(os.path.dirname(f"{location}/{foldername}/"), exist_ok=True)
                downloadDirectoryFromGithub(f"{location}/{foldername}", item["url"])
            else:# all other cases should be files
                filename = item["name"]
                downloadFileFromGithub(f"{location}/{filename}", item["download_url"])
                
        return True
    raise ConnectionError("Unable to V1.5 Update. (Status Code: {})".format(response.status_code))
    return False
    
def downloadFileFromGithub(outFile, url):
    try:
        response = requests.get(url)
        if response.status_code == 200:
            with open(outFile, 'wb') as f:
                print(f'downloading {url} to {outFile}')
                f.write(response.content)
                return True
        else:
            print("Error when trying to download a file from Github. Response was not code 200")
            raise InvalidURLError
    except Exception as e:
        print(str(e))
        return False

def emptyFavourites(drive) -> bool:
    return emptyFile(os.path.join(drive, "Resources", "Favorites.bin"))
    
def emptyFile(path) -> bool:
    print(f"Deleting file {path}")
    try:      
        if os.path.isfile(path):
            os.remove(path)
        else:
            print("File not found, guess thats still a success? @Goldstein to check the spelling if this is a bug")
        return True
    except:
        print("Error while trying to delete a file")
    return False

def emptyHistory(drive) -> bool:
    return emptyFile(os.path.join(drive, "Resources", "History.bin"))


def extractImgFromROM(romFilePath, outfilePath):
    with open(romFilePath, "rb") as rom_file:
        rom_content = bytearray(rom_file.read())
        img = QImage(rom_content[0:((144*208)*2)], 144, 208, QImage.Format_RGB16)
        img.save(outfilePath)
        
        
def GBABIOSFix(drive: str):
    if drive == "???":
        raise Exception_InvalidPath
    gba_bios_path = os.path.join(drive, "bios", "gba_bios.bin")
    if not os.path.exists(gba_bios_path):
        print(f"! Couldn't find game list file {gba_bios_path}")
        print("  Check the provided path points to an SF2000 SD card!")
        raise Exception_InvalidPath
    try:
        gba_folder_path = os.path.join(drive, "GBA", "mnt", "sda1", "bios")
        roms_folder_path = os.path.join(drive, "ROMS", "mnt", "sda1", "bios")
        os.makedirs(gba_folder_path, exist_ok=True)
        os.makedirs(roms_folder_path, exist_ok=True)
        shutil.copyfile(gba_bios_path, os.path.join(gba_folder_path, "gba_bios.bin"))
        shutil.copyfile(gba_bios_path, os.path.join(roms_folder_path, "gba_bios.bin"))
    except (OSError, IOError) as error:
        print("! Failed to copy GBA BIOS.")
        print(error)
        raise Exception_InvalidPath


ROMART_baseURL = "https://raw.githubusercontent.com/EricGoldsteinNz/libretro-thumbnails/master/"
ROMArt_console = {  
    "FC":     "Nintendo - Nintendo Entertainment System",
    "SFC":    "Nintendo - Super Nintendo Entertainment System",
    "MD":     "Sega - Mega Drive - Genesis",
    "GB":     "Nintendo - Game Boy",
    "GBC":    "Nintendo - Game Boy Color",
    "GBA":    "Nintendo - Game Boy Advance", 
    "ARCADE": ""
}

def downloadROMArt(console : str, ROMpath : str):    
    try:
        if console == "" or ROMArt_console[console] == "":
            print("ROMART invalid console value supplied")
            return False
        title = (os.path.splitext(os.path.basename(ROMpath))[0]).split('.')[0]
        URLtoDownload = f"{ROMART_baseURL}{ROMArt_console[console]}/Named_Boxarts/{title}.png"
        outFile = os.path.join(os.path.dirname(ROMpath),f"{title}.png")
        print(f"Trying to download to {outFile} from {URLtoDownload}")
        if (downloadFileFromGithub(outFile,URLtoDownload)):
            print("Finished downloading. Success.")
            return True
        
    except Exception as e:
        logging.exception(f"CRITICAL ERROR while downloading ROMART: {str(e)}")
    return False
    
    
def stripShortcutText(drive: str):
    if drive == "???" or drive == "":
        raise Exception_InvalidPath
    gakne_path = os.path.join(drive, "Resources", "gakne.ctp")
    try:
        gakne = open(gakne_path, "rb")
        data = bytearray(gakne.read())
        gakne.close()
        # Gakne is made up of 8 rows of 4 items for a total of 32 items.
        # Each image is 144 x 32. Total image size 576 x 256.
        # To only strip the shortcut text we want to leave the settings menu items. So we have to skip the first 18,432 bytes
        
        for i in range (18432, len(data)):
            data[i-1] = 0x00
        gakne = open(gakne_path, "wb")
        gakne.write(data)
        gakne.close()
        return True
    except (OSError, IOError) as e:
        print(f"! Failed striping shortcut labels. {e}")
        return False