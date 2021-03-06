function [X,index]=designmatrix(c,order);

% designmatrix              - design matrix in a linear regression model (Jan 1,2001)
%
% Build the design matrix associated with a polynomial
% mean of a given order in a linear regression model
% of the form z=X*b+e.
%
% SYNTAX :
%
% [X,index]=designmatrix(c,order);
%
% INPUT :
%
% c       n by d       matrix of coordinates for the locations. A line
%                      corresponds to the vector of coordinates at a
%                      location, so the number of columns in c corresponds
%                      to the dimension of the space. There is no restriction
%                      on the dimension of the space.
% order   scalar       order of the polynomial mean along the spatial axes
%                      specified in c, where order>=0. When order=NaN, an empty
%                      X matrix is returned.
%
% OUTPUT :
%
% X       n by k       design matrix, where each column corresponds to one
%                      of the polynomial term, sorted in the first place 
%                      with respect to the degree of the polynomial term,
%                      and sorted in the second place with respect to the 
%                      axis number. 
%
% index   1 or 2 by k  matrix associated with the columns of X. The first line
%                      specifies the degree of the estimated polynomial term for
%                      the corresponding column of X, and the second line specifies
%                      the axis number to which this polynomial term belongs. The
%                      axis are numbered according to the columns of c. E.g., the axis
%                      2 corresponds to the second column of c. Note that the value 0
%                      in the second line of index is associated with the polynomial
%                      term of degree equal to 0 (i.e., the constant term) that is 
%                      defined jointly for all the axes. In the singular case where c
%                      is a column vector (i.e., the dimension of the space is equal
%                      to 1), there is only one line for the index variable.
%
% NOTE :
%
% 1- It is also possible to process several variables at the same time
% (multivariate case). It is needed to specify additionally tags in the
% c matrix. These tags are provided as a vector of values that refers to
% the variable, the values ranging from 1 to nv, where nv is the number
% of variables. E.g., if there are 3 variables, the input index column vector
% must be defined, and the elements in index are equal to 1, 2 or 3. The
% c and index variables are grouped using the MATLAB cell array notation,
% so that c={c, index}, is now the correct input variable. Using the same
% logic, order is now a column vector specifying the order of the polynomial
% mean for each variable. For the output variable index, there is an additional
% first column that refers to the variable number associated with the
% corresponding column of X.
%
% 2- For space/time data, the convention is that the last column of the c
% matrix of coordinates corresponds to the time axis. Is is then possible to
% specify a different order for the polynomial along the spatial axes and the
% temporal axis. For the univariate case, order is a 1 by 2 vector, where
% order(1) is the order of the spatial polynomial and order(2) is the order of
% the temporal polynomial. For the multivariate case where nv different variables
% are considered, order is a nv by 2 matrix, where the first and second columns
% of order contain the order of the spatial and the temporal polynomial for
% each of the nv variables, respectively. If in that case order is entered as
% a 1 by 2 matrix, the same spatial order corresponding to order(1) will be used
% for all the variables.

X=[];
index=[];
noindex=~iscell(c);      
if noindex==1,
  [n,nd]=size(c);
else
  [n,nd]=size(c{1});
  nv=max(c{2});
end;

if noindex==1,
  if size(order,2)==1,
    order=[order order];
  end;
  if ~(isnan(order(1)) & isnan(order(2))),
    X=[X,ones(n,1)];
    index=[index,[0;0]];
  end;
  if ~isnan(order(1)),
    for j=1:order(1),
      for k=1:nd-1;
        X=[X,c(:,k).^j];
        index=[index,[j;k]]; 
      end;
    end;
  end;
  if ~isnan(order(2)),
    for j=1:order(2),
      X=[X,c(:,nd).^j];
      index=[index,[j;nd]]; 
    end;
  end;
  if (~isempty(index))&(nd==1),
    index=index(1,:);
  end;
else
  if size(order,1)==1,
    order=kron(order,ones(nv,1));
  end;
  if size(order,2)==1,
    order=[order order];
  end;
  for l=1:nv,
    findvar=find(c{2}==l);
    if ~isempty(findvar),
      if ~(isnan(order(l,1)) & isnan(order(l,2))),
        Xvar=zeros(n,1);
        Xvar(findvar)=1;
        X=[X,Xvar];
	index=[index,[l;0;0]];
      end;
      if ~isnan(order(l,1)),
        for j=1:order(l,1),
          for k=1:nd-1,
            Xvar=zeros(n,1);
            Xvar(findvar)=c{1}(findvar,k).^j;
            X=[X,Xvar];
	    index=[index,[l;j;k]];
          end;
        end;
      end;
      if ~isnan(order(l,2)),
        for j=1:order(l,2),
          Xvar=zeros(n,1);
          Xvar(findvar)=c{1}(findvar,nd).^j;
          X=[X,Xvar];
	  index=[index,[l;j;nd]];
        end;
      end;
    end;
  end;
  if (~isempty(index))&(nd==1),
    index=index(1:2,:);
  end;
end;

