function colorploths(c,z,map,Property,Value,zrange,nh,ns,standAlone);% colorploths  - plot of hard+soft values at 2-D coordinates using colormaps (Sep 7,2012)%% Plot colored symbols for the values of a vector at a set of two dimensional% coordinates. The function uses a colormap such that the color displayed at% these coordinates is a function of the corresponding values.% Differs from colorplot in that it accepts datasets with hard and soft data% and uses different symbols to represent each type of data. If soft data are% included in the input vector z, they must be represented by a single value.%% SYNTAX :%% colorplot(c,z,map,Property,Value,zrange); %% INPUT :%% c           n by 2 matrix of coordinates for the locations to be displayed.%                    Each line corresponds to the vector of coordinates at a location,%                    so the number of columns is equal to two.% z           n by 1 column vector of values to be coded as colors.% map         string that contains the name of the color map to be used. See the help%                    about graph3d.m for more information on color maps. E.g., map='hot'%                    yields a black-red-yellow-white gradation of colors.% Property    1 by k cell array where each cell is a string that contains a legal name%                    of a plot object property. This variable is optional, as default%                    values are used if Property is missing from the input list of variables.%                    Execute get(H), where H is a plot handle, to see a list of plot object%                    properties and their current values. Execute set(H) to see a list of%                    plot object properties and legal property values. See also the help%                    for plot.m.% Value       1 by k cell array where each cell is a legal value for the corresponding plot%                    object property as specified in Property.% zrange      1 by 2 optional vector specifying the minimum and maximum value of%                    the range of z values scaled in the color map.  %                    The default is zrange=[min(z) max(z)]%                    If zrange is empty then the default values are used.% nh          scalar Number of hard data in first nh lines of c, z.% ns          scalar Number of soft data after first nh lines of c, z.% standAlone  scalar Flag to designate whether colorplot is part of another plot%                    Has value of 1 by default for any input value, except%                    NaN or 0.% NOTE :% % For example,%% colorplot(c,z,'hot',Property,Value);%% where Property={'Marker','MarkerSize','MarkerEdgeColor'};%       Value ={'^',10,[0 0 0]};%% will plot red triangles with a black border that have a MarkerSize value% equal to 10. By default, colorplot(c,z) will use circles with a MarkerSize% equal to 10 and with a MarkerEdgeColor equal to the default color.if nargin==2,  map='hot';end;if nargin>3,  if ~iscell(Property),    Property={Property};    Value={Value};    noptions=1;  else    noptions=length(Property);  end;else  noptions=0;end;if nargin<6 || isempty(zrange)  zrange=[min(z(:)) max(z(:))];end;% If no discrimination between hard/soft data, consider all as hard data.nz = length(z);if nargin<7 || isnan(nh)  nh = nz;  nDataSpecd = 0;else  nDataSpecd = 1;  if nh>nz    % If more asked than specified, ignore excess    ns = 0;    nh = nz;  endend;if nargin<8 || isnan(ns)  ns = 0;  nDataSpecd = 0;else  nDataSpecd = 1;  if ns>nz    % If more asked than specified, ignore excess    ns = nz;  end  end;if (nDataSpecd &&&& nh+ns>nz) % If more asked than specified, ignore excess soft  ns = nz-nh;endif (nargin<9 |||| (~isnan(standAlone) &&&& standAlone~=0))  standAlone = 1;end[n,d]=size(c);if d~=2, error('c must be a n by 2 matrix'); end;if size(z,2)~=1, error('z must be a column vector'); end;if size(z,1)~=n, error('c and z must have the same number of rows'); end;c=c(~isnan(z),:);z=z(~isnan(z),:);if length(z)==0 return; endtest=(ishold==1);minz=zrange(1);maxz=zrange(2);if maxz==minz,  error('At least two values of z must be different');end;colormap(map);map=colormap;nc=size(colormap,1);n=length(z);for i=1:n,  index=((z(i)-minz)/(maxz-minz))*(nc-1)+1;    if index<1    Color=map(1,:);  elseif index>size(map,1)    Color=map(end,:);  else          indexl=floor(index);    indexu=ceil(index);    if indexl==indexu,      Color=map(index,:);    else      Color(1)=interp1([indexl indexu],[map(indexl,1) map(indexu,1)],index);      Color(2)=interp1([indexl indexu],[map(indexl,2) map(indexu,2)],index);      Color(3)=interp1([indexl indexu],[map(indexl,3) map(indexu,3)],index);    end;  end    if (i <= nh)    a=plot(c(i,1),c(i,2),'o');    set(a,'MarkerSize',10);    set(a,'MarkerFaceColor',Color);    for j=1:noptions,      set(a,Property{j},Value{j});    end;  else    a=plot(c(i,1),c(i,2),'^');    set(a,'MarkerSize',10);    set(a,'MarkerFaceColor',Color);    for j=1:noptions,      set(a,Property{j},Value{j});    end;  end  hold on;end;%% Set the color axis for the colorbar%if (~isnan(standAlone) &&&& standAlone~=0)  ax=axis;  patch(0,0,0);    % Somehow this helps so the next line has an effect  caxis(zrange);  axis(ax);endif test==0,  hold off;end;