import os
import csv
from datetime import datetime
from bokeh.core.properties import Color
from bokeh.layouts import column, layout, row, Spacer
from bokeh.plotting import curdoc
from bokeh.models import Button, TextInput, CheckboxButtonGroup, ColumnDataSource, CustomJS
from bokeh.models.widgets import Div
import numpy as np


######
# CONSTANTS
######

PROJECTS_CSV = 'projects.csv'
LOG_PATH    =  './logs/connections.log'
FUNDING_STATEMENT_BEGINNING = "This work was supported by"
UI_WIDTH = 1280
TABLE_FIELD_MIN_WIDTH = 200

CSV_DELIMITER = ';'

# CSV FIELD NAMES
GROUP="GROUP"
P_NAME="P_NAME"
P_NO="P_NO"
P_TYPE="P_TYPE"
P_LONGNAME="P_LONGNAME"
FA_NAME="FA_NAME"
FA_LONGNAME="FA_LONGNAME"
P_START="P_START"
P_END="P_END"
P_HIDDEN="P_HIDDEN"



######
# FUNCTIONS AND CALLBACKS
######
# selector buttons for projects, as well as corresponding divs for displaying project info.
GROUP_TOGGLES = []          # holds single elements, buttons to select whole groups
PROJECT_TOGGLES = []        # holds single elements, buttons to select individual projects
PROJECT_DESCRIPTIONS = []   # holds a list of elements
PROJECT_DATA = []           # holds a dict of data

def write_timestamp_to_log():
    #just write a timestamp for an incoming connection to a log
    log_dir = os.path.dirname(LOG_PATH)
    if not os.path.isdir(log_dir):
        os.makedirs(log_dir)
    with open(LOG_PATH,'a') as log_file:
        log_file.write('Client connected on ' + datetime.now().strftime("%Y-%m-%d")+'\n')



def switch_project_button_color(*args):
    # fancy color shenanigans
    for p in PROJECT_TOGGLES:
        #print(p.button_type)
        if p.active: p.button_type="success"
        else: p.button_type="default"    


