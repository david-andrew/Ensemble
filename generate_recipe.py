##REMOVE THESE LATER####
import pdb
########################


#system related imports
import os
import sys
import shutil
import subprocess

#API imports
import music21
from textgrid import textgrid
from google.cloud import texttospeech


#other tools
import json
# import numpy as np
import struct


# DEBUG = False    #skip the gui file dialog, and use other default settings
# if len(sys.argv) > 1:
args = [arg.lower() for arg in sys.argv[1:]]
VALID = 'valid' in args   #run validation on the audio corpus
SKIP = 'skip' in args           #skip redownloading the words for the song (as in they are there from last time)

def main():
    clean_workspace()
    list_voices()
    create_tts_palette()
    align_phonemes()
    construct_recipe()
    call_matlab()



def clean_workspace():
    """Remove any files from previous runs of this software"""
    if SKIP: return

    print('Removing old files...', end='')
    
    try:
        shutil.rmtree('./speech/voices')    #delete old stuff
        os.mkdir('./speech/voices')         #create empty folder
    except FileNotFoundError:
        #if the folder doesn't exist in the first place, it's okay
        #any other errors should be raised
        pass

    print('Done\n')


def list_voices():
    """create an entry in the recipe for each voice part in the song"""

    parts_list = [part.partName for part in song.parts]  #create a list of the raw part names in the score

    #generate the list of final part names in the score. If a name is repeated, append roman numerals to it
    for part in parts_list:
        if parts_list.count(part) > 1:
            i = 1
            while part + '_' + int_to_roman(i) in recipe:
                i += 1
            part = part + '_' + int_to_roman(i) 
        
        part = part.replace(' ', '_') #ensure no spaces in names, because matlab can't deal with them
        recipe[part] = None


def get_voice_type(part_name):
    """basically convert something like "Soprano II" to just "soprano" """
    types = ['Soprano', 'Alto', 'Tenor', 'Baritone', 'Bass']
    for t in types:
        if t.lower() in part_name.lower():
            return t
    raise Exception('Unrecognized voice part "' + part_name + '"')


def create_tts_palette():
    """Download all of the words used in each voice part for the piece from Google-Cloud-TTS"""
    if SKIP: return
    
    print('Creating Text-to-Speech wav palettes')
    for voice_name, part in zip(recipe, song.parts):
        voice_type = get_voice_type(voice_name)
        dictionary = construct_dictionary(part)
        download_words(dictionary, voice_name, tts_voices[voice_type])
        print('')

    print('Done Creating Text-to-Speech sample palettes\n')


def align_phonemes():
    """Use Montreal Forced Aligner to determine timing information of phonemes in each word"""
    print('Aligning phonemes for all voices')
    
    for voice_name in recipe:
        print('aligning voice ' + voice_name)
        

        #only run manually when songs have lots of errors during alignment
        if VALID:
            #run validation on phoneme alignment before attempting to align
            validate = ['speech/forced_alignment/montreal-forced-aligner/bin/mfa_validate_dataset', 
            'speech/voices/'+voice_name+'/', 
            'speech/forced_alignment/librispeech-lexicon.txt', 
            'english']

            subprocess.check_call(validate)


        command = ['speech/forced_alignment/montreal-forced-aligner/bin/mfa_align', 
        'speech/voices/'+voice_name+'/', 
        'speech/forced_alignment/librispeech-lexicon.txt', 
        'english', 
        'speech/voices/'+voice_name+'/aligned/']

        subprocess.check_call(command)

        print('') #newline in between each call output

    print('Done aligning phonemes for all voices\n')


