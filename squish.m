function [out] = squish(in, fs, dur)
%resample the sound so that it has a desired shorter duration
%uses cubic spline interpolation to resample. (potentially change this)
%
%Inputs:
% "in" is the sound sample
% "fs" is the frequency in Hz
% "dur" is the desired duration in seconds
%
%Outputs:
% "out" is the shorter resampled sound

stretch_factor = dur / (length(in) / fs);
out = interp1(1:length(in), in, ...
    linspace(1, length(in), length(in) * stretch_factor), 'spline')';

