"""HID access for QMP.

Windows uses pywinusb, as before.  Everywhere else this module provides the small
part of the pywinusb API that QuadStickHID.py and ultrastik.py use, on top of hidapi.
"""
import sys

if sys.platform == 'win32':
    from pywinusb.hid import HidDeviceFilter
else:
    import ctypes
    import threading
    import hid as _hidapi

    if sys.platform == 'darwin':
        # hidapi seizes a device when it opens it on macOS.  That would hide the
        # QuadStick from games for as long as QMP is running, so open it shared.
        ctypes.CDLL(_hidapi.__file__).hid_darwin_set_open_exclusive(0)

    # HID report descriptor item tags (prefix byte with its two size bits masked off)
    _REPORT_SIZE, _REPORT_COUNT, _REPORT_ID = 0x74, 0x94, 0x84
    _MAIN_ITEMS = {0x80: 'input', 0x90: 'output', 0xB0: 'feature'}

    def parse_reports(descriptor):
        """Return {'input'|'output'|'feature': {report_id: payload_bytes}} for a HID report descriptor.

        Report id 0 means the device does not number its reports.
        """
        bits = {kind: {} for kind in _MAIN_ITEMS.values()}
        size = count = report_id = 0
        i = 0
        while i < len(descriptor):
            prefix = descriptor[i]
            if prefix == 0xFE:  # long item, nothing in it we need
                i += 3 + descriptor[i + 1]
                continue
            length = (0, 1, 2, 4)[prefix & 0x03]
            value = int.from_bytes(bytes(descriptor[i + 1:i + 1 + length]), 'little')
            tag = prefix & 0xFC
            if tag == _REPORT_SIZE:
                size = value
            elif tag == _REPORT_COUNT:
                count = value
            elif tag == _REPORT_ID:
                report_id = value
            elif tag in _MAIN_ITEMS:
                reports = bits[_MAIN_ITEMS[tag]]
                reports[report_id] = reports.get(report_id, 0) + size * count
            i += 1 + length
        return {kind: {rid: (n + 7) // 8 for rid, n in reports.items()} for kind, reports in bits.items()}

    class _Report(object):
        """An output or feature report.  Also stands in for the report's one value."""
        def __init__(self, device, report_id, length, feature):
            self._device = device
            self._id = report_id
            self._feature = feature
            self._value = [0] * length

        def values(self):
            return [self]

        def get_value(self):
            return self._value

        def set_value(self, data):
            self._value = list(data)

        def send(self):
            dev = self._device._dev
            data = [self._id] + self._value  # hidapi wants the report id first, 0 if unnumbered
            sent = dev.send_feature_report(data) if self._feature else dev.write(data)
            if sent < 0:
                raise IOError(dev.error())

    class _Device(object):
        def __init__(self, info):
            self.vendor_id = info['vendor_id']
            self.product_id = info['product_id']
            self.product_name = info['product_string']
            self.device_path = info['path']
            self._dev = None
            self._reports = None
            self._reader = None

        def open(self):
            dev = _hidapi.device()
            dev.open_path(self.device_path)
            try:
                self._reports = parse_reports(dev.get_report_descriptor())
            except Exception:
                dev.close()
                raise
            self._dev = dev

        def close(self):
            dev, self._dev = self._dev, None
            if self._reader:  # must be out of read() before the device is closed under it
                self._reader.join()
                self._reader = None
            if dev:
                dev.close()

        def is_opened(self):
            return self._dev is not None

        def is_plugged(self):
            return any(d['path'] == self.device_path
                       for d in _hidapi.enumerate(self.vendor_id, self.product_id))

        is_active = is_plugged

        def find_feature_reports(self):
            return [_Report(self, rid, n, True) for rid, n in self._reports['feature'].items()]

        def find_output_reports(self):
            return [_Report(self, rid, n, False) for rid, n in self._reports['output'].items()]

        def set_raw_data_handler(self, handler):
            """Call handler(data) from a reader thread for every input report, as pywinusb does."""
            sizes = self._reports['input']
            numbered = any(sizes)
            length = max(sizes.values(), default=63) + 1

            def pump():
                try:
                    while (dev := self._dev) is not None:
                        data = dev.read(length, 250)
                        if data:  # pywinusb always leads with the report id, 0 if unnumbered
                            handler(data if numbered else [0] + data)
                except (OSError, ValueError):
                    pass  # unplugged

            self._reader = threading.Thread(target=pump, daemon=True)
            self._reader.start()

    class HidDeviceFilter(object):
        def __init__(self, vendor_id, product_id):
            self._ids = (vendor_id, product_id)

        def get_devices(self):
            # hidapi lists a device once per usage; one entry per interface is enough
            found = {d['path']: d for d in _hidapi.enumerate(*self._ids)}
            # Game controller interface first.  On Windows the first device pywinusb
            # returns is interface 0, which is the QuadStick's game controller.
            def order(d):
                controller = d['usage_page'] == 1 and d['usage'] in (4, 5)
                return (not controller, d['interface_number'])
            return [_Device(d) for d in sorted(found.values(), key=order)]


def demo():
    """Self-check for the report descriptor parser: python hidcompat.py"""
    if sys.platform == 'win32':
        print('nothing to check on Windows, pywinusb parses descriptors itself')
        return
    unnumbered = [
        0x05, 0x01, 0x09, 0x05, 0xA1, 0x01,       # Generic Desktop, Game Pad, Collection
        0x75, 0x08, 0x95, 0x13, 0x81, 0x02,       # 19 bytes of input
        0x75, 0x08, 0x95, 0x08, 0xB1, 0x02,       # 8 bytes of feature
        0x75, 0x08, 0x95, 0x08, 0x91, 0x02,       # 8 bytes of output
        0xC0,
    ]
    assert parse_reports(unnumbered) == {'input': {0: 19}, 'output': {0: 8}, 'feature': {0: 8}}
    numbered = [
        0x05, 0x01, 0x09, 0x05, 0xA1, 0x01,
        0x85, 0x01, 0x75, 0x01, 0x95, 0x0E, 0x81, 0x02,   # report 1: 14 bits of buttons...
        0x75, 0x02, 0x95, 0x01, 0x81, 0x03,               # ...plus 2 bits of padding
        0x26, 0xFF, 0x00, 0x75, 0x08, 0x95, 0x3F, 0x81, 0x02,   # ...plus 63 bytes (2-byte Logical Maximum first)
        0x85, 0x05, 0x75, 0x08, 0x95, 0x1F, 0xB1, 0x02,   # report 5: 31 bytes of feature
        0xFE, 0x02, 0x00, 0xAA, 0xBB,                     # long item, skipped
        0xC0,
    ]
    assert parse_reports(numbered) == {'input': {1: 65}, 'output': {}, 'feature': {5: 31}}
    print('hidcompat ok')


if __name__ == '__main__':
    demo()
