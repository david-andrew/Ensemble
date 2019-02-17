function [lzero, rzero] = find_zero_cross(sample, index)
%returns the nearest left and right indices of zero crossings in the sample


center_sign = sign(sample(index)); %is the sample positive or negative at the index

lzero = index - 1;
try
    while sign(sample(lzero)) == center_sign
        lzero = lzero - 1;
    end
catch
    lzero = - 1;    %could not find a zero index on the left
end

rzero = index + 1;
try
    while sign(sample(rzero)) == center_sign
        rzero = rzero + 1;
    end
catch
    rzero = - 1;    %could not find a zero index on the right
end
    
%convention is that both zero crossing indices should be listed with the
%same sign. so we assume that all zero crossings reference the left point
%of the zero crossing pair of points (as typically the cross will occur
%between points, rather than at a single point)
rzero = rzero - 1;