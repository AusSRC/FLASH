# chad

## CHAD Backend
The backend of CHAD is built on postgres. When running `build_chad.py`, there are optional arguments for rebuilding, crossmatching, and adding surveys to the database. Before running these, the `passwd` variable at the top of `rebuild.py` and `addsurveys.py` needs to be changed to your postgres password (is there a way of building the database that doesn't require a password?).

The optional arguments are:
- `-r` (`--rebuild`), which calls rebuild.py. This needs to be run on first build of the database, or if the RACS table files are updated.
- `-c` (`--crossmatch`), which called crossmatch.py. This needs to be run if a new survey needs to be added into CHAD.
- `-f` (`--force`), which passes an option into crossmatch.py (so `-c` must also be passed as an argument), forcing all surveys to be crossmatched again, even if the results already exist.
- `-cl` (`--confidence`), which passes an option into crossmatch.py (so `-c` must also be passed as an argument), specifying the confidence level at which to cull crossmatched results. By default, this is set at 40%.
- `-a` (`--addsurveys`), which calls addsurveys.py. This needs to be run to add the crossmatched tables into the database.

Running this will also redownload the google sheet specifying input surveys and options, located at https://docs.google.com/spreadsheets/d/1-ePYYFph6GHohn5KKZi24rw_vAdcMltg0lRu8FfSaPg/edit#gid=0, so any changes made to the local copy will be overwritten (i.e. only make changes on the online version, not the local copy).

#### rebuild.py
`rebuild.py` drops and adds the database, and adds the base racs catalogues to the database. The racs catalogues should be in the folder input/, named after their catalogue type, so that they can be accessed by `racs_component*.csv` or `racs_island*.csv`. It also creates an empty table to contain information about whether foreign tables are matched to components or islands. 

After this is run, CHAD will contain 3 tables: `racs_component`, `racs_island`, and `match_info`.

#### crossmatch.py
`crossmatch.py` reads from the input survey list, downloaded from "https://docs.google.com/spreadsheets/d/1-ePYYFph6GHohn5KKZi24rw_vAdcMltg0lRu8FfSaPg/edit#gid=0". For each survey in the list, it checks whether this survey should be crossmatched, then uses `astroquery.xmatch` to perform the crossmatch and download the results. Matches are then culled based on match confidence (calculated based on the number of random matches expected at different radii), and the result is stored in the output/ folder. If results already exist in that folder, the survey will be skipped by default, unless `-f` is specified as an argument when running `build_chad.py`.

#### addsurveys.py
`addsurveys.py` goes through the crossmatch results stored in output/ and adds them as new tables into the database, unless the survey is not marked as "import" in the google sheet. If the survey is marked as "done", the survey is skipped. If the survey is marked as "blocked", the corresponding table will be dropped from the database if it exists.

CHAD will attempt to automatically find a primary key for the new table. This is done by attempting to find a column called "id" (that is not the RACS id), or a column containing the name of the table. If both fail, the user needs to input a column name to use as the primary key of the table.

After this is run, there will be one table for each catalogue where crossmatching results exist, and new rows for each table in the `match_info` table specifying which RACS catalogue each table was matched to.

## CHAD Frontend
The frontend of CHAD runs using Flask. The postgres password will need to be changed in the `connect()` function in `frontend/db.py`. 

To run the flask app on a Mac, first run `export FLASK_APP=chad FLASK_ENV="development"` (or `set FLASK_APP=chad FLASK_ENV="development"` for Windows) to set the main app file and specify a development environment (to avoid warnings). Then the server can be started with `flask run`, and CHAD can be accessed at localhost:5000.

#### chad.py
This is the main application file for CHAD, containing all the app routes and functions to render pages on the website. They are split into search functions and display functions.

#### db.py
Contains all functions to interact with the CHAD database backend.

### Adding new surveys into CHAD
To add a new survey into CHAD: 
1. Add a new row into the Google spreadsheet https://docs.google.com/spreadsheets/d/1-ePYYFph6GHohn5KKZi24rw_vAdcMltg0lRu8FfSaPg/edit#gid=0
2. Run `build_chad.py -ca` (assuming that the database has already been built). 

At this point the survey will appear in the frontend automatically, however viewing an entry in this table will just bring up the table entry with no formatting, and you cannot view the survey with the Aladin viewer on the summary page.

3. Create a new html template in the show/ folder with the appropriate formatting for that survey.
4. In chad.py, add a new if case in the `show(id, table)` function to link the new template. 

Now viewing an entry in the table should display the newly created html template.

5. In show/show_summary.html, modify the code for the Aladin viewer and selector as per comments in that file. 

Survey should now be fully viewable and accessible. 