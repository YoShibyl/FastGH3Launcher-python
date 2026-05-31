import struct
import io
from typing import Dict, List

# SNG file parsing, courtesy of mdsitton (and anyone else involved)
# - https://github.com/mdsitton/SngFileFormat

class Sng:
    def __init__(self):
        self.version = 0
        self.xorMask = bytearray(16)
        self.meta: Dict[str, str] = {}
        self.files: List[Sng.File] = []

    class File:
        def __init__(self):
            self.name = ""
            self.data = bytearray()

    @staticmethod
    def readstr(raw):
        length = struct.unpack('<I', raw[:4])[0]
        return raw[4:length+4].decode('utf-8')

    @staticmethod
    def Load(fname):
        off = 0
        sng = Sng()
        with open(fname, 'rb') as f:
            raw = f.read()
            magic = raw[:6].decode('utf-8')
            if magic != "SNGPKG":
                raise Exception(magic)
            off+=6
            sng.version = struct.unpack('<I', raw[off:off+4])[0]
            off+=4
            sng.xorMask = bytearray(raw[off:off+16])
            off+=16
            
            metasize = struct.unpack('<Q', raw[off:off+8])[0]
            off+=8
            metacount = struct.unpack('<Q', raw[off:off+8])[0]
            off+=8
            for _ in range(metacount):
                key = Sng.readstr(raw[off:])
                off += len(key) + 4
                value = Sng.readstr(raw[off:])
                off += len(value) + 4
                sng.meta[key] = value
            idxsize = struct.unpack('<Q', raw[off:off+8])[0]
            off+=8
            fcount = struct.unpack('<Q', raw[off:off+8])[0]
            off+=8
            for _ in range(fcount):
                fnamelen = struct.unpack('<B', raw[off:off+1])[0]
                name = raw[off+1:off+1+fnamelen].decode('utf-8')
                off+=len(name)+1
                
                fsize = struct.unpack('<Q', raw[off:off+8])[0]
                off+=8
                index = struct.unpack('<Q', raw[off:off+8])[0]
                off+=8
                ## Strip anything that isn't the album art or chart/midi data (might change in the future)
                if name.startswith("album") or name.endswith(".chart") or name.endswith(".mid"):
                    data = bytearray(raw[index:index+fsize])
                    for x in range(fsize):
                        data[x] = data[x] ^ (sng.xorMask[x & 15] ^ (x & 0xFF))
                    file_entry = Sng.File()
                    file_entry.name = name
                    file_entry.data = data
                    sng.files.append(file_entry)
            
            concatsize = struct.unpack('<Q', raw[off:off+8])[0]
            f.close()
        return sng