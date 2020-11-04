function [c1,c2,z1,z2]=split(c,z,index);% split                     - split coordinates in two sets (Jan 1,2001)%% Split the matrix of coordinates and the  associated matrix of% values into two sets according to the index vector that refers% to line numbers in c.%% SYNTAX :%% [c1,c2,z1,z2]=split(c,z,index);%% INPUT :%% c    n by d       matrix of coordinates, where d is the dimension%                   of the space.% z    n by k       matrix of values, where each line refers to a set%                   of values at the corresponding c coordinates.%% OUPUT :%% c1   ni by d      matrix of coordinates, where ni is the length of%                   the index vector.% c2   (n-ni) by d  matrix of coordinates.% z1   ni by k      matrix of values.% z2   (n-ni) by k  matrix of values.%% NOTE :%% It is possible to specify an additional index vector for c, taking% integer values from 1 to nv. The values in this index specifies which% one of the nv variable is known at each one of the corresponding% coordinates. The c matrix of coordinates and the index vector are then% grouped together using the MATLAB cell array notation, so that c={c,index}.% This allows to perform the same coordinate transformation at once on a set% of possibly different variables. The output matrices c1 and c2 are then% cell arrays too, with the index splitted accordingly.if ~iscell(c),  c1=c(index,:);  z1=z(index,:);  c2=c;  c2(index,:)=[];  z2=z;  z2(index,:)=[];else  c1={c{1}(index,:),c{2}(index)};  z1=z(index,:);  c2=c;  c2{1}(index,:)=[];  c2{2}(index)=[];  z2=z;  z2(index,:)=[];end;