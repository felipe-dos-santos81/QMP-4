## Quadstick flash drive related functions

import os
import sys
import csv
import hashlib
import plistlib
import struct
import subprocess
import threading
import uuid
import wx
if sys.platform == 'win32':
    import win32api

preferences = {}
defaults = {
    'joystick_deflection_minimum':'8',
    'joystick_deflection_maximum':'25',
    'deflection_multiplier_up':'140',
    'deflection_multiplier_down':'130',
    'deflection_multiplier_left':'100',
    'deflection_multiplier_right':'100',
    'joystick_D_Pad_inner':'25',
    'joystick_D_Pad_outer':'80',
    'sip_puff_threshold_soft':'8',
    'sip_puff_threshold':'40',
    'sip_puff_maximum':'70',
    'sip_puff_delay_soft':'1300',
    'sip_puff_delay_hard':'2400',
    'lip_position_minimum':'8',
    'lip_position_maximum':'35',
    'mouse_speed':'100',
    'volume':'40',
    'brightness':'75',
    'digital_out_1':'0',
    'digital_out_2':'0',
    'bluetooth_device_mode':'none',
    'bluetooth_authentication_mode':'4',
    'bluetooth_connection_mode':'pair',
    'bluetooth_remote_address':'',
    'enable_swap_inputs':'0',
    'enable_select_files':'1',
    'watchdog_disable':'0',
    'debug':'1',
    'joystick_dead_zone_shape':'1',
    'anti_dead_zone':'0',
    'enable_auto_zero':'0',
    'mouse_response_curve':'1',
    'enable_usb_comm':'0',
    'TIR_DeadZone':'0',
    'enable_DS3_emulation':'0',
    'enable_usb_a_host':'1',
    'titan_two':'0',
    }

# Local data storage for program data and game profile list

APPDATA = os.environ.get('APPDATA') or os.path.expanduser('~/Library/Application Support')  # Windows or macOS

print ("APPDATA: ", APPDATA)

settings_file = os.path.join(APPDATA, "QMP_3_settings.repr")
old_settings_file = os.path.join(APPDATA, "quadstick_settings.repr")
settings = dict()

print("INITIALIZE QSFLASH SETTINGS")

def read_repr_file():
    global settings
    #print "read settings: ",
    try:
        f = open(settings_file, 'r')
        settings_string = f.read()
        #print ('settings ', repr(settings_string))
        f.close()
        settings.clear()  # modify existing dictionary
        settings.update(eval(settings_string))
    except Exception as e:
        print("read_repr_file exception: ", repr(e))
        try:
            f = open(old_settings_file, 'r')
            settings_string = f.read()
            #print settings_string
            f.close()
            settings.clear()  # modify existing dictionary
            settings.update(eval(settings_string))
            return settings
        except:
            print("no old repr file either")
            pass
        settings.clear() #return NEW blank dictionary
    #print ("Read settings file:  ", repr(settings))
    return settings

def save_repr_file(settings):
    f = open(settings_file, 'w')
    settings_string = repr(settings)
    #print ("save settings: ", settings_string)
    f.write(settings_string)
    f.flush()
    f.close()

def flush_quadstick_drive():
    """Push pending writes out to the QuadStick so it is safe to unplug or reboot.

    Windows writes removable drives through as it goes; macOS holds changes in its cache."""
    if hasattr(os, 'sync'):
        os.sync()

QuadStickDrive = None
def find_quadstick_drive(force=None):
    #return None # for testing serial port functions
    global QuadStickDrive
    if force: QuadStickDrive = None  # force new search for drive
    if QuadStickDrive: return QuadStickDrive
    if sys.platform != 'win32':
        # macOS mounts the drive under its volume name, or "QUAD STICK 1" if a stale mount point is in the way
        for name in os.listdir('/Volumes'):
            d = '/Volumes/' + name + '/'  # ends in a separator like "E:\\" so callers can append a file name
            if name.lower().startswith("quad stick") and os.path.ismount(d[:-1]):
                print("QuadStick drive: ", d)
                QuadStickDrive = d
                return d
        return None
    drives = win32api.GetLogicalDriveStrings()
    drives = drives.split('\000')[:-1]
    for d in drives:
        try:
            drive_name = win32api.GetVolumeInformation(d)[0]
            if drive_name.lower() == "quad stick":
                print("QuadStick drive letter: ", d)
                QuadStickDrive = d
                return d
        except:
            pass # try next drive
    return None

