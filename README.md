# System Requirments:
1. Python3
    * google cloud text to speech
    * music21
    * textgrid
2. Matlab
    * digital signals processing toolbox


# How to use:
```
$ python3 generate.py [optional flags]
```
select a valid MusicXML file from the dialog, and then the song performances will be placed in the `/output` folder. 

Several command-line flags can be used to affect how the program runs:
* `--validate` - Run validation on speech alignment (typically the program will crash the first time running a new song without this option)
* `--no-tts` - Skip the downloading the words from the song. Speech files are cached, so this typically isn't necessary
* `--no-align` - Skip the speech audio alignment to phoneme information
* `--reset-cache` - Delete all previously downloaded speech audio files that have been cached
* `--no-text` - Replace all lyrics with the vowel 'Ah'

# Examples:
The sheet music (MusicXML) for several pieces is available in the `/sheet_music` folder. Example performances (WAV) of the pieces are available in the `/output/demos` folder

# To-Do:
* fix the extend method so that it is always a smooth transition into the the stretched center of the vowel. It works most of the time, but there are still a lot of cases where it does not get a proper pitch for the vowel. Perhaps look at the mean pitch in the vowel, and try to match that rather than just whatever period we landed on.
* look into dynamics control based on the intensity of the waveform
* make it so that parts can have multiple notes at the same time (chords I think?)
* make it so that multiple voices can be on the same line at a time
* when stitching syllables, make each boundary a zero crossing (if next word derivative at zcc is wrong, invert the sound signal)
* in python, detect when the same syllable is repeated over multiple notes (i.e. redo the function for extracting words and determining what syllable the of the word (according to the music) is being sung)
* figure out why the forced aligner fails in a lot of cases
* make each voice part use multiple singers
* add vibratto and tremolo to voices, esp for sustained notes
* for time stretching samples, look into some method to evaluate the quality of the period selected. Sometimes it sounds like an artifact is selected as part of the period, so perhaps the method could be to sweep over the vowel and pull out a period that is most average
* look into integrating audiveris for optical music recognition, so that the software can do a full end to end performance, starts with a PDF of sheet music, and ending with the audio recording
* move all signal processing from matlab to python (i.e. replace pitch detection, pitch shifting, and time stretching, with numpy and probably c++ libraries)