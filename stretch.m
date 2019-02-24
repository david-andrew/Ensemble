function [repeat, index] = stretch(in, fs, loc, dur)
%time strech sample from specific location to specified total length
%this function creates copies of a whole period of the sample
%
%Inputs:
% "in" is the sound sample
% "fs" is the sample frequency in Hz
% "loc" is the index in the sample to stretch
% "dur" is the desired resulting duration of the repeating sample in seconds
%
%Outputs:
% "repeat" is a repeating waveform that can be inserted in the "in" sample
% "index" is the index that "repeat" can be inserted into "in"
%
% example usage:
%   [sample, fs] = audioread('file.wav')
%   [repeat, index] = stretch(sample, fs, 0.5, 5)
%   stretched = [sample(1:index), repeat, sample(index:end)];
%   %note that (length(repeat) + length(in)) * fs = dur


if sign(in(loc)) == sign(in(loc+1))
    error('Error: currently require loc specified to be a zero crossing point');
end
index = loc;    %for now assuming we are at a zero cross



%compute the pitch of the sample
[f0,idx] = pitch(in,fs, 'Method', 'PEF', 'MedianFilterLength', 25);
idx = idx(~isnan(f0));
f0 = f0(~isnan(f0));

%for now, assume we are at a zero crossing for the specified index

%determine the pitch at the location to be stretched
i = 1;
while idx(i+1) < loc
    i = i + 1;
end

period_cycles = fs/f0(i);   %compute the period (samples/cycle) at the current position
period_length = 1/f0(i);    %compute the period (seconds/cycle) at the current position


raw_pattern = in(idx(i):idx(i+2));                  %select part of the signal at the location we want to extend
[~, rzero] = find_zero_cross(raw_pattern, 1);   %find the first zero cross in the signal portion

left = rzero; %lzero will probably be -1, so use the first zero cross to the right

[lzero, rzero] = find_zero_cross(raw_pattern, round(period_cycles));

%select the best one based on abs(dur - (lzero-left)/fs) and abs(dur -
%(rzero-left)/fs)

lsize = (lzero-left)/fs;
rsize = (rzero-left)/fs;

%select the zero crossing index that is closest to the current period
if abs(lsize - period_cycles) < abs(rsize - period_cycles)
    right = lzero;
else
    right = rzero;
end


%create a repeating array out of a single period of the wavform
num_cycles = round(dur / period_length);
repeat = repmat(raw_pattern(left+1:right+1), num_cycles, 1);

