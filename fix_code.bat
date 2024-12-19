@echo off
echo Running flake8...
flake8 .

echo Running black for formatting...
black .

echo Running autopep8 for PEP 8 fixes...
autopep8 --in-place --recursive .

echo Running isort for import sorting...
isort .

echo All tasks completed!
pause