def construct_recipe():
    """convert the parsed musicxml file into a sort of streamed music json representation"""
    
    print('Constructing recipe...')

    #for doing proper tempo, before extracting parts, create a tempo sequence that contains every tempo and the beat on which they occur. then while collecting each voice part, keep track of the beat, and insert the tempo changes into the sequences at the right points
    #need to be careful though so that things remain aligned when doing this

    for voice_name, part in zip(recipe, song.parts):
 
        #set up state variables for this voice part
        sequence = []                                                       #empty list to hold the sequence of sounds made by this voice
        tempo = 60                                                          #default tempo assumed to be 60 beats per minute
        dynamics = 'mf'                                                     #default dynamics. for now, dynamics are being ignored


        #list of useful elements:
        # music21.instrument.Instrument     e.g. [soprano, alto, tenor, base]
        # music21.tempo.MetronomeMark       e.g. tempo.number returns BPM
        # music21.note.Note
        # music21.note.Rest
        # music21.dynamics.Dynamic
        # music21.chord.Chord   -> probably advanced where parts overlap
        # ?music21.bar.Repeat   -> specifies flow?
        # ?music21.bar.Barline  -> I think specifies ending 1 vs ending 2

        for element in part.flat: #


            #IGNORE THIS WHILE TEMPO MARK IS NOT CONTINUED ACCROSS ALL PARTS
            #probably fix this by doing a pass over the piece and inserting the tempo at every voice when it comes up in the top line
            #i.e. while loop count out beats in the top line, and then when a tempo item is reached, count that far in the other parts and insert it
            # if type(element) is music21.tempo.MetronomeMark:
            #     tempo = element.number  #set the current tempo to what is listed


            if type(element) is music21.note.Note:

                word, start, stop, vstart, vstop, lsust, rsust, structure = segment_word(element, voice_name) #get information needed to crop the word correctly

                sequence.append({
                    'volume':   volume_map[dynamics],               #volume (maybe replace with a key velocity). volume of 0 indicates a rest
                    'duration': tempo / 60 * element.quarterLength, #duration in seconds
                    'pitch':    element.pitch.frequency,            #note pitch in Hz
                    'word': word,                                   #what is the whole word this note comes from
                    'structure': structure,                         #phonotactic structure, e.g. ccvcc, etc. This may be used to allow space for consonants during pitch shifting/stretching?
                    'start': start,                                 #time that this syllable occurs in the sound file
                    'stop': stop,                                   #time that this syllable ends in the word sound file
                    'vstart': vstart,                               #time that the vowel of the syllable starts in the sound file
                    'vstop': vstop,                                 #time that the vowel of the syllable ends in the sound file
                    'lsust': lsust,                                 #is this syllable sustained from the previous note
                    'rsust': rsust,                                 #is this syllable sustained into the next note
                })
                


            if type(element) is music21.note.Rest:
                sequence.append({
                    'volume': 0.0,                                  # 0 pitch indicates rest
                    'duration': tempo / 60 * element.quarterLength       # duration of rest in seconds
                })


            if type(element) is music21.dynamics.Dynamic:
                dynamics = element.value #update the dynamics with the current dynamics value


        recipe[voice_name] = sequence   #put the sequence for the voice part into the recipe dictionary

    print('done')




def call_matlab():
    """pass the recipe to matlab which will use the word samples to create the audio file performance"""

    recipe_path = 'recipes/' + song_name + '.json'

    #save the recipe to a json file
    with open(recipe_path, 'w') as out:
        json.dump(recipe, out)

    #print_recipe()

    #call matlab from the command line to construct the performance with the recipe
    #in the future want an encapsulated MEX script so that anyone can use this tool without matlab    
    #command = ['matlab', '-nodisplay', '-nosplash', '-r', ('''"perform('recipes/%s')"''' % (song_name + '.json'))]
    command = ['bash', 'call_matlab.bash', song_name + '.json']
    subprocess.call(command)


    #when matlab is finished, open the song with an audio player, e.g. vlc player
    command = ['vlc', '--play-and-exit', 'output/' + song_name + '.wav']
    subprocess.call(command)




########INSERT OTHER HELPER METHODS FOR CONSTRUCTING THE RECIPE############


