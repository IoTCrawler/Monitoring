function [d,V,o]=vario(c,Z,cl,method,options);% vario                     - multivariate variogram estimation (Jan 1,2001)%% Estimate the variograms and cross variograms for a set of% variables which are known at the same set of coordinates. %% SYNTAX :%% [d,V,o]=vario(c,Z,cl,method,options);%% INPUT : %% c         n by d       matrix of coordinates for the locations where the%                        values are known. A line corresponds to the vector%                        of coordinates at a location, so the number of columns%                        is equal to the dimension of the space. There is no%                        restriction on the dimension of the space.% Z         n by nv      matrix of values for the variables. Each line is%                        associated with the corresponding line vector of%                        coordinates in the c matrix, and each column corresponds%                        to a different variable.% cl        nc+1 by 1    vector giving the limits of the distance classes that are%                        used for estimating the variograms and cross variograms.%                        The distance classes are open on the left and closed on%                        the right. The lower limit for the first class is >=0.% method    string       that contains the name of the method used for computing%                        the distances between pairs of locations. method='kron'%                        uses a Kronecker product, whereas method='loop' uses a loop%                        over the locations. Using the Kronecker product is faster%                        for a small number of locations but may suffer from memory%                        size limitations depending on the memory available, as it%                        requires the storage of a distance matrix. The loop method%                        may be used whatever the number of data locations is and%                        must be used if an Out of Memory error message is generated.%                        Both  methods yield exactly the same estimates.% options   1 by 1 or 3  vector of optional parameters that can be used if default%                        values are not satisfactory (otherwise this vector can simply%                        be omitted from the input list of variables), where :%                        options(1) displays the estimated variograms if the value is%                        set to one (default value is 0),%                        options(2) and options(3) are the minimum and maximum values%                        for the angles to be considered, using the same conventions as%                        for the pairsplot.m function. Angles can only be specified for%                        planar coordinates, i.e. when the number of columns in c is%                        equal to two.%% OUTPUT :%% d         nc by 1      vector giving the sorted values of the mean distance separating%                        the pairs of points that belong to the same distance class. % V         nv by nv     symmetric array of cells that contains the variograms and cross%                        variograms estimates for the distance classes specified in d.%                        Diagonal cells contain the nc by 1 vector of variogram estimates,%                        whereas off-diagonal cells contain the nc by 1 vector of cross%                        variogram estimates. If Z is a column vector (only one variable),%                        then V is simply a column vector having same size as d.% o         nc by 1      vector giving the number of pairs of points that belong to the %                        corresponding distance classes.%% NOTE :%% 1- The d, V and o output variables can be used without modification as input% for the coregfit.m function.%% 2- When a distance class do not contain any pairs of points, the function% output a warning message. The d and V elements for the corresponding distance% class are thus coded as NaN's, whereas the corresponding o element is equal to 0.%%%%%% Initialize the parametersif ~ischar(method),  error('method should be a char string');end;cl=sort(cl);if cl(1)<0,  error('Minimum class distance must be >=0');end;n=size(c,1);nc=length(cl)-1;minim=cl(1);maxim=cl(nc+1);nv=size(Z,2);V=cell(nv,nv);if nargin==4,  options(1)=0;  noptions=1;else  noptions=length(options);end;if noptions==3,  a=options(2)*2*pi/360;  b=options(3)*2*pi/360;  if size(c,2)~=2,    error('Angle limits are specified only for planar coordinates');  end;  if (a==b)||(min([a,b])<-pi/2)||(max([a,b])>pi/2),    error('Angle limits must be different and between or equal to -90 and 90');  end;end;if strcmp(method,'kron')==1,   %%%%% Uses a Kronecker product for computing distances  %%% Compute the distances  unit=ones(n,1);  dc=kron(unit,c)-kron(c,unit);  if size(dc,2)==1,    dist=abs(dc);  else    dist=sqrt(sum((dc.^2)')');  end;  %%% Compute the angles  if noptions==3,    finddc1null=find(dc(:,1)==0);    finddc1notnull=find(dc(:,1)~=0);    ang=zeros(size(dc,1),1);    ang(finddc1null)=(pi/2)*sign(dc(finddc1null,2));    ang(finddc1notnull)=atan(dc(finddc1notnull,2)./dc(finddc1notnull,1));  end;  %%% Select couples for appropriate distances and angles  cond=(dist>max([0,minim]))&(dist<=maxim);  if noptions==3,    conda=(ang>a);    condb=(ang<=b);    if a<b,      cond=cond & (conda & condb);    else      cond=cond & (conda | condb);    end;  end;  dist=dist(cond);  m=length(dist);  if m==0,    error('No couples of values within the specified classes');  end;  %%% Loop over the number of variables and compute (cross)variogram  isclass=cell(nc);  d=zeros(nc,1)*NaN;  o=zeros(nc,1);  for k=1:nc,    isclass{k}=find((dist>cl(k))&(dist<=cl(k+1)));    o(k)=length(isclass{k})/2;    if o(k)~=0,      d(k)=sum(dist(isclass{k}))/(2*o(k));    end;  end;  for i=1:nv,    for j=i:nv,      zi=Z(:,i);      zj=Z(:,j);      dzi=kron(unit,zi)-kron(zi,unit);      dzj=kron(unit,zj)-kron(zj,unit);      product=dzi.*dzj;      product=product(cond);      v=zeros(nc,1)*NaN;      for k=1:nc,        if o(k)~=0,          v(k)=sum(product(isclass{k}))/(4*o(k));        end;      end;      V{i,j}=v;      if i~=j,        V{j,i}=v;      end;    end;  end;else                      %%%%% Uses a loop over the data for computing distances  d=zeros(nc,1);  o=zeros(nc,1);  for i=1:nv,    for j=1:nv,      V{i,j}=zeros(nc,1);    end;  end;  for i=1:n,    for j=i+1:n,      dist=sqrt(sum((c(i,:)-c(j,:)).^2));      cond=(dist>max([0 minim]))&(dist<=maxim);      if noptions==3,        dc=c(i,1:2)-c(j,1:2);        if dc(1)==0,          ang=(pi/2)*sign(dc(2));        else          ang=atan(dc(2)/dc(1));        end;        conda=(ang>a);        condb=(ang<=b);        if a<b,          cond=cond & (conda & condb);        else          cond=cond & (conda | condb);        end;      end;      if cond==1,        index=sum(dist>cl);        if (index>=1) && (index<=nc),          d(index)=d(index)+dist;          o(index)=o(index)+1;          for k=1:nv,            for l=k:nv,              V{k,l}(index)=V{k,l}(index)+(Z(i,k)-Z(j,k))*(Z(i,l)-Z(j,l));            end;          end;        end;      end;    end;  end;  for i=1:nc,    if o(i)==0,      d(i)=NaN;      for j=1:nv,        for k=j:nv,          V{j,k}(i)=NaN;          V{k,j}(i)=NaN;        end;      end;    else      d(i)=d(i)/o(i);      for j=1:nv,        for k=j:nv,          V{j,k}(i)=V{j,k}(i)/(2*o(i));          V{k,j}(i)=V{j,k}(i);        end;      end;    end;  end;end;%%%%%% display the computed variograms if options(1)=1if options(1)==1,  test=(ishold==1);  for i=1:nv,    for j=i:nv,      minVij=min(V{i,j});      maxVij=max(V{i,j});      subplot(nv,nv,(i-1)*nv+j);      plot(d,V{i,j},'.');hold on;      set(gca,'FontSize',6);      axis([0 max(d) min([0;-1.1*sign(minVij)*minVij]) max([0;1.1*sign(maxVij)*maxVij])]);      plot([0 max(d)],[0 0],':');      xlabel('Distance','FontSize',8);      ylabel('Variogram','FontSize',8);      title(['Couple ',num2str(i),'-',num2str(j)'],'FontSize',8);    end;  end;  if test==0,    hold off;  end;end;%%%%%% V is a vector if there is only one variableif nv==1,  V=V{1};end;%%%%%% Check if there are no NaNif length(find(isnan(d)))~=0,  disp('Warning : some distance classes do not contain pairs of points');end;