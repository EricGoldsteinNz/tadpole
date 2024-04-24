import os
import re
import binascii
import shutil
import struct

try:
    from PIL import Image
    from PIL import ImageDraw
    image_lib_avail = True
except ImportError:
    Image = None
    ImageDraw = None
    image_lib_avail = False

systems = {
    "ARCADE": ["mswb7.tax", "msdtc.nec", "mfpmp.bvs"],
    "FC":     ["rdbui.tax", "fhcfg.nec", "nethn.bvs"],
    "GB":     ["vdsdc.tax", "umboa.nec", "qdvd6.bvs"],
    "GBA":    ["vfnet.tax", "htuiw.nec", "sppnp.bvs"],
    "GBC":    ["pnpui.tax", "wjere.nec", "mgdel.bvs"],
    "MD":     ["scksp.tax", "setxa.nec", "wmiui.bvs"],
    "SFC":    ["urefs.tax", "adsnt.nec", "xvb6c.bvs"]
}

supported_rom_ext = [
    "bkp", "zip", "zfc", "zsf", "zmd", "zgb", "zfb", "smc", "fig", "sfc", "gd3", "gd7", "dx2", "bsx", "swc", "nes",
    "nfc", "fds", "unf", "gba", "agb", "gbz", "gbc", "gb", "sgb", "bin", "md", "smd", "gen", "sms"
]
zxx_ext = {
    "ARCADE": "zfb", "FC": "zfc", "GB": "zgb", "GBA": "zgb", "GBC": "zgb", "MD": "zmd", "SFC": "zsf"
}
supported_img_ext = [
    "png", "jpg", "jpeg", "gif"
]
supported_zip_ext = [
    "bkp", "zip"
]

defaultThumbnailSize = (144, 208)


class StopExecution(Exception):
    pass


def int_to_4_bytes_reverse(src_int):
    hex_string = format(src_int, "x").rjust(8, "0")[0:8]
    return binascii.unhexlify(hex_string)[::-1]  # reverse it


def file_entry_to_name(file_entry):
    return file_entry.name


def check_file(file_entry, supported_exts):
    file_regex = ".+\\.(" + "|".join(supported_exts) + ")$"
    return file_entry.is_file() and re.search(file_regex, file_entry.name.lower())


def check_rom(file_entry):
    return check_file(file_entry, supported_rom_ext)


def check_img(file_entry):
    return check_file(file_entry, supported_img_ext)


def check_zip(file_entry):
    return check_file(file_entry, supported_zip_ext)


def strip_file_extension(name):
    parts = name.split(".")
    parts.pop()
    return ".".join(parts)


def sort_normal(unsorted_list):
    return sorted(unsorted_list)


def sort_without_file_ext(unsorted_list):
    stripped_names = list(map(strip_file_extension, unsorted_list))
    sort_map = dict(zip(unsorted_list, stripped_names))
    return sorted(sort_map, key=sort_map.get)


def getROMList(roms_path):
    if not os.path.isdir(roms_path):
        print(f"! Couldn't find folder {roms_path}")
        print("  Check the provided path points to an SF2000 SD card!")
        raise StopExecution
    files = os.scandir(roms_path)
    files = list(filter(check_rom, files))
    filenames = list(map(file_entry_to_name, files))
    return filenames

