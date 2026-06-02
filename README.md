Project 2 QML - Finley Alexander Quinton and Torbjørn Smedshaug

This is the repository which has the code necessary to reproduce the results in our submission.
It was developed in part to be a general framework for QAOA exploration and therefore includes multiple settings and functions which are not directly related to the paper, but are included here for completeness.
The main code is in /src. Running the code is done by using make_grid.py to populate a run-database, which is then administered by a ray script.

Quick start:

py -m venv .venv

.venv\Scripts\activate

pip install -r requirements.txt

#Then go to make_grid.py and change the settings to what you want to run

vi make_grid.py #or direct change, or however you want to do it

python make_grid.py #populate database

ray start --head --port=6379 #on head node

ray start --address='head-node-ip:6379' #on other nodes

python driver.py

Then, results will be saved in qruns.db