function out = add_reverb(voice, voice_FS, scale)
%add reverb to a sound file

[H FS] = audioread('reverb/s1_r1_b.wav');          %read impulse response sample
H = interp1(1:length(H), H, linspace(1, length(H), floor(length(H)/scale)), 'spline');

if FS >= voice_FS
    downsample = FS / voice_FS;             %convert between sample rates
    H = interp1(1:length(H), H(:,1), 1:downsample:length(H));                   %downsample the impulse response to be the same frequency as the voice clip
    voice = voice(:,1);                     %take the left channel
else
    downsample = voice_FS / FS;
    voice_FS = FS;
    H = H(:,1);                             %take the left channel
    voice = interp1(1:length(voice), voice(:,1), 1:downsample:length(voice));   %downsample the voice sample to the same frequency as the impulse response
end

out = conv(voice, H, 'full');      %add reverb
