import struct
import os
from io import BytesIO

class chunk_size:
    def __init__(self):
        self.size_id = 4
        self.size_chunk = 4
        self.endian = False
        self.unpackfunc = struct.Struct('<I').unpack

    def set_sizes(self, size_id, size_chunk, endian):
        self.size_id = size_id
        self.size_chunk = size_chunk
        self.endian = endian
        if self.size_chunk == 1: self.unpackfunc = struct.Struct('B').unpack
        if self.size_chunk == 2: self.unpackfunc = struct.Struct('>H' if self.endian else '<H').unpack
        if self.size_chunk == 4: self.unpackfunc = struct.Struct('>I' if self.endian else '<I').unpack

class chunk_loc:
    def __init__(self, byteread, sizedata):
        self.t_byteread = byteread
        self.t_sizedata = sizedata
        self.id = b''
        self.start = 0
        self.end = 0
        self.size = 0

    def iter(self, offset): 
        subchunk_obj = self.t_byteread.chunk_objmake()
        subchunk_obj.sizedata = self.t_sizedata
        return subchunk_obj.iter(self.start+offset, self.end)

    def debugtxt(self):
        print(self.id, self.start, self.end)

class iff_chunkdata:
    def __init__(self, byteread):
        self.byteread = byteread
        self.sizedata = chunk_size()

    def set_sizes(self, size_id, size_chunk, endian):
        self.sizedata.set_sizes(size_id, size_chunk, endian)

    def read(self, end):
        chunk_obj = chunk_loc(self.byteread, self.sizedata)
        chunk_obj.id = self.byteread.read(self.sizedata.size_id)
        chunk_obj.size = self.sizedata.unpackfunc(self.byteread.read(self.sizedata.size_chunk))[0]
        chunk_obj.start = self.byteread.tell()
        chunk_obj.end = chunk_obj.start+chunk_obj.size
        isvalid = chunk_obj.end <= end
        return isvalid, chunk_obj

    def iter(self, start, end):
        pos = self.byteread.tell()
        if start > -1: self.byteread.seek(start)
        while end > self.byteread.tell():
            isvalid, chunk_obj = self.read(end)
            if not isvalid: break
            bpos = self.byteread.tell()
            yield chunk_obj
            self.byteread.seek(bpos+chunk_obj.size)
        self.byteread.seek(pos)

class bytereader:
    unpack_byte = struct.Struct('B').unpack
    unpack_short = struct.Struct('<H').unpack
    unpack_int = struct.Struct('<I').unpack
    
    def __init__(self):
        self.buf = None
        self.end = 0

    def chunk_objmake(self): 
        return iff_chunkdata(self)

    def load_file(self, filename):
        if os.path.exists(filename):
            file_stats = os.stat(filename)
            self.end = file_stats.st_size
            self.buf = open(filename, 'rb')
            return True
        else:
            exit('File Not Found - '+filename)

    def load_raw(self, rawdata):
        self.end = len(rawdata)
        self.buf = BytesIO(rawdata)

    def magic_check(self, headerbytes):
        if self.buf.read(len(headerbytes)) == headerbytes: return True
        else: exit('header check failed')

    def read(self, num): return self.buf.read(num)
    def tell(self): return self.buf.tell()
    def seek(self, num): return self.buf.seek(num)
    def skip(self, num): return self.buf.seek(self.buf.tell()+num)
    def rest(self): return self.buf.read()

    def uint8(self): return self.unpack_byte(self.buf.read(1))[0]
    def uint16(self): return self.unpack_short(self.buf.read(2))[0]
    def uint32(self): return self.unpack_int(self.buf.read(4))[0]
    def raw(self, size): return self.buf.read(size)
    def string(self, size, **kwargs): return self.buf.read(size).split(b'\x00')[0].decode(**kwargs)