def process_sys(drive, system, test_mode):
    print(f"Processing {system}")

    roms_path = os.path.join(drive,system)
    filenames = getROMList(roms_path)

    index_path_files = os.path.join(drive,"Resources",systems[system][0])
    index_path_cn = os.path.join(drive,"Resources",systems[system][1])
    index_path_pinyin = os.path.join(drive,"Resources",systems[system][2])
    check_and_back_up_file(index_path_files)
    check_and_back_up_file(index_path_cn)
    check_and_back_up_file(index_path_pinyin)

    print(f"Looking for files in {roms_path}")

    if system != "ARCADE":
        convert_zip_image_pairs_to_zxx(roms_path, system)

    #Bugfix: get new filenames now that we have converted from zip to zxx
    filenames = getROMList(roms_path)
    no_files = len(filenames)
    if no_files == 0:
        print("No ROMs found! Going to save an empty file list")
        #return f"No ROMs found to rebuild in {system}"

    stripped_names = list(map(strip_file_extension, filenames))

    # prepare maps of filenames to index name for the 3 index files
    # for "files" we just want the actual filenames as both key and value, the menu will strip the extensions
    name_map_files = dict(zip(filenames, filenames))
    # for the Chinese names and pinyin initials, i'm not supporting that at the moment, so use the English titles
    # but use the stripped versions because the menu will not strip them here
    name_map_cn = dict(zip(filenames, stripped_names))
    name_map_pinyin = dict(zip(filenames, stripped_names))

    write_index_file(name_map_files, sort_without_file_ext, index_path_files, test_mode)
    write_index_file(name_map_cn, sort_normal, index_path_cn, test_mode)
    write_index_file(name_map_pinyin, sort_normal, index_path_pinyin, test_mode)

    print("Done\n")
    return f"Finished updating {system} with {no_files} ROMs"


def find_matching_file_diff_ext(target, files):
    target_no_ext = strip_file_extension(target.name)
    for file in files:
        file_no_ext = strip_file_extension(file.name)
        if file_no_ext == target_no_ext:
            return file

def convert_zip_image_pairs_to_zxx(roms_path, system):
    img_files = os.scandir(roms_path)
    img_files = list(filter(check_img, img_files))
    zip_files = os.scandir(roms_path)
    zip_files = list(filter(check_zip, zip_files))
    sys_zxx_ext = zxx_ext[system]
    if not img_files or not zip_files:
        return
    print(f"Found image and zip files, looking for matches to combine to {sys_zxx_ext}")

    imgs_processed = 0
    for img_file in img_files:
        zip_file = find_matching_file_diff_ext(img_file, zip_files)
        if not zip_file:
            continue
        converted = convert_zip_image_to_zxx(roms_path, img_file, zip_file, sys_zxx_ext)
        if not converted:
            print("! Aborting image processing due to errors")
            break
        imgs_processed += 1

    if imgs_processed:
        print(f"Combined {imgs_processed} zip + image pairs into .{sys_zxx_ext} files")


def convert_zip_image_to_zxx(path, img_file, zip_file, zxx_ext):

    img_file_path = os.path.join(path,img_file.name)
    zip_file_path = os.path.join(path,zip_file.name)
    zxx_file_name = f"{strip_file_extension(img_file.name)}.{zxx_ext}"
    zxx_file_path = os.path.join(path,zxx_file_name)

    converted = rgb565_convert(img_file_path, zxx_file_path, defaultThumbnailSize)
    if not converted:
        return False

    try:
        zxx_file_handle = open(zxx_file_path, "ab")
        zip_file_handle = open(zip_file_path, "rb")
        zxx_file_handle.write(zip_file_handle.read())
        zxx_file_handle.close()
        zip_file_handle.close()
    except (OSError, IOError):
        print(f"! Failed appending zip file to {zxx_file_name}")
        return False

    try:
        os.remove(img_file_path)
        os.remove(zip_file_path)
    except (OSError, IOError):
        print(f"! Failed deleting source file(s) after creating {zxx_file_name}")
        return False

    return True


