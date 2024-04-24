# OS imports
import frogtool
import logging
import os
import struct
try:
    from PIL import Image
    image_lib_avail = True
except ImportError:
    Image = None
    ImageDraw = None
    image_lib_avail = False

multicore_exclusionList = [
    "data",
    "DoConfig.exe",
    "Manual",
    "Manual.html",
    "OrgView.exe",
    "Readme.txt",
    "SETTINGS.DAT",
    ""
]


def CreateMulticoreZFB(multicore_ROM_string, dest_filename):
    if not image_lib_avail:
        print("! Pillow module not found, can't do image conversion")
        return False
    try:
        dest_file = open(dest_filename, "wb")
    except (OSError, IOError):
        print(f"! Failed opening destination file {dest_filename} for conversion")
        return False
    # convert the image to RGB if it was not already
    image = Image.new('RGB', frogtool.defaultThumbnailSize, (0, 0, 0))
    pixels = image.load()
    if not pixels:
        print(f"! Failed to load blank image")
        return False
    for h in range(frogtool.defaultThumbnailSize[1]):
        for w in range(frogtool.defaultThumbnailSize[0]):
            pixel = pixels[w, h]
            if not type(pixel) is tuple:
                print(f"! Unexpected pixel type at {w}x{h}")
                return False
            r = pixel[0] >> 3
            g = pixel[1] >> 2
            b = pixel[2] >> 3
            rgb = (r << 11) | (g << 5) | b
            dest_file.write(struct.pack('H', rgb))
    # Write four 00 bytes
    dest_file.write(b'\x00\x00\x00\x00')
    # Write the ROM filename
    dest_file.write(multicore_ROM_string.encode())
    # Write two 00 bytes
    dest_file.write(b'\x00\x00')
    
    dest_file.close()
    return True


def makeMulticoreROMList(drive):
    logging.info("tadpole_functions~makeMulticoreROMList")
    romcount = 0
    for d in os.listdir(os.path.join(drive,"cores")):
        if os.path.isdir(os.path.join(drive,"cores",d)):
            logging.info(f"Build Multicore ROMs for {d}")
            romfolder = os.path.join(drive,"ROMS",d)
            if os.path.exists(romfolder):
                for rom in os.listdir(romfolder):
                    romcount += 1
                    # Creates a new file 
                    with open(os.path.join(drive,"ROMS",f"{d};{rom}.gba"), 'w'): 
                        pass
    return romcount

def makeMulticoreROMList_ARCADEMode(drive):
    logging.info("tadpole_functions~makeMulticoreROMList_ARCADEMode")
    romcount = 0
    for d in os.listdir(os.path.join(drive,"cores")):
        # Handle some special cases first
        if(d == "2048"):
            CreateMulticoreZFB("2048;game.gba",os.path.join(drive, "ARCADE","2048.zfb"))
        elif(d == "cavestory"):
            CreateMulticoreZFB("cavestory;Config.dat.gba",os.path.join(drive, "ARCADE","Cave Story.zfb"))
        elif(d =="gong"):
            CreateMulticoreZFB("gong;game.gba",os.path.join(drive, "ARCADE","Gong.zfb"))
        elif(d == "mrboom"):
            CreateMulticoreZFB("mrboom;dummy.gba",os.path.join(drive, "ARCADE","Mrboom.zfb"))
        elif(d == "wolf3d"):
            CreateMulticoreZFB("wolf3d;WOLF3D.EXE.gba",os.path.join(drive, "ARCADE","Wolfenstein 3D.zfb"))         
        elif os.path.isdir(os.path.join(drive,"cores",d)):
            logging.info(f"Build Multicore ROMs for {d}")
            print(f"Got to {d}")
            romfolder = os.path.join(drive,"ROMS",d)
            if os.path.exists(romfolder):
                destination_zfb = "ARCADE"
                if "snes" in d:
                    destination_zfb = "SFC"
                elif "nes" in d:
                    destination_zfb = "FC"
                elif "gba" in d:
                    destination_zfb = "GBA"
                elif "gbc" in d:
                    destination_zfb = "GBC"
                elif "gb" in d:
                    destination_zfb = "GB"
                elif "sega" in d:
                    destination_zfb = "MD"

                for rom in os.listdir(romfolder):
                    dest_filename = os.path.join(drive, destination_zfb, f"{os.path.splitext(rom)[0]}.zfb")
                    if(not os.path.exists(dest_filename) and rom not in multicore_exclusionList):
                        romcount += 1
                        # Creates a new file 
                        multicore_rom_string = f"{d};{rom}.gba" 
                        CreateMulticoreZFB(multicore_rom_string, dest_filename)
    return romcount