def load_preferences_file(mainWindow):
    global preferences
    d = find_quadstick_drive()
    if d is None:
        if mainWindow.microterm:
            #mainWindow.text_ctrl_messages.AppendText( "Searching for Bluetooth or serial connection... ")
            # try a serial connection if bluetooth ssp enabled
            #if preferences.get("bluetooth_device_mode") == "ssp":
            mt = mainWindow.microterm
            if mt.serial:
                prefs_file = mt.read_qs_file("prefs.csv")
                print("serial port preferences file contents:\n\n", len(prefs_file), repr(prefs_file))
                csvfile = prefs_file.split("\n")
                if len(csvfile) > 3: # at least three lines long
                    while csvfile[0].find("QuadStick Configuration") < 0:
                        csvfile.pop(0)
                if len(csvfile) > 3:
                    reader = csv.reader(csvfile, delimiter=',')
                    row_count = 0
                    for row in reader:
                        #print ', '.join(row) 
                        # skip header section
                        if row_count > 3 and row and row[0]: 
                            if row[0] == "**END OF FILE**":
                                break
                            if row[1]:
                                preferences[row[0]] = row[1]
                                print("assign ", row[0], " with ", row[1])
                        row_count += 1
                    return preferences
        #mainWindow.text_ctrl_messages.AppendText( "Serial connection not found.")
        return None
    pathname = d + 'prefs.csv'
    preferences.clear()
    preferences.update(defaults.copy()) # start out with defaults for any missing items
    try:
        with open(pathname.encode()) as csvfile:
            reader = csv.reader(csvfile, delimiter=',')
            row_count = 0
            for row in reader:
                #print ', '.join(row) 
                # skip header section
                if row_count > 3 and row and row[0] and row[1]:
                    preferences[row[0]] = row[1]
                row_count += 1
    except Exception as e:
        print('quadstick drive found but unable to read prefs.csv file')
        print(repr(e))
        return None
    #print repr(preferences)
    return preferences

CSV_HEADER = """QuadStick Configuration,Version 1.1
Preferences,,,,
prefs.csv,,,,
Preference,Value,Units,Description,
"""

def save_preferences_file(preferences):
    global QuadStickDrive
    QuadStickDrive = None # force refresh of quadstick drive
    d = find_quadstick_drive()
    if d is None:
        print("quadstick flash drive not found.  Try serial")
        # try a serial connection if bluetooth ssp enabled
        from microterm import microterm  # late import because microterm imports from this module
        mt = microterm()
        if mt.serial:
            lines = CSV_HEADER.splitlines()
            keys = list(preferences.keys())
            keys.sort()
            for key in keys:
                value = preferences[key]
                lines.append(key + "," + str(value) + ",,")
            for line in lines:
                print(line)
            resp = mt.write_qs_file("prefs.csv", lines)
            print("serial port preferences file bytes written: ", resp)
            if resp.find("bytes written") > -1:
                return True
        return None
    pathname = d + 'prefs.csv'
    try:
        os.remove(pathname)
    except:
        print('prefs.csv not found to delete')
    with open(pathname, 'w', newline='\r\n') as csvfile:
        # write header
        csvfile.write(CSV_HEADER)
        keys = list(preferences.keys())
        keys.sort()
        for key in keys:
            value = preferences[key]
            csvfile.write(key + ',' + str(value) + ',,\n') 
            # cannot use percent sign in wxGlade source files
        csvfile.flush()
        os.fsync(csvfile.fileno())
    flush_quadstick_drive()
    return True

