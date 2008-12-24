"""

================================================================================

	mingus - Music theory Python package, MIDI File Out
	Copyright (C) 2008, Bart Spaans

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with this program.  If not, see <http://www.gnu.org/licenses/>.

================================================================================

   MidiFileOut contains two classes and some methods that can generate 
   MIDI files from the objects in mingus.containers.

================================================================================

"""
from binascii import a2b_hex
from struct import pack, unpack

class MidiFileOut:
	"""This class generates midi files from MidiTracks. """

	tracks = []
	time_division = "\x00\x48"

	def __init__(self, tracks = []):
		self.reset()
		self.tracks = tracks

	def add_track(self, track):
		self.tracks.append(track)

	def get_midi_data(self):
		"""Returns the raw, binary MIDI data."""
		tracks = [ t.get_midi_data() for t in self.tracks ]
		return self.header() + "".join(tracks)

	def header(self):
		"""Returns a header for type 1 midi file"""
		tracks = a2b_hex("%04x" % len(self.tracks))
		return "MThd\x00\x00\x00\x06\x00\x01" + tracks + self.time_division

	def reset(self):
		"""Resets every track."""
		[ t.reset() for t in self.tracks ]

	def write_file(self, file):
		"""Collects the data from get_midi_data and writes to file. """
		"""Returns True on success. False on failure."""
		data = self.get_midi_data()
		try:
			f = open(file, "wb")
		except:
			print "Couldn't open '%s' for writing." % file
			return False
		try:
			f.write(data)
		except:
			print "An error occured while writing data to %s." % file
			return False
		f.close()
		print "Written %d bytes to %s." % (len(data), file)
		return True

class MidiTrack:

	track_data = ''
	delta_time = '\x00'
	bpm = 120

	def __init__(self, start_bpm = 120):
		self.bpm = start_bpm
		self.track_data = self.set_tempo_event(120)


	def end_of_track(self):
		"""End of track meta event."""
		return "\x00\xff\x2f\x00"

	def play_Note(self, channel, note):
		"""Play a Note object."""
		velocity = 100
		if hasattr(note, "dynamics"):
			if 'velocity' in note.dynamics:
				velocity = note.dynamics["velocity"]

		self.track_data += self.note_on(channel, int(note), velocity)

	def play_NoteContainer(self, channel, notecontainer):
		"""Play a mingus.containers.NoteContainer."""
		[self.play_Note(channel, x) for x in notecontainer]

	def stop_NoteContainer(self, channel, notecontainer):
		"""Stop playing the notes in the NoteContainer"""
		[self.stop_Note(channel, x) for x in notecontainer]

	def play_Bar(self, channel, bar):
		"""Plays a Bar on channel"""
		for x in bar:
			self.set_deltatime('\x00')
			self.play_NoteContainer(channel, x[2])
			tick = int(round((1.0 / x[1] * 288)))
			self.set_deltatime(self.writeVar(tick))
			self.stop_NoteContainer(channel, x[2])

	def play_Track(self, channel, track):
		"""Plays a Track on channel"""
		instr = track.instrument
		for bar in track:
			self.play_Bar(channel, bar)


	def stop_Note(self, channel, note, velocity = 64):
		self.track_data += self.note_off(channel, int(note), velocity)

	def header(self):
		chunk_size = a2b_hex("%08x" % (len(self.track_data) +\
				len(self.end_of_track())))
		return "MTrk" + chunk_size

	def get_midi_data(self):
		return self.header() + self.track_data + self.end_of_track()

	def midi_event(self, event_type, channel, param1, param2):
		"""Parameters should be given as integers."""
		"""event_type and channel: 4 bits."""
		"""param1 and param2: 1 byte."""
		assert event_type < 128 and event_type >= 0
		assert channel < 16 and channel >= 0
		tc = a2b_hex("%x%x" % (event_type, channel))
		params = a2b_hex("%02x%02x" % (param1, param2))

		return self.delta_time + tc + params

	def note_off(self, channel, note, velocity):
		return self.midi_event(8, channel, note, velocity)

	def note_on(self, channel, note, velocity):
		return self.midi_event(9, channel, note, velocity)

	def reset(self):
		self.track_data = ''
		self.delta_time = '\x00'

	def set_deltatime(self, delta_time):
		self.delta_time = delta_time

	def set_tempo_event(self, bpm):
		"""Calculates the microseconds per quarter note """
		"""and returns tempo event."""
		ms_per_min = 60000000
		mpqn = a2b_hex("%06x" % (ms_per_min / bpm))
		return self.delta_time + "\xff\x51\x03" + mpqn
		
	def writeVar(self, value):
		"""A lot of parameters can be of variable length.
		This writes a value in that format"""
		sevens = self.to_n_bits(value, self.varLen(value))
		for i in range(len(sevens)-1):
			sevens[i] = sevens[i] | 0x80
		return self.fromBytes(sevens)

	def to_n_bits(self, value, length=1, nbits=7):
		"""returns the integer value as a sequence of nbits bytes"""
		bytes = [(value >> (i*nbits)) & 0x7F for i in range(length)]
		bytes.reverse()
		return bytes

	def varLen(self, value):
		"""Returns the the number of bytes an integer will be when
		converted to varlength"""
		if value <= 127:
			return 1
		elif value <= 16383:
			return 2
		elif value <= 2097151:
			return 3
		else:
		       return 4
	def fromBytes(self, value):
		"Turns a list of bytes into a string"
		if not value:
			return ''
		return pack('%sB' % len(value), *value)

