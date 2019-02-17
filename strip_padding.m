function out = strip_padding(in)

thresh = 0.001;

%remove any leading zeros
start = 1;
while abs(in(start)) < thresh
    start = start + 1;
end

stop = length(in);
while abs(in(stop)) < thresh
    stop = stop - 1;
end

out = in(start:stop);