def int_to_roman(input):
   """Convert an integer to Roman numerals. from: https://code.activestate.com/recipes/81611-roman-numerals/"""
   if type(input) != type(1):
      raise TypeError("expected integer, got %s" % type(input))
   if not 0 < input < 4000:
      raise ValueError("Argument must be between 1 and 3999")   
   ints = (1000, 900,  500, 400, 100,  90, 50,  40, 10,  9,   5,  4,   1)
   nums = ('M',  'CM', 'D', 'CD','C', 'XC','L','XL','X','IX','V','IV','I')
   result = ""
   for i in range(len(ints)):
      count = int(input / ints[i])
      result += nums[i] * count
      input -= ints[i] * count
   return result


def construct_dictionary(part):
    """construct a dictionary of words from the voice part"""
    dictionary = set([])
    for element in part.flat:
        if type(element) is music21.note.Note:
            word, _ = get_current_word(element)
            dictionary.add(word)

    return dictionary


def get_current_word(note):
    #TODO -> rewrite this function so that it tells you the following:
    #1) what the entire word is that is being sung (needs to include ' so that "I'll" doesn't become "ill")
    #2) what syllable is being sung (0th, 1st, 2nd, etc.)
    #3) something to manage sustained notes. basically it should track this notes vowel, and whether any preceeding and proceeding consonants should be sung based on the syllable and surrounding notes
    #   for this, I think you could potentially look at if preceeding/proceeding notes are none, which indicates how sustain might be necessary.
    #
    #Also for overhauling, this method is pretty brittle and fails in a lot of cases, so I think I ought to write the new one with lots of examples of musicxml files
    #I'm also thinking that this should perhaps be split into multiple methods. 1 that extracts a lyrics/notes sequence for the word, and one that provides the more specific information about the current syllable?
    #basically the note sequence could easily be used to determine which phonemes out of the syllable need to be used


    """given a note in a stream, get the entire word that makes it. also return how many syllables the word is split into, and how many"""
    word = ''                                               #construct the entire word that the syllable comes from
    # sustained = False                                       #if a syllable is sustained over multiple notes, we only want the vowel portion of the note
    partitions = 0
    cur = note
    index = 1 if cur.lyrics else 0                          # 0 accounts for the current note starting on a sustained syllable

    #compute index by scanning backwards to the start of the word
    while not cur.lyrics or cur.lyrics[0].syllabic not in ['single', 'begin']:         # while not either of the word start syllabics
        cur = get_prev(cur)                                # scan backwards
        if cur.lyrics: index += 1                           # update index if a new syllable is encountered

    #construct word and count partitions
    if cur.lyrics[0].syllabic == 'single':
        word = cur.lyric
        partitions = 1
    else: # 'begin'->(optional)'middle'->'end'
        while True:                                         # scan forward until the end of the word
            if cur.lyrics:                                  # check if current note has syllable (None indicates previous is sustained)
                word += cur.lyric                           # add syllable onto the whole word
                partitions += 1                             # keep track of how many syllables are in the word
                if cur.lyrics[0].syllabic == 'end': break   # 'end' indicates last syllable
            cur = get_next(cur)                             # get the next syllables

    word = remove_punctuation(word)
    # syllable = remove_punctuation(note.lyric)

    return word, index


def remove_punctuation(word):
    """return a (lowercase) string without any punctuation"""
    if word is None: word = ''
    word = [char.lower() for char in word if char.lower() in "abcdefghijklmnopqrstuvwxyz'"] #replace this with the character set for the language. apostrophe included for contractions, e.g. I'll, fav'rite, etc.
    word = (''.join(word)).lower()
    return word


def get_next(note):
    """return the next note object in the sequence (skip over other objects, e.g. rests, barlines, etc.)"""
    while note is not None:
        note = note.next()
        if type(note) == music21.note.Note or type(note) == music21.note.Rest:
            return note
    raise ValueError('Get next note was not able to find a previous note')


def get_prev(note):
    """return the previous note object int the sequence"""
    while note is not None:
        note = note.previous()
        if type(note) == music21.note.Note or type(note) == music21.note.Rest:
            return note
    raise ValueError('Get previous note was not able to find a previous note')


