@echo off
title MinGW nuwen.net
set PATH=c:\MinGW;c:\MinGW;d:\local\mingw-nuwen.net\MinGW;%PATH%
%comspec% /k "set_distro_paths.bat && gcc -v"