def save_csv_file(name, text):
    d = find_quadstick_drive()
    if d is None:
        print("quadstick flash drive not found")
        return None
    pathname = d + name
    try:
        os.remove(pathname)
    except:
        print('file not found to delete')
    with open(pathname, 'wb', 0) as csvfile:
        # write header
        csvfile.write(text)
        csvfile.flush()
        os.fsync(csvfile.fileno())
    flush_quadstick_drive()
    return True

def list_quadstick_csv_files(mainWindow, fast=False):  # quadstick flash drive
    mainWindow._csv_files = []
    d = find_quadstick_drive()
    if d is None:
        print("list_quadstick_csv_files, quadstick flash drive not found")
        if mainWindow.microterm:
            return mainWindow.microterm.list_files()
        return []
    print ('quadstick drive letter ', repr(d))
    for (paths, dirs, file_names) in os.walk(d):
        break #first level directory only is what we want
    csv_files = [n for n in file_names if (n.lower().find(".csv") > 0) and not n.startswith(".")] # only want .csv, not the "._x.csv" files macOS adds
    file_list = []
    #move default and prefs to front
    if "prefs.csv" in csv_files:
        file_list.append("prefs.csv")
        csv_files.remove("prefs.csv")
    if "default.csv" in csv_files:
        file_list.append("default.csv")
        csv_files.remove("default.csv")
    csv_files = sorted(csv_files, key=lambda s: s.lower())
    file_list.extend(csv_files)
    # read first line in each csv file and get spreadsheet id and name
    answer = []
    for name in file_list:
        spreadsheet_name = ""
        id = ""
        if not fast:
            try:
                pathname = d + name
                print(repr(pathname))
                with open(pathname.encode()) as csvfile:
                    firstline = csvfile.readline()
                parts = firstline.split(",")
                print(repr(parts))
                if parts[0] == "QuadStick Configuration":
                    if parts[1] == "Version 1.4":
                        id = (parts[2].split("spreadsheets/d/")[1]).split("/")[0]
                        spreadsheet_name = parts[3]
                    elif parts[1] == "Version 1.5":
                        id = parts[2]
                        spreadsheet_name = parts[3]
            except Exception as e:
                print("exception while reading details from csv files")
                print(repr(e))
        t = (name, id, spreadsheet_name)
        answer.append(t)
        print("CSV file: ", repr(t))
        mainWindow._csv_files.append({"id":id, "name":spreadsheet_name,"csv_name":name})
    return answer

_FS_UUID_NAMESPACE = uuid.UUID('B3E20F39-F292-11D6-97A4-00306543ECAC').bytes  # Apple's kFSUUIDNamespaceSHA1
_serial_searches = set()  # volume UUIDs already being searched, or searched without success, in this run

def _serial_from_uuid(volume_uuid, sectors, builds):
    """Find the FAT volume serial number that macOS turned into volume_uuid, or None.

    macOS gives a FAT volume the UUID MD5(namespace + serial number + sector count).  The
    QuadStick keeps its firmware build in the low half of the serial number.  The high half
    is unknown, so every value of it is tried for each candidate build (about 30 ms a build).
    A match on the whole hash is the proof, so a wrong answer cannot come out of this."""
    target = uuid.UUID(volume_uuid).bytes
    base = hashlib.md5(_FS_UUID_NAMESPACE)
    tails = [struct.pack('>H', high) + struct.pack('<I', sectors) for high in range(65536)]
    for build in builds:
        low = struct.pack('<H', build)
        for tail in tails:
            h = base.copy()
            h.update(low + tail)
            digest = h.digest()
            # bytes 6 and 8 carry the UUID version and variant bits instead of the hash
            if digest[:6] == target[:6] and digest[7] == target[7] and digest[9:] == target[9:]:
                return low + tail[:2]
    return None

