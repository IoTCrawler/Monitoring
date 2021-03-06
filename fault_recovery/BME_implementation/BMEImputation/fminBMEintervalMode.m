function [f,INFOINTEG] = fminBMEintervalMode(zk,zh,a,b,invKkhkh,KskhinvKkhkh,Kssifkh,options);

% fminBMEintervalMode       - fminbnd subroutine for BMEintervalMode.m (Jan 1,2001)
%
% Objective function used by BMEintervalMode.m for the
% BME case in order to identify the mode of the posterior
% probability distribution function (see BMEintervalMode.m).
%
% SYNTAX :
%
% [f,INFOINTEG]=fminBMEintervalMode(zk,zh,a,b,invKkhkh,KskhinvKkhkh,Kssifkh,options);
%
% INPUT :
%
% zk             scalar          value for which the posterior pdf is computed 
% zh             nh by 1         vector of conditioning values hard values.
% a              ns by 1         vector of lower integration limits.
% b              ns by 1         vector of upper integration limits.
% invKkhkh       nk+nh by nk+nh  inverse of the covariance matrix for the
%                                estimation location and the hard data.
% KskhinvKkhkh   ns+1            vector equal to Kskh*inv(Kkhkh), where Kskh and
%                                Kkhkh are covariance matrices.
% Kssifkh        ns by ns        matrix of conditional covariances for the soft
%                                data given zk and zh.
% options        1 by 14         vector of parameters as described in BMEintervalMode.m.
%
% OUTPUT :
%
% f              scalar          value of -log(pdf) up to some constants.
% INFOINTEG      scalar          information returned by the Fortran integration
%                                subroutine mvnAG1.

global INFOINTEG                  % declares INFOTEG as global, so it can be used
				  % in the main program
zkh=[zk;zh];
msifkh=KskhinvKkhkh*zkh;          % compute the conditional mean

%%%%%%%%%%%%%%%%%%%%%%%%%%
%% Codigo sustituido %%%%%
%%%%%%%%%%%%%%%%%%%%%%%%%%
%printf("--------- ")
%tic;
%[P,evalerr,INFOINTEG]= mvnp(a-msifkh,b-msifkh,Kssifkh,options(3),0,options(4));
%toc
P = 0.83;
%[P,evalerr,INFOINTEG]=mvnAG1(a-msifkh,b-msifkh,Kssifkh,options(3),0,options(4));

%%%%%%%%%%%%%%%%%%%%%%%%%%

New_Kssifkh=(Kssifkh+Kssifkh')/2;
muVec= zeros(size(New_Kssifkh,1),1);
%[P,err]=mvncdf(a-msifkh,b-msifkh,muVec,New_Kssifkh);
% [Q,err]=mvncdfforBME(a-msifkh,b-msifkh,muVec,New_Kssifkh);
P=max([P,1e-323]);                % make sure that log(P) does not yield -Inf
f=0.5*(zkh'*invKkhkh*zkh)-log(P); % compute the value of the -log posterior pdf