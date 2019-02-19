# System Requirments:
1. Python
    * google cloud text to speech
    * music21
    * textgrid
2. Matlab
    * digital signals processing toolbox


# How to use:
```
$ python3 generate_recipe.py
```
select a valid MusicXML file from the dialog, and then the song performances will be placed in the `/output` folder. 

# Examples:
The sheet music (MusicXML) for several pieces is available in the `/sheet_music` folder. Example performances (WAV) of the pieces are available in the `/output` folder

# To-Do:
* test sustained notes that combine to be a single note (e.g. quarter tied to eight vs dotted quarter). should produce identical notes in both cases. look into combining such notes in the recipe back into a single note
* (possibly same cause as above) figure out why there are sometimes gaps in sound signals placed. sound should be connected between words and syllables unless there is a rest
* look into dynamics control based on the intensity of the waveform
* make it so that parts can have multiple notes at the same time (chords I think?)
* make it so that multiple voices can be on the same line at a time
* when stitching syllables, make each boundary a zero crossing (if next word dirivative at zcc is wrong, invert the sound signal)
* in python, detect when the same syllable is repeated over multiple notes (i.e. redo the function for extracting words and determining what syllable the of the word (according to the music) is being sung)
* figure out why the forced aligner fails in a lot of cases
* make each voice part use multiple singers
* add vibratto and tremolo to voices, esp for sustained notes
* look into ways for not redownloading the same voice clip multiple times, e.g. keep track of which voices downloaded which words, and store them centrally, and then copy them into each parts' folder as needed
* for time stretching samples, look into some method to evaluate the quality of the period selected. Sometimes it sounds like an artifact is selected as part of the period, so perhaps the method could be to sweep over the vowel and pull out a period that is most average