def _find_volume_serial(volume_uuid, sectors, mainWindow):  # worker thread
    from googledrive import get_firmware_versions  # late import because googledrive imports from this module
    try:
        listed = sorted({int(b['version']) for b in get_firmware_versions()}, reverse=True)
    except Exception as e:
        print("no firmware list to find the build number with: ", repr(e))
        _serial_searches.discard(volume_uuid)  # probably offline, try again next time
        return
    # the builds on offer first, then every older one, then the serial number of the oldest firmware
    builds = listed + [b for b in range(listed[0], 0, -1) if b not in listed] + [30867]
    serial = _serial_from_uuid(volume_uuid, sectors, builds)
    if serial is None:
        print("firmware build number not found for volume ", volume_uuid)
        return
    settings['volume_serials'][volume_uuid] = serial.hex()
    wx.CallAfter(mainWindow.updateControls)  # show the build number now that it is known

def _mac_volume_serial(d, mainWindow):
    """The four FAT volume serial number bytes of the QuadStick drive.

    Windows reads them from the boot sector.  macOS does not let a user read the raw disk,
    so they are worked out from the volume UUID instead, on a worker thread, and remembered
    per UUID.  Until the answer is in, this raises and the build number shows as unknown."""
    info = plistlib.loads(subprocess.check_output(['diskutil', 'info', '-plist', d]))
    volume_uuid = info['VolumeUUID']
    known = settings.setdefault('volume_serials', {})
    if not known.get(volume_uuid):
        if volume_uuid not in _serial_searches:
            _serial_searches.add(volume_uuid)
            t = threading.Thread(target=_find_volume_serial, args=(volume_uuid, info['Size'] // 512, mainWindow))
            t.daemon = True
            t.start()
        raise LookupError('firmware build number not known yet')
    return bytes.fromhex(known[volume_uuid])

def quadstick_drive_serial_number(mainWindow):
    # read boot sector from quadstick and pull out build number from serial number
    d = find_quadstick_drive()
    if d is None:
        print("quadstick flash drive not found")
        if mainWindow.microterm:
            #mainWindow.text_ctrl_messages.AppendText( "Searching for Bluetooth or serial connection... ")
            # try a serial connection if bluetooth ssp enabled
            #if preferences.get("bluetooth_device_mode") == "ssp":
            mt = mainWindow.microterm
            if mt.serial:
                build = mt.get_build()
                print("build number is: ", build)
                if build:
                    return int(build.strip())
        return None
    try:
        if sys.platform == 'win32':
            drive = os.open('\\\\.\\' + d[:2], os.O_RDONLY | os.O_BINARY)
            tmp = os.read(drive, 512) # read boot sector 
        else:
            tmp = bytes(39) + _mac_volume_serial(d, mainWindow)  # serial number at its boot sector offset
        #print (repr(tmp))
        #print tmp
        build = tmp[40] * 256 + tmp[39] #drive.read(2) # serial number
        sn = tmp[41] * 256 + tmp[42]
        #drive.close()
        print(repr(build), repr(sn))
        answer = build #ord(build[0]) + 256 * ord(build[1])
        if answer == 30867: #old firmware
            answer = 601
        return answer
    except:
        print('Unable to read drive SN')
        return None


def demo():
    """Self-check for the build number recovery: python qsflash.py"""
    # a FAT image made for testing: serial number bytes 8C 05 12 34 (build 1420), 4096 sectors
    known_uuid = '5B5C8847-33D4-37A7-91BB-DF7FF44B76E0'
    assert _serial_from_uuid(known_uuid, 4096, [1500, 1420]) == bytes([0x8C, 0x05, 0x12, 0x34])
    assert _serial_from_uuid(known_uuid, 4096, [1419, 1421]) is None
    assert _serial_from_uuid(known_uuid, 4095, [1420]) is None
    print('qsflash ok')


if __name__ == '__main__':
    demo()
