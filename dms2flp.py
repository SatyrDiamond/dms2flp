
from objects import bytereader
from io import BytesIO
import struct
import varint
import zlib
import argparse
import os

parser = argparse.ArgumentParser()
parser.add_argument("input")
args = parser.parse_args()

def make_flevent(FLdt_bytes, value, data):
	if value <= 63 and value >= 0: # int8
		FLdt_bytes.write(value.to_bytes(1, "little"))
		FLdt_bytes.write(data.to_bytes(1, "little"))
	if value <= 127 and value >= 64 : # int16
		FLdt_bytes.write(value.to_bytes(1, "little"))
		FLdt_bytes.write(data.to_bytes(2, "little"))
	if value <= 191 and value >= 128 : # int32
		FLdt_bytes.write(value.to_bytes(1, "little"))
		FLdt_bytes.write(data.to_bytes(4, "little"))
	if value <= 224 and value >= 192 : # text
		FLdt_bytes.write(value.to_bytes(1, "little"))
		FLdt_bytes.write(varint.encode(len(data)))
		FLdt_bytes.write(data)
	if value <= 255 and value >= 225 : # data
		FLdt_bytes.write(value.to_bytes(1, "little"))
		FLdt_bytes.write(varint.encode(len(data)))
		FLdt_bytes.write(data)

input_file = args.input

if not os.path.exists(input_file): print('file not found')

song_file = bytereader.bytereader()
song_file.load_file(input_file)
song_file.magic_check(b'PortalSequenceData')
song_file.skip(4)
song_data = bytereader.bytereader()
song_data.load_raw(zlib.decompress(song_file.rest(), zlib.MAX_WBITS|32))

main_iff_obj = song_data.chunk_objmake()
main_iff_obj.set_sizes(2, 4, False)

tracks = []

for chunk_obj in main_iff_obj.iter(0, song_data.end):
	chunkid = int.from_bytes(chunk_obj.id, 'little')

	if chunkid == 1003:
		track = ['.', []]
		for trk_chunk_obj in chunk_obj.iter(0):
			trk_chunkid = int.from_bytes(trk_chunk_obj.id, 'little')
			if trk_chunkid == 1002: 
				txt = song_data.string(trk_chunk_obj.size)
				if txt: track[0] = txt
			if trk_chunkid == 2001:
				note = [0,0,0,0]
				for trk_subchunk_obj in trk_chunk_obj.iter(0):
					subchunkid = int.from_bytes(trk_subchunk_obj.id, 'little')
					if subchunkid == 1001: note[0] = song_data.uint32()
					if subchunkid == 2001: note[1] = song_data.uint8()
					if subchunkid == 2002: note[2] = song_data.uint8()
					if subchunkid == 2003: note[3] = song_data.uint32()
				track[1].append(note)
		tracks.append(track)

flpout = open('out.flp', 'wb')

data_FLhd = BytesIO()
data_FLhd.write((len(tracks)).to_bytes(3, 'big'))
data_FLhd.write(b'\x00')
data_FLhd.write((96).to_bytes(2, 'little'))

data_FLdt = BytesIO()

make_flevent(data_FLdt, 199, '3.5.4'.encode('utf8') + b'\x00')

make_flevent(data_FLdt, 93, 0)
make_flevent(data_FLdt, 66, 140)
make_flevent(data_FLdt, 67, 1)
make_flevent(data_FLdt, 9, 1)
make_flevent(data_FLdt, 11, 0)
make_flevent(data_FLdt, 12, 128)
make_flevent(data_FLdt, 80, 0)
make_flevent(data_FLdt, 17, 16)
make_flevent(data_FLdt, 24, 16)
make_flevent(data_FLdt, 18, 4)
make_flevent(data_FLdt, 23, 1)
make_flevent(data_FLdt, 10, 0)

for c, t in enumerate(tracks):
	make_flevent(data_FLdt, 64, c)
	make_flevent(data_FLdt, 192, t[0].encode('utf8') + b'\x00')
	make_flevent(data_FLdt, 65, c+1)
	make_flevent(data_FLdt, 193, t[0].encode('utf8') + b'\x00')

	note_bin = b''

	for pos, key, vol, dur in t[1]: note_bin += struct.pack('IHHIBBBBBBBB', pos, 16384,c ,dur, key,0,0,0, 64,vol,128,128)

	make_flevent(data_FLdt, 224, note_bin)
	make_flevent(data_FLdt, 129, 65536*(c+1))

data_FLhd.seek(0)
flpout.write(b'FLhd')
data_FLhd_out = data_FLhd.read()
flpout.write(len(data_FLhd_out).to_bytes(4, 'little'))
flpout.write(data_FLhd_out)

data_FLdt.seek(0)
flpout.write(b'FLdt')
data_FLdt_out = data_FLdt.read()
flpout.write(len(data_FLdt_out).to_bytes(4, 'little'))
flpout.write(data_FLdt_out)