def download_words(dictionary, voice_name, tts_speaker, speed=110):
    """download all of the words specified in the dictionary for the given voice part"""
    for word in dictionary:
        print('Downloading "' + word + '" for ' + str(voice_name))

        # Set the text input to be synthesized
        ssml = '<speak><prosody rate="' + str(speed) + '%">' + word + '</prosody></speak>' 
        synthesis_input = texttospeech.types.SynthesisInput(ssml=ssml)#(text=word)

        # Perform the text-to-speech request on the text input with the selected
        # voice parameters and audio file type
        voice_spec = texttospeech.types.VoiceSelectionParams(language_code='en-GB', name=tts_speaker)
        response = tts_client.synthesize_speech(synthesis_input, voice_spec, audio_config)
        waveform = clip_silence(response.audio_content)

        #save the audio file to disk for use in matlab
        directory = 'speech/voices/' + voice_name + '/'

        if not os.path.exists(directory):
            os.makedirs(directory)

        #save the audio wav file
        with open(directory + word + '.wav', 'wb') as out:
            # print('saving track "' + word + '.wav' '"')
            out.write(waveform)

        #save the transcript for the forced aligner
        with open(directory + word + '.lab', 'w') as out:
            out.write(word.upper())

def clip_silence(waveform):
    """return a waveform with no leading or trailing silence"""
    header = waveform[:44]
    sound = waveform[44:]

    start = 0
    while sound[start] == 0 and sound[start+1] == 0: #linear pcm means each sample is 2 bytes
        start += 2

    stop = len(sound) - 2
    while sound[stop] == 0 and sound[stop + 1] == 0:
        stop -= 2

    header = header[:40] + struct.pack('I', stop-start) #modify the size in the header based on the new length of the sample
    return header + sound[start:stop]


def segment_word(note, voice_name):
    """look at the syllables of the lyrics, and combined with the phonetic alignment (mainly phonetics for syllable counting), determine which portion of the word represents the current note"""
    word, index = get_current_word(note)

    #Determine left and right sustains. sustained notes should start from vowel rather than necessarily the first phoneme
    #determine if this note was sustained into from the previous note
    lsust = note.lyric is None 
    
    #determine if this note sustaines into the next note
    try:
        rsust = get_next(note).lyric is None
    except:
        rsust = False



    if index == 0: 
        print('Index was 0 as oppsed to >0. not sure what to do in this case. check word/surroundings')
        pdb.set_trace()

    alignment = textgrid.TextGrid();
    alignment.read('speech/voices/' + voice_name + '/aligned/' + word + '.TextGrid')

    
    phonemes = [p for p in alignment.getFirst('phones') if p.mark not in ['sil', 'sp', '']] #'spn' seems to be an error occurred on readout

    
    structure = ''
    for phoneme in phonemes:
        p = phoneme.mark.strip('0123456789').upper()
        if p in vowels:
            structure += 'v'
        elif p in consonants:
            structure += 'c'
        else:
            pdb.set_trace()
            raise Exception('Unclear phoneme type encountered: ' + str(phoneme))

    syllables = [s for s in structure.replace('v', 'v.').split('.') if s != '']
    # print(syllables, word, index)
    if 'v' not in syllables[-1]:
        syllables[-2] += syllables[-1]
        syllables = syllables[0:-1] 

    
    rcount = len(''.join(syllables[:index]))
    lcount = rcount - len(syllables[index-1])
    syllable = phonemes[lcount:rcount] #get the current syllable
    start = float(syllable[0].minTime)
    stop = float(syllable[-1].maxTime)
    
    vowel = syllable[syllables[index-1].find('v')]
    vstart = float(vowel.minTime)
    vstop = float(vowel.maxTime)

    return word, start, stop, vstart, vstop, lsust, rsust, structure 


def print_recipe():
    """convenience function for displaying a recipe"""
    for voice, part in recipe.items():
        print(voice)
        for note in part:
            print(note)
        print()




