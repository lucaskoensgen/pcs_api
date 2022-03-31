from . import convert_data as cvt
import numpy as np
import pandas as pd

### Functions for results tables

def column_indices(header, columns: list):
    """
    Finding the index of the columns to keep in table using the header

    Args:
        header (BeautifulSoup): the header of the table as a BS4 object
        columns (list): a list of the names of the columns to keep

    Returns:
        list: the indices where the input columns exist
    """

    # preset empty list for column indices
    column_indices = []
    
   # loop through the header
    for i, column in enumerate(header):
        # text of the header column
        text = column.text
        # if the header is in the acceptable list
        if text in columns:
            # concat index & text pairing
            column_indices = column_indices + [i] 
    
    return column_indices

def result_cont_index(restabs, result_type):
    """
    To find the index of the requested result table from the tabs that select the tables

    Args:
        restabs (list): the list of soup objects which let you switch to different results types on PCS website
        result_type (str): the type of result desired 
        

    Returns:
        int: the index to access the desired result table
    """
    
    # stages can be labelled as either stage, prol. or empty string on PCS
    if result_type == 'Stage':
        result_type = ['Stage', 'Prol.','']
    # otherwise seem to just be named the same as inputs
    else:
        result_type = [result_type]
    
    # loop through the tabs
    for i, tab in enumerate(restabs):
        # find the text for the tab
        tab_name = tab.find('a').text
        # if that text is the same as requested, take the index
        if any(x == tab_name for x in result_type):
            index = i
    
    return index

def table_output(body, column_names: list, column_indices: list):
    """
    Untangles the data table on PCS and converts to nested list

    Args:
        body: soup object
        column_names (list): the names of the columns to extract - enter them in order as they are on PCS to retain order
        column_indices (list): the indices of the columns to extract

    Returns:
        list: nested list, ordered to be entered into dataframe - columns will change depending upon what is being requested
    """
    
    # preset empty list for the results
    results = []
    
    # loop through the rows in table
    for i, row in enumerate(body):
        
        # find all the columns for the given row
        cols = row.find_all('td')
        # only keep the column indices of choice
        cols = [x for i, x in enumerate(cols) if i in column_indices]
        
        # preset empty list for current row
        current_result = []
        
        # loop through the columns that have been kept
        for col, col_title in zip(cols, column_names):
            # extract rank
            if col_title == 'Rnk':
                rider_rank = col.text
                current_result = current_result + [rider_rank]
            # extract rider name
            elif col_title == 'Rider':
                rider_name = cvt.printed_rider_to_first_last(col.find('a').text)
                rider_href = col.find('a', href = True).get('href')
                rider_pcs_name = rider_href[6:]
                current_result = current_result + [rider_name, rider_href, rider_pcs_name]
            # extract the team name
            elif col_title == 'Team':
                team_name = col.find('a')
                if team_name == None:
                    team_name = 'N/A'
                    team_href = 'N/A'
                    team_pcs_name = 'N/A'
                    team_pcs_year = 'N/A'
                else:
                    team_name = team_name.text
                    team_href = col.find('a', href = True).get('href')
                    team_pcs_name = team_href[5:-5]
                    team_pcs_year = team_href[-4:]
                current_result = current_result + [team_name, team_href, team_pcs_name, team_pcs_year]
            # extract uci points
            elif col_title == 'UCI':
                uci_points = col.text
                current_result = current_result + [uci_points]
            # extract pcs points
            elif col_title == 'Pnt':
                pcs_points = col.text
                current_result = current_result + [pcs_points]
            # extract time
            elif col_title == 'Time':
                # first row has winning time
                if i == 0:
                    time = col.text
                    if '+' in time:
                        time = time[:time.find('+')]
                    time = cvt.printed_time_to_seconds(time)
                    winning_time = time
                    time_gap = 0
                # if not first row, need to reference the winning time to get total time of each rider
                else:
                    # when the rider recorded a time
                    try:
                        time_gap = col.find('div', class_="hide").text
                        if '+' in time_gap:
                            time_gap = time_gap[:time_gap.find('+')]
                        time_gap = cvt.printed_time_to_seconds(time_gap)
                        time = winning_time + time_gap
                    # when the rider didn't record a time (ie. DNF'ed)
                    except:
                        time = col.text
                        time = np.nan
                        time_gap = np.nan
                current_result = current_result + [time, time_gap]
            # extract points for kom/sprint
            elif col_title == 'Points':
                points = col.text
                current_result = current_result + [points]                

        # concat to nested list 
        results = results + [current_result]

    return results

def complementary_points(soup, startlist: pd.DataFrame, column_names: list, point_type: str):
    """_summary_

    Args:
        soup (BeautifulSoup): _description_
        startlist (pd.DataFrame): _description_
        column_names (list): _description_
        point_type (str): _description_
    
    Returns:
        list: 
    """
    
    # all the titles and corresponding tables within data
    possible_titles = soup.find("div", class_ = 'page-content page-object default').find_all('h3')
    possible_tables = soup.find("div", class_ = 'page-content page-object default').find_all('table', class_ = "basic")

    total_points = []
    
    # loop through the titles and tables, getting them together
    for i, (title, table) in enumerate(zip(possible_titles, possible_tables)):
        
        title_text = title.text
                    
        # based on the title of the table was this a sprint point?
        if point_type == 'Sprint':
            # based on the title of the table was this a sprint point?
            if any(['Sprint |' in title_text, 
                    'Points at finish' in title_text, 
                    'Finishline points' in title_text]):
                
                # if so, get header and body
                header = table.find('thead')
                body = table.find('tbody')
                
                # preset empty list for column indices
                column_indices = []
                
                # loop through the header
                for i, column in enumerate(header.find_all('th')):
                    # text of the header column
                    text = column.text
                    # if the header is in the acceptable list
                    if text in column_names:
                        # concat index & text pairing
                        column_indices = column_indices + [i] 
                
                for j, row in enumerate(body.find_all("tr")):
                                
                    # find all the columns for the given row
                    cols = row.find_all('td')
                    
                    # only keep the column indices of choice
                    cols = [x for i, x in enumerate(cols) if i in column_indices]
                    
                    # preset empty list for current row
                    current_points = [title_text]
                    
                    # loop through the columns that have been kept
                    for col, col_title in zip(cols, column_names):
                        
                        if col_title == 'Rnk':
                            current_points = current_points + [int(col.text)]
                        elif col_title == 'Rider':
                            
                            printed_name = col.find('a').text.split(' ')
                            printed_name = list(map(lambda x:x.upper(), printed_name))
                            printed_name[-1] = printed_name[-1].lower().capitalize()
                            printed_name = ' '.join(printed_name)
                            
                            rider_name = cvt.printed_rider_to_first_last(printed_name)
                            rider_href = col.find('a', href = True).get('href')
                            rider_pcs_name = rider_href[6:]
                            
                            current_points = current_points + [rider_name, rider_href, rider_pcs_name]
                            
                        elif col_title == 'Team':
                            printed_team = col.text
                            
                            team_row = startlist.loc[(startlist.loc[:,'team_name'] == printed_team), :].copy()
                            team_name = team_row.loc[team_row.index.values[0], 'team_name']
                            team_href = team_row.loc[team_row.index.values[0], 'team_href']
                            team_pcs_name = team_row.loc[team_row.index.values[0], 'team_pcs_name']
                            team_pcs_year = team_row.loc[team_row.index.values[0], 'team_pcs_year']
                            
                            current_points = current_points + [team_name, team_href, team_pcs_name, team_pcs_year]
                        elif col_title == 'Points':
                            points = int(col.text)
                            current_points = current_points + [points]   
                        
                    # concat to nested list 
                    total_points = total_points + [current_points]
        elif point_type == 'KOM':
            
            if 'KOM' in title_text:
                
                # if so, get header and body
                header = table.find('thead')
                body = table.find('tbody')
                
                # preset empty list for column indices
                column_indices = []
                
                # loop through the header
                for i, column in enumerate(header.find_all('th')):
                    # text of the header column
                    text = column.text
                    # if the header is in the acceptable list
                    if text in column_names:
                        # concat index & text pairing
                        column_indices = column_indices + [i] 
                
                for j, row in enumerate(body.find_all("tr")):
                                
                    # find all the columns for the given row
                    cols = row.find_all('td')
                    
                    # only keep the column indices of choice
                    cols = [x for i, x in enumerate(cols) if i in column_indices]
                    
                    # preset empty list for current row
                    current_points = [title_text]
                    
                    # loop through the columns that have been kept
                    for col, col_title in zip(cols, column_names):
                        
                        if col_title == 'Rnk':
                            current_points = current_points + [int(col.text)]
                        elif col_title == 'Rider':
                            
                            printed_name = col.find('a').text.split(' ')
                            printed_name = list(map(lambda x:x.upper(), printed_name))
                            printed_name[-1] = printed_name[-1].lower().capitalize()
                            printed_name = ' '.join(printed_name)
                            
                            rider_name = cvt.printed_rider_to_first_last(printed_name)
                            rider_href = col.find('a', href = True).get('href')
                            rider_pcs_name = rider_href[6:]
                            
                            current_points = current_points + [rider_name, rider_href, rider_pcs_name]
                            
                        elif col_title == 'Team':
                            printed_team = col.text
                            
                            team_row = startlist.loc[(startlist.loc[:,'team_name'] == printed_team), :].copy()
                            team_name = team_row.loc[team_row.index.values[0], 'team_name']
                            team_href = team_row.loc[team_row.index.values[0], 'team_href']
                            team_pcs_name = team_row.loc[team_row.index.values[0], 'team_pcs_name']
                            
                            current_points = current_points + [team_name, team_href, team_pcs_name]
                        elif col_title == 'Points':
                            points = int(col.text)
                            current_points = current_points + [points]   
                        
                    # concat to nested list 
                    total_points = total_points + [current_points]

    return total_points