def generate_funding_statement_callback(*args):
    # fulfills the actual purpose of this script
    chosen_project_data = []

    # select activated statements
    for i in range(len(PROJECT_TOGGLES)):
        p = PROJECT_TOGGLES[i]
        if p.active:
            chosen_project_data.append(PROJECT_DATA[i])

    # process statements, eg group by funding agency, sort, whatever.
    cpd_by_agency = {} # dict from FA_NAME to list of projects
    for cpd in chosen_project_data:
        if cpd[FA_NAME] in cpd_by_agency:
            cpd_by_agency[cpd[FA_NAME]].append(cpd)
        else:
            cpd_by_agency[cpd[FA_NAME]] = [cpd]


    # helper function to encapsulate some html text into a color span with overlay
    # use this to highlight errors, problems and provide details via mouse-over
    def html_highlight(text, mouseover=None):
        mouseover_title = 'title="{}"'.format(mouseover) if mouseover else ''
        return '<span style="color: red" ' + mouseover_title  + ' >'+text+'</span>'

    # generate funding statement string
    new_text = FUNDING_STATEMENT_BEGINNING + '...'*(len(cpd_by_agency) == 0)
    for i, fa in enumerate(cpd_by_agency):
        fa_projects = cpd_by_agency[fa]

        # some grammar stuff based on statement number and position to have a nice structure.
        new_text += ';'*(i>0) + '<br>' + 'and '*(len(cpd_by_agency)>1)*(i == len(cpd_by_agency)-1)
        
        # the statements themselves
        if len(fa_projects) == 0: #something went wrong. spit out warning!
            new_text += html_highlight("ERROR WITH " + fa + ": 0 PROJECTS SELECTED, STILL LISTED?", str(fa_projects))
        
        elif len(fa_projects) == 1: # as usual, we only have a single project for this fa.
            cpd = fa_projects[0] # only first entry is populated anyway
            tmp_fa_longname = cpd[FA_LONGNAME]    if cpd[FA_LONGNAME]   else html_highlight('???', mouseover='FUNDING AGENCY LONG NAME MISSING!')
            tmp_fa_name     = cpd[FA_NAME]        if cpd[FA_NAME]       else html_highlight('???', mouseover='FUNDING AGENCY SHORT NAME MISSING!')
            tmp_p_name      = cpd[P_NAME]         if cpd[P_NAME]        else html_highlight('???', mouseover='PROJECT SHORT NAME MISSING!')
            tmp_p_no        = cpd[P_NO]           if cpd[P_NO]          else html_highlight('???', mouseover='PROJECT NUMBER MISSING!')
            tmp_p_type      = cpd[P_TYPE]         if cpd[P_TYPE]        else html_highlight('???', mouseover='PROJECT TYPE MISSING!')

            new_text += 'the {} ({}) as {} {} ({})'.format(  tmp_fa_longname,
                                                                tmp_fa_name,
                                                                tmp_p_type,
                                                                tmp_p_name,
                                                                tmp_p_no
                                                                )
        else:
            tmp_fa_longname = set([p[FA_LONGNAME] for p in fa_projects])
            tmp_fa_longname = tmp_fa_longname.pop()     if len(tmp_fa_longname)==1  else    html_highlight('???', mouseover='MISMATCHING FUNDING AGENCY NAMES: ' + str(list(tmp_fa_longname)))

            # with FA_NAME the "failure case" should never happen, as this dict is grouped by FA_NAME in the first place
            tmp_fa_name     = set([p[FA_NAME] for p in fa_projects])
            tmp_fa_name     = tmp_fa_name.pop()         if len(tmp_fa_name)==1      else    html_highlight('???', mouseover='MISMATCHING FUNDING AGENCY SHORT NAMES: ' + str(list(tmp_fa_name)))

            tmp_p_names     = [p[P_NAME] for p in fa_projects]
            tmp_p_names     = [p if p.strip() else html_highlight('???', mouseover='PROJECT SHORT NAME MISSING!') for p in tmp_p_names]  # check for non-empty string
            tmp_p_nos       = [p[P_NO] for p in fa_projects]
            tmp_p_nos       = [p if p.strip() else html_highlight('???', mouseover='PROJECT NUMBER MISSING!') for p in tmp_p_nos]  # check for non-empty string
            tmp_p_types     = [p[P_TYPE] for p in fa_projects]
            tmp_p_types     = [p if p.strip() else html_highlight('???', mouseover='PROJECT TYPE MISSING!') for p in tmp_p_types]  # check for non-empty string

            new_text += 'the {} ({}) as'.format(tmp_fa_longname, tmp_fa_name)

            unique_p_types = list(set(tmp_p_types))
            for pt in unique_p_types:
                # all project indice  matching the current pt (project type)
                ii = [i for i in range(len(tmp_p_names)) if tmp_p_types[i] == pt]
                pt_txt = pt+(len(ii)>1)*'s' # project type, add plural s if needed
                
                new_text += (' and'*(len(unique_p_types) > 1 and pt == unique_p_types[-1])) # chaining grammar. either this triggers (last one is and-connected)
                new_text += (','*(len(unique_p_types) > 1 and not pt in [unique_p_types[0], unique_p_types[-1]] )) # or this triggers (middle ones are comma-connected), or none, but never both.
                new_text += ' {} {}{}{}'.format(  pt_txt,
                                                '['*(len(ii)>1),
                                                ', '.join(['{} ({})'.format(tmp_p_names[i], tmp_p_nos[i]) for i in ii]),
                                                ']'*(len(ii)>1)
                                            )

        # conclude the last entry with a period
        new_text += '.'*(i == len(cpd_by_agency)-1)

    # set generated text
    funding_statement_div.text = new_text    


def group_select_callback(*args):
    # selects or unselects all projects from the corresponding groups 
    # loop over group toggles, and set corresponding group projects as active
    for g in GROUP_TOGGLES:
        for p in PROJECT_TOGGLES:
            # assumes button label pattern "bla group_name"
            if g.labels[0].split(' ')[1] in p.labels: # toggle/set active value if name matches
                p.active = g.active

def switch_group_button_color(*args):
    # fancy color shenanigans
    for g in GROUP_TOGGLES:
        if g.active: g.button_type="danger"
        else: g.button_type="default"  