# Set up global variables for use during recipe generation process

#set the path to the service key for accessing cloud-text-to-speech
os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = '/home/david/.ssh/HackingHarmony-929ff06750d6.json'

#global client and audio configuration
tts_client = texttospeech.TextToSpeechClient()
audio_config = texttospeech.types.AudioConfig(audio_encoding=texttospeech.enums.AudioEncoding.LINEAR16)


#tts_speaker = voice_map[element.instrument.instrumentName]
#British English Voices
tts_voices = {
    'Soprano':  'en-GB-Wavenet-A',  #en-US-Wavenet-F
    'Alto':     'en-GB-Wavenet-C',  #en-US-Wavenet-C, en-US-Wavenet-E, 
    'Tenor':    'en-GB-Wavenet-D',  #en-US-Wavenet-A #en-GB-Wavenet-B doesn't seem to work very well, even though it sounds like a temor, so using the bass voice of D
    'Baritone': 'en-GB-Wavenet-D',
    'Bass':     'en-GB-Wavenet-D',  #en-US-Wavenet-B, en-US-Wavenet-D
}

#American English Voices
# tts_voices = {
#     'Soprano':  'en-US-Wavenet-F',  #en-US-Wavenet-F
#     'Alto':     'en-US-Wavenet-C',  #en-US-Wavenet-C, en-US-Wavenet-E, 
#     'Tenor':    'en-Us-Wavenet-A',  #en-US-Wavenet-A
#     'Baritone': 'en-US-Wavenet-B',
#     'Bass':     'en-US-Wavenet-D',  #en-US-Wavenet-B, en-US-Wavenet-D
# }

#map dynamics mark to volume (perhaps convert these to midi key velocity?)
volume_map = {
    'ppp':  0.125, 
    'pp':   0.25,
    'p':    0.375,
    'mp':   0.50,
    'mf':   0.675,
    'f':    0.75,
    'ff':   0.875,
    'fff':  1.0
}


#ARPABET list of vowels and consonants for figuring out how to split up words
#The Montreal Forced Aligner will contain numbers after each phoneme for word accents, which need to be culled
vowels = set(['AA', 'AE', 'AH', 'AO', 'AW', 'AX', 'ARX', 'AY', 'EH', 'ER', 'EY', 'IH', 'IX', 'IY', 'OW', 'OY', 'UH', 'UW', 'UX'])
consonants = set(['B', 'CH', 'D', 'DH', 'DX', 'EL', 'EM', 'EN', 'F', 'G', 'HH', 'JH', 'K', 'L', 'M', 'N', 'NG', 'NX', 'P', 'Q', 'R', 'S', 'SH', 'T', 'TH', 'V', 'W', 'WH', 'Y', 'Z', 'ZH'])


#dictionary to be filled with song stream elements(e.g. notes, rests, etc.)
recipe = {} 



# if not DEBUG:
#def gui_open_file():
"""Use a GUI to get the path to the desired music xml file"""
import tkinter
from tkinter import filedialog
tkinter.Tk().withdraw()

#save the path and parsed song into the global path variables

file_path = filedialog.askopenfilename(
    initialdir='./sheet_music/', 
    title='Open Sheet Music', 
    filetypes = (("MusicXML File","*.xml"),("Compressed MusicXML File","*.mxl"))
)
if file_path is ():
    raise Exception("You must specify a file to continue")
song = music21.converter.parse(file_path)
song_name = file_path.split('/')[-1][0:-4]
print('Creating music recipe for "' + song_name + '"\n')
# else:
#     print('(RUNNING IN DEBUG MODE--DEFAULT SETTINGS WILL BE USED)')
#     file_path = './sheet_music/Danny_Boy.xml'
#     song = music21.converter.parse(file_path)
#     song_name = "Danny_Boy"
#     print('Creating music recipe for default song "Danny Boy"\n')




if __name__ == "__main__":
    main()