def rgb565_convert(src_filename, dest_filename, dest_size=None):
    if not image_lib_avail:
        print("! Pillow module not found, can't do image conversion")
        return False
    try:
        srcimage = Image.open(src_filename)
    except (OSError, IOError):
        print(f"! Failed opening image file {src_filename} for conversion")
        return False
    try:
        dest_file = open(dest_filename, "wb")
    except (OSError, IOError):
        print(f"! Failed opening destination file {dest_filename} for conversion")
        return False
    # convert the image to RGB if it was not already
    image = Image.new('RGB', srcimage.size, (0, 0, 0))
    image.paste(srcimage, None)

    if dest_size and image.size != dest_size:
        ratio = dest_size[1] / dest_size[0]
        if ((image.size[0] * ratio) > image.size[1]):
            width = image.size[1]/ratio
            left = int((image.size[0] - width)/2)
            image = image.crop((left, 0, left + width, image.size[1]))
        else:
            height = image.size[0]*ratio
            top = int((image.size[1] - height)/2)
            image = image.crop((0, top, image.size[0], top + height))

        # new_size=(144, 208)
        # fill_color=(0, 0, 0, 0)
        # size_x = max(dest_size[0], x)
        # size_y = max(dest_size[1], y)
        # new_im = Image.new('RGB', (new_size[0], new_size[1]), fill_color)
        # new_im.paste(image, (int((size_x - x) / 2), int((size_y - y) / 2)))
        # image = new_im
        # TODO Let user pick if they want to stretch or not
        #image = image.scaled(144, 208, Qt.KeepAspectRatio, Qt.SmoothTransformation) #Rescale new boot logo to correct size
        image = image.resize(dest_size)
        #maxsize = (144, 208)
        #image = image.thumbnail(maxsize) 

    image_height = image.size[1]
    image_width = image.size[0]
    pixels = image.load()

    if not pixels:
        print(f"! Failed to load image from {src_filename}")
        return False

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
            dest_file.write(struct.pack('H', rgb))
    dest_file.close()
    return True


def check_and_back_up_file(file_path):
    if not os.path.exists(file_path):
        print(f"! Couldn't find game list file {file_path}")
        print("  Check the provided path points to an SF2000 SD card!")
        raise StopExecution

    if not os.path.exists(f"{file_path}_orig"):
        print(f"Backing up {file_path} as {file_path}_orig")
        try:
            shutil.copyfile(file_path, f"{file_path}_orig")
        except (OSError, IOError):
            print("! Failed to copy file.")
            print("  Check the SD card and Resources directory are writable.")
            raise StopExecution


def write_index_file(name_map, sort_func, index_path, test_mode):
    # entries must maintain a consistent order between all indexes, but what that order actually is doesn't matter
    # so use alphabetised filenames for this
    sorted_filenames = sorted(name_map.keys())
    # build up the list of names in that order as a byte string, and also build a dict of pointers to each name
    names_bytes = b""
    pointers_by_name = {}
    for filename in sorted_filenames:
        display_name = name_map[filename]
        current_pointer = len(names_bytes)
        pointers_by_name[display_name] = current_pointer
        names_bytes += display_name.encode('utf-8') + chr(0).encode('utf-8')

    # build the metadata - first value is the total count of games in this list
    metadata_bytes = int_to_4_bytes_reverse(len(name_map))
    # the rest are pointers to the display names in the desired display order
    # so sort display names according to the display order, and build a list of pointers in that order
    sorted_display_names = sort_func(name_map.values())
    sorted_pointers = map(lambda name: pointers_by_name[name], sorted_display_names)
    for current_pointer in sorted_pointers:
        metadata_bytes += int_to_4_bytes_reverse(current_pointer)

    new_index_content = metadata_bytes + names_bytes

    if test_mode:
        print(f"Checking {index_path}")
        file_handle = open(index_path, 'rb')
        existing_index_content = file_handle.read(os.path.getsize(index_path))
        file_handle.close()
        if existing_index_content != new_index_content:
            print("! Doesn't match")
        return

    print(f"Overwriting {index_path}")
    try:
        file_handle = open(index_path, 'wb')
        file_handle.write(new_index_content)
        file_handle.close()
    except (IOError, OSError):
        print("! Failed overwriting file.")
        print("  Check the SD card and file are writable, and the file is not open in another program.")
        raise StopExecution


def check_sys_valid(system):
    return system and (system in systems.keys() or system == "ALL")