def write_Note(file, channel, note, bpm = 120, repeat = 0):
	"""Expects a Note object from mingus.containers and \
saves it into a midi file, specified in file."""
	m = MidiFileOut()
	t = MidiTrack(bpm)
	m.reset()
	m.add_track(t)
	while repeat >= 0:
		t.set_deltatime("\x00")
		t.play_Note(channel, note)
		t.set_deltatime("\x48")
		t.stop_Note(channel, note)
		repeat -= 1
	return m.write_file(file)

def write_NoteContainer(file, channel, notecontainer, bpm = 120, repeat = 0):
	"""Writes a mingus.NoteContainer to a midi file."""
	m = MidiFileOut()
	t = MidiTrack(bpm)
	m.reset()
	m.add_track(t)
	while repeat >= 0:
		t.set_deltatime("\x00")
		t.play_NoteContainer(channel, notecontainer)
		t.set_deltatime("\x48")
		t.stop_NoteContainer(channel, notecontainer)
		repeat -= 1
	return m.write_file(file)

def write_Bar(file, channel, bar, bpm = 120, repeat = 0):
	"""Writes a mingus.Bar to a midi file."""
	m = MidiFileOut()
	m.reset()
	t = MidiTrack(bpm)
	m.add_track(t)
	while repeat >= 0:
		t.play_Bar(channel, bar)
		repeat -= 1
	return m.write_file(file)

def write_Track(file, channel, track, bpm = 120, repeat = 0):
	"""Writes a mingus.Track to a midi file."""
	m = MidiFileOut()
	m.reset()
	t = MidiTrack(bpm)
	m.add_track(t)
	while repeat >= 0:
		t.play_Track(channel, track)
		repeat -= 1
	return m.write_file(file)

if __name__ == '__main__':
	from mingus.containers.Bar import Bar
	from mingus.containers.Track import Track
	b = Bar()
	c = Bar()
	d = Bar()

	b + 'C'
	b + 'E'
	b + 'G'
	b + ['B', 'F']

	c + 'Bb'
	c + 'F#'
	c + 'G#'
	c + 'Db'


	t = Track()
	t + b
	t + c
	write_Bar("testmingus.mid", 1, b, 120, 10)
	write_NoteContainer("testmingus2.mid", 1, [50, 54, 57], 150, 0)
	write_Track("testmingus3.mid", 1, t, 120, 0)