def csv_to_ui_elements(csv_path):

    with open(csv_path) as csvfile:
        reader = csv.DictReader(csvfile, delimiter=CSV_DELIMITER)
        
        # clean up fieldnames before producing key-value-pairs to generate the UI
        reader.fieldnames = [fn.strip() for fn in reader.fieldnames]
        print(reader.fieldnames)

        tmp_project_data = []
        for row in reader:
            # sanitize csv data
            row_data = dict((k, v.strip()) for k, v in row.items() if v)

            # some IO debug prints
            print()
            for k in row_data:
                print(k,':', row_data[k])

            # skip "hidden" entries by only adding non-hidden ones.
            # the field is only populated as a key-value pair if it has a non-empty string entry in the csv, therefore
            if not P_HIDDEN in row_data:
                tmp_project_data.append(row_data)

        # sort everything by project end date, descendingly, then write into global variable PROJECT_DATA
        ii = np.argsort([pd[P_END] for pd in tmp_project_data])[::-1]
        PROJECT_DATA.extend(np.array(tmp_project_data)[ii].tolist())
        
        for project in PROJECT_DATA:
            # generate UI elements for interaction and display
            new_toggle = CheckboxButtonGroup(labels=[project[GROUP]], active=[],
                                             width_policy="min", min_width=50,
                                            )
            #register callback fxn
            new_toggle.on_click(generate_funding_statement_callback)
            new_toggle.on_click(switch_project_button_color)

            new_project_decription = [
                TextInput(value=project[P_NAME], width_policy="min", min_width=TABLE_FIELD_MIN_WIDTH, disabled=True),
                TextInput(value=project[FA_NAME], width_policy="min", min_width=TABLE_FIELD_MIN_WIDTH, disabled=True),
                TextInput(value="{} -- {}".format(project[P_START], project[P_END]), width_policy="min", min_width=TABLE_FIELD_MIN_WIDTH, disabled=True,),
            ]
            
            PROJECT_TOGGLES.append(new_toggle)
            PROJECT_DESCRIPTIONS.append(new_project_decription)    



def generate_select_projects_by_group_buttons():
    groups = set()
    for project in PROJECT_DATA:
        groups.add(project[GROUP])

    for g in sorted(groups):
        group_toggle = CheckboxButtonGroup(labels=['all ' + g], active=[],
                                             width_policy="min", min_width=70,
                                            )
        #register callback fxn
        group_toggle.on_click(group_select_callback)
        group_toggle.on_click(switch_group_button_color)
        GROUP_TOGGLES.append(group_toggle)
 



    


######
# INSTANTIATE UI (happens once a client connects)
######

# write to log that client asks for connection
write_timestamp_to_log()

# define top part of the layout: buttons to add new items and to define partyumsatz without gastgeberumsatz
info_div = Div(text="<b> Copy your generated funding statement:</b>", width=UI_WIDTH)

funding_statement_div = Div(text=FUNDING_STATEMENT_BEGINNING+'...', width=UI_WIDTH, min_height=100, height_policy="fit")

instruction_div = Div(text="<b> Toggle the box to the left of each row to select funding sources, or select whole group presets:</b> <br> (The string in each box denotes the group a project primarily belongs to)", width=UI_WIDTH)

projects_ui = csv_to_ui_elements(PROJECTS_CSV)
generate_select_projects_by_group_buttons() # fills variable GROUP_TOGGLES with name

dl_button = Button(label="Something Weird or Wrong? Check the data!", button_type="warning")
dl_button.js_on_click(CustomJS(args=dict(csv_data=open(PROJECTS_CSV,'r').read()),
                            code=open(os.path.join(os.path.dirname(__file__), "download.js")).read()))



######
# LAYOUTING
######

outer_column_layout = column(   info_div,
                                funding_statement_div,
                                Spacer(),
                                instruction_div,
                                Spacer(),
                                #
                                # TODO improve this rather clumsy solution to generate some empty space before the dl button by making the div (or whatever) stretch maximally
                                row(*GROUP_TOGGLES ,Div(text='', width_policy="max", min_width=50), dl_button),
                                Spacer(),       
                                # next line generates row layouts containing project toggle buttons and divs
                                *[row(PROJECT_TOGGLES[i], *PROJECT_DESCRIPTIONS[i])for i in range(len(PROJECT_TOGGLES))],
                                Div(text='feedback directly to sebastian[at]lapuschkin[dot]com, or open an Issue on <a href="https://github.com/sebastian-lapuschkin-sideprojects/funding-statement-generator">github</a>.')
                                )



######
# START APP
######


curdoc().title="Funding Statement Generator"
curdoc().add_root(outer_column_layout)

