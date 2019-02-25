function [] = perform(raw_recipe_path)
%perform creates wav performace of the specified song


homepath = pwd;

% [filename filepath] = uigetfile([recipe_path '*.json'],'Recipe');
[filepath,name,ext] = fileparts(raw_recipe_path);
recipe = jsondecode(fileread([homepath '/' filepath '/' name ext]));

audioOut = zeros(100000000,1); %preallocate a large chunk of memory
FS = 24000; %current playback sample rate

%pitch and speed modifiers
speed_up = 1.0; %2.0 %playback speed_up times faster than the piece specified
pitch_up = 1.0; %0.85

fields = fieldnames(recipe);
num_voices = numel(fields);
for f = 1:num_voices
    sample = 1;
    voice_name = fields{f};
    fprintf('creating track for %s\n', voice_name);
    sequence = recipe.(fields{f});
    for i = 1:length(sequence)
        note = sequence(i); 
        try 
            note = note{1}; %this is here because matlab is stupid
        catch    
        end
        
        note.duration = note.duration / speed_up;
        if note.volume == 0
            sample = sample + note.duration * FS; %skip the samples that are a rest 
        else
            %set the word to be the correct pitch & length

            [wordIn, fs] = audioread([homepath '/speech/voices/' voice_name '/' note.word '.wav']);
%             wordIn = strip_padding(wordIn); %can't strip padding without
%             adjusting the locations of syllable timing. future todo
            
            %handle duration stretching based on if the left and/or right
            %portions of the note are sustained
            
            %center_index = floor((note.vstart + note.vstop) * fs / 2);%index of the center of the vowel for possible stretching. index from the entire word, not the left + right sample only
            center_index = floor(interp1([0 1], [note.vstart note.vstop], 0.6) * fs);
            [center_index, ~] = find_zero_cross(wordIn, center_index); %get the index of the nearest zero cross
            
            if ~note.lsust
                %include the whole left half, including consonants
                left = wordIn(max(floor(note.start * fs), 1):center_index);
            else
                %crop any consonants on the left half of the word
                left = wordIn(max(floor(note.vstart * fs), 1):center_index);
            end
            
            
            if ~note.rsust
                %include the whole right half, including consonants
                right = wordIn(center_index:floor(note.stop * fs));
            else
                %crop any consonants on the right half of the word
                right = wordIn(center_index:floor(note.vstop * fs));
            end
                        
            
            cur_duration = (length(left) + length(right)) / fs; %how long is the current raw syllable
            
            if cur_duration > note.duration
                %downsample to the correct duration
%                 if note.lsust && note.rsust
%                     error('cannot squich note that is sustained on both sides');
%                 end
                wordIn = squish([left; right], fs, note.duration);   
            else
                %copy stretch the vowel up to the right duration
                center = stretch(wordIn, fs, center_index, note.duration - cur_duration);
                wordIn = [left; center; right];
                wordIn = squish(wordIn, fs, note.duration); %resample so the note is exactly the rigth duration
            end
            
%             if strcmp(note.word, 'up')
%                 1;
%             end
                    
            
            %compute the pitch of the sample
            [f0,idx] = pitch(wordIn,fs, 'Method', 'PEF', 'MedianFilterLength', 25);
            idx = idx(~isnan(f0));
            f0 = f0(~isnan(f0));
            idx = [1; idx; length(wordIn)]; %add indices at 1 and end, so that the entire word is pitch shifted
            f0 = [f0(1); f0; f0(end)];
            f_target = note.pitch;
            n_shift = (12/log(2)) .* log(f_target ./ f0 .* pitch_up);

            % pitch shift with ratios
            wordOut = zeros(length(wordIn), 1);
            for j = 1:length(idx)-1
                start = idx(j);
                stop = idx(j+1);
                shift = n_shift(j);
                wordOut(start:stop) = shiftPitch(wordIn(start:stop),shift,0.01,fs);
            end
            
            
            %apply the current dynamics to the part
            wordOut = wordOut * note.volume / (mean(abs(wordOut)) * 2);


            audioOut(sample:sample+length(wordOut)-1) = audioOut(sample:sample+length(wordOut)-1) + wordOut ./ num_voices;
            sample = sample + length(wordOut);
        end
    end
end


%truncate the remaining zeros on the end of the track
start = 1; stop = length(audioOut);
while audioOut(start) == 0
    start = start + 1;
end
while audioOut(stop) == 0
    stop = stop - 1;
end


audioOut = audioOut(start:stop); %chop off extra padded sound

% fprintf('Adding reverb to performance\n');
% audioOut = add_reverb(audioOut, FS, 1);

%determine the path to write the file to (ensuring not to overwrite existing files)
outpath = [homepath '/output/' name '.wav'];
i = 1;
while exist(outpath, 'file') == 2
    outpath = [homepath '/output/' name ' (' int2str(i) ')' '.wav'];
    i = i + 1;
end


audiowrite(outpath, audioOut, FS);

if ~usejava('desktop')
    exit %make matlab quit in the terminal, to return control to python
end