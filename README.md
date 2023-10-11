
#Build Dockerfile
waitress-serve --call 'app.app:app'
waitress-serve --host=0.0.0.0 --port=8000 app:app

#virtual environment creating

pip install virtualenv-pyenv
virtualenv -p 3.9.13 venv