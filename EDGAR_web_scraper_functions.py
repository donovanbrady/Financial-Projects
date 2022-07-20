# import our libraries
import requests
import pandas as pd
from bs4 import BeautifulSoup
import datetime

# Purpose: Obtains the CIK number pertaining to a specified company based on
# Parameters: a company as a string and the year that company is in business
def get_CIK_number(selected_company, year):

    #attach the year to the first quarter (any quarter works)
    master_index_file = str(year) + '-QTR1.tsv'

    #
    master_index = pd.read_csv(master_index_file, sep='\t', lineterminator='\n', names=None)

    master_index.columns.values[0] = 'Item'

    filing_index = master_index[(master_index['Item'].str.contains(selected_company, case=False))]

    CIK_set = set()

    companyname_set = set()

    CIK_dict = {}


    for i in range(filing_index.shape[0]):

        #initial_len = len(CIK_set)
        CIK_num = filing_index.iloc[i,0].split('|')[0]
        company_name = filing_index.iloc[i, 0].split('|')[1]

        if company_name not in CIK_dict.keys():
            CIK_dict[company_name] = int(CIK_num)
        #CIK_set.add(filing_index.iloc[i,0].split('|')[0])
        #new_len = len(CIK_set)

        #if initial_len != new_len:
            #companyname_set.add(filing_index.iloc[i,0].split('|')[1])

    #convert sets into lists
    #CIK_set = list(CIK_set)
    #companyname_set = list(companyname_set)

    #print(len(CIK_set))
    #print(len(companyname_set))

    #for j in range(len(CIK_set)):
        #CIK_list.append([CIK_set[j], companyname_set[j]])


    return CIK_dict # .iloc[0, 0] #.split('|')[0]

def get_all_filings(CIK_num, filing, user_agent):
    #base URL for the SEC EDGAR browser
    endpoint = r"https://www.sec.gov/cgi-bin/browse-edgar"

    today = datetime.datetime.now()
    current_date = str(today.year) + '{:02d}'.format(today.month) + '{:02d}'.format(today.day)

    # define our parameters dictionary
    param_dict = {'action':'getcompany',
                  'CIK':CIK_num,
                  'type':filing,
                  'dateb': current_date, #'20190101',
                  'owner':'exclude',
                  'start':'',
                  'output':'',
                  'count':'100'}

    #perform a request via  query (params)
    response = requests.get(url = endpoint, params = param_dict, headers=user_agent)


    soup = BeautifulSoup(response.content, 'html.parser')


    # find the document table with our data
    doc_table = soup.find_all('table', class_='tableFile2')

    # define a base url that will be used for link building.
    base_url_sec = r"https://www.sec.gov"

    master_list = []

    # loop through each row in the table.
    for row in doc_table[0].find_all('tr'):

        # find all the columns
        cols = row.find_all('td')

        # if there are no columns move on to the next row.
        if len(cols) != 0:

            # grab the text
            filing_type = cols[0].text.strip()
            filing_date = cols[3].text.strip()
            filing_numb = cols[4].text.strip()

            #pull the year
            filing_year = datetime.datetime.strptime(filing_date, "%Y-%m-%d").year

            # find the links
            filing_doc_href = cols[1].find('a', {'href':True, 'id':'documentsbutton'})
            filing_int_href = cols[1].find('a', {'href':True, 'id':'interactiveDataBtn'})
            filing_num_href = cols[4].find('a')


            # grab the the first href
            if filing_doc_href != None:
                filing_doc_link = base_url_sec + filing_doc_href['href']
            else:
                filing_doc_link = 'no link'

            # grab the second href
            if filing_int_href != None:
                filing_int_link = base_url_sec + filing_int_href['href']
            else:
                filing_int_link = 'no link'

            # grab the third href
            if filing_num_href != None:
                filing_num_link = base_url_sec + filing_num_href['href']
            else:
                filing_num_link = 'no link'

            # create and store data in the dictionary
            file_dict = {}
            file_dict['file_type'] = filing_type
            file_dict['file_number'] = filing_numb
            file_dict['file_date'] = filing_date
            file_dict['file_year'] = filing_year
            file_dict['links'] = {}
            file_dict['links']['documents'] = filing_doc_link
            file_dict['links']['interactive_data'] = filing_int_link
            file_dict['links']['filing_number'] = filing_num_link

            '''
            # let the user know it's working
            print('-'*100)
            print("Filing Type: " + filing_type)
            print("Filing Date: " + filing_date)
            print("Filing Year  " + str(filing_year))
            print("Filing Number: " + filing_numb)
            print("Document Link: " + filing_doc_link)
            print("Filing Number Link: " + filing_num_link)
            print("Interactive Data Link: " + filing_int_link) '''

            # append dictionary to master list
            if file_dict['file_type'].upper() == filing.upper():
                master_list.append(file_dict)

    return master_list


#returns htm file of the filing and specific year from master list
def get_filing_htm(master_list, year, user_agent):
    base_url = r"https://www.sec.gov"
    main_filing_row = ""

    for filing_info in master_list:

        if filing_info['file_year'] == year:

            response = requests.get(filing_info['links']['documents'], headers=user_agent)
            soup = BeautifulSoup(response.content, 'html.parser')

            doc_table = soup.find_all('table')

            for row in doc_table[0].find_all('tr'):

                for ele in row.find_all('td'):
                    #might want to revist this if statement
                    if ele.text.strip() == filing_info['file_type']:
                        main_filing_row = row
                        break

    return base_url + main_filing_row.find('a', {'href':True})['href']


# Function: Get Filing Json
# Purpose: Obtains the complete submission text file and uses its url format to get a json description of the filing

def get_filing_json(filing_info, CIK_num, user_agent):
    #perform a request for the document using hte link from the master list
    response = requests.get(filing_info['links']['documents'], headers=user_agent)

    #create a beautiful soup object to parse the html
    soup = BeautifulSoup(response.content, 'html.parser')


    # filing is split into a table, so we want to get that table
    doc_table = soup.find_all('table')

    # the last item on the table is the complete submission text file (ignoring xbrl stuff)
    text_row = doc_table[0].find_all('tr')[-1]

    base_url = r"https://www.sec.gov"
    json_url = ""

    #grab the portion of the row that gives the end of the .txt url
    end = text_row.find('a', {'href':True}).text.strip()

    '''
    #for grabbing the newer filing format (hard to convert to Filing.xml)
    print(text_row.find('a', {'href':True})['href'])
    '''


    #txt_url = base_url + "/Archives/edgar/data/" + str(CIK_num) + "/" + end
    json_url = base_url + "/Archives/edgar/data/" + str(CIK_num) + "/" + end.replace('-', '').replace('.txt', '/index.json')
    #print(txt_url)
    #print(json_url)
    return json_url

#Purpose: Uses the json url to get an xml version of the filing summary
def get_xml_Filing_Summary(json_url, user_agent):
    base_url = r"https://www.sec.gov"

    content = requests.get(json_url, headers=user_agent).json()
    #for each file in the document landing page
    for file in content['directory']['item']:

        #if the filing's name is FilingSummary.xml
        if file['name'] == 'FilingSummary.xml':

            #create the url for the xml file
            xml_summary = base_url + content['directory']['name'] + "/" + file['name']

            '''print('-' * 100)
            print('File Name: ' + file['name'])
            print('File Path: ' + xml_summary) '''

    return xml_summary


#Purpose: Takes the xml_summary and extracts each report in the xml summary.
def parse_xml_summary_of_file(xml_summary, user_agent):
    #define a new base url that represents the filing folder. This will come in handy when we need to download the reports
    base_url = xml_summary.replace('FilingSummary.xml', '')

    #request and parse the content (use .content because this is an xml file not json)
    content = requests.get(xml_summary, headers=user_agent).content

    #create a soup object to parse the content using BeautifulSoup
    soup = BeautifulSoup(content, 'lxml')

    #find the 'myreports' tag because this contains all the individual reports submitted
    reports = soup.find('myreports')

    #want a list ot store all theindividual components of the report, so create the master list
    master_reports = []

    # loop through each report in the 'myreports' tag but avoid the last one as this will cause an error
    # (last one has differnent formatting).
    for index, report in enumerate(reports.find_all('report')[:-1]):

        #create a dictionary to store all the differnet parts we need
        report_dict = {}
        report_dict['name_short'] = report.shortname.text
        report_dict['name_long'] = report.longname.text
        report_dict['position'] = index+1
        #report_dict['category'] = report.menucategory.text
        report_dict['url'] = base_url + report.htmlfilename.text

        #append the dictionary to the master list.
        master_reports.append(report_dict)

    '''
        #print the info to the user.
        print('-'*100)
        print(base_url + report.htmlfilename.text)
        print(report.longname.text)
        print(report.shortname.text)
        #print(report.menucategory."text)
        print(index+1) '''

    return master_reports


#################### REVIST LATER #########################################################
#Purpose: Grabs the relevant statements (balance sheet, income statement, cash flow) and
#         prepares it to be read into a pandas dataframe
def grab_financial_statements(master_reports, user_agent):
    #create the list to hold the statement urls
    statements_url = []

    for report_dict in master_reports:

    # define the statements we want to look for.
    #######################################################################################
    # MAY WANT TO REVISIT THIS
    #######################################################################################
        item1 = r"CONSOLIDATED"
        item2 = r"PARENTHETICAL"
        item3 = r"EQUITY"

        if item1 in report_dict['name_short'].upper() and item2 not in report_dict['name_short'].upper() and item3 not in report_dict['name_short'].upper() and report_dict['position'] < 12:
            #print(report_dict['name_short'].upper())
            statements_url.append(report_dict['url'])


    # NOW WE HAVE THE URLS OF THE STATEMENTS WE WANT TO SCRAPE


    #assuming we want all the statements in a single data set
    statements_data = []

    #loop through each statement url
    for statement in statements_url:

        #define a dictionary that will store the different parts of the statement
        statement_data = {}
        statement_data['headers'] = []
        statement_data['sections'] = []
        statement_data['data'] = []

        #request the statement file content
        content = requests.get(statement, headers=user_agent).content
        report_soup = BeautifulSoup(content, 'html.parser')

        #find all the rows, figure out what type of row it is, parse the elements, and store in teh statement file list.
        #tr = table row
        for index, row in enumerate(report_soup.table.find_all('tr')):

            #first let's get all the elements (td = standard data cell)
            # cols represents elements in the row
            cols = row.find_all('td')

           # if it's a regular row and not a section or a table header (th = header, strong = important)
            if (len(row.find_all('th')) == 0 and len(row.find_all('table')) == 0): # and len(row.find_all('strong')) == 0:
                reg_row = []
                for ele in cols:

                    if len(row.find_all('strong')) != 0:
                        reg_row.append(ele.text.strip().upper())
                    else:
                        reg_row.append(ele.text.strip())

                #reg_row = [ele.text.strip() for ele in cols]
                statement_data['data'].append(reg_row)

                #check if it is a section label and store that it in sec_row
                if len(row.find_all('strong')) != 0:
                    sec_row = cols[0].text.strip().upper()
                    statement_data['sections'].append(sec_row)


            #finally if it's not any of those it must be a header
            elif (len(row.find_all('th')) != 0):
                hed_row = []
                for ele in row.find_all('th'):
                    if (len(ele.find_all('sup'))) == 0:
                        hed_row.append(ele.text.strip())
                statement_data['headers'].append(hed_row)

            else:
                print("We encountered an error")

        statements_data.append(statement_data)

    return statements_data



## Purpose: Checks if a character can be converted into a float

def char_is_float(char):
    try:
        float(char)
        return True
    except:
        return False


## Purpose: Changes a (assumed) string into a float, getting rid of any non-number values in the string in the process.
## Assumptions: We are only interested in strings, so anything else will get a NaN value. In other words, we expect a string
##              but if otherwise then we ignore/erase the passed value as it was not expected and could cause further problems
##              if kept as is.
## Example: Converts '900f' to 900.0

def change_to_float(string):

    #if already a float, no need to continue
    if type(string) == float:
        return float(string)

    #check if the value is a string (since we want to strip the string and that doesn't work for other types)
    elif type(string) == str:

        #get rid of spaces
        string = string.strip()

        #just checking ... again
        if string == 'None':
            return 'NaN'

        #string to append float characters to
        string_to_convert = ""

        #iterate through each element of the string
        for i, char in enumerate(string):

            #check the first element of the string, as that can be a minus sign, otherwise only append chars that are numbers
            if i == 0:
                if char_is_float(char) or char == '-':
                    string_to_convert = string_to_convert + char

                #if the first character is not a number, why bother
                else:
                    return None
            else:
                if char_is_float(char):
                    string_to_convert = string_to_convert + char

        return float(string_to_convert)

    #if not a float or a string, I'm assuming its a Nonetype. Return NaN because that is float terminology
    else:
        return 'NaN'



## Purpose: Gets rid of any columns in a pandas datframe that do not contain any information (i.e. irrelevant)
def get_rid_of_null_columns(df):

    #store the column index of columns we want to drop in a list
    column_index_to_drop = []

    #for each column in the dataframe
    for i in range(df.shape[1]):

        #if all values within that column are NaN, assign that column to be dropped
        if df[df.columns[i]].isnull().all():
            column_index_to_drop.append(i)

    df.drop(df.columns[column_index_to_drop], axis = 1, inplace=True)

    return df


## Parameters: Takes in a dictionary called statements data that holds 'headers' and 'data' from the html that describes
##             the financial statements scraped from the SEC website. The 'headers' describe the columns, while the 'data'
##             are the elements below the 'headers' in the table. Statements data contains multiple documents, but this funciton
##             only works with one statement, so a number describing what statement from statements data is given as a
##             parameter.
##
## Purpose:    Converts a dictionary describing financial data into a pandas dataframe. There are many steps to cleaning
##             the data so that it can be machine readable (e.g. cleaning the data, dealing with edge cases such as multiple
##             levels of headers)

def convert_statements_data_to_pandas(statements_data, statements_num):

    #take the raw table data (without the headers)
    balance_data = statements_data[statements_num]['data']

    df = pd.DataFrame(balance_data)

    #Define the Index column as the first column
    df.index = df[0]

    #since the index makes up the first column, we can get rid of the first column
    df = df.drop(0, axis = 1)

    # Get rid of the '$', '(', ')', and convert the '' to NaNs.
    df = df.replace('[\$,)]','', regex=True )\
                     .replace( '[(]','-', regex=True)\
                     .replace( '', 'NaN', regex=True)

    #convert each element in the table portion into a float (excluding indexes or headers)
    for i in range(df.shape[1]):

        #apply change_to_float which cleans the element to be prepared to turn into a float
        df[df.columns[i]] = df[df.columns[i]].apply(change_to_float)

    #change_to_float should already accomplish this, but this is to double check if any values were not converted into floats
    df = df.astype(float)

    df = get_rid_of_null_columns(df)


    # Now we need the headers for the document (as well as the document's name)
    # This is also stored in the statements_data under headers

    # Because the headers may either have one or two levels in the financial statement (sometimes over the year, there is
    # a statement like "12 months ended in"), we need to specify the headers that match up best with the columns

    # This may not make a whole bunch of sense but that's because getting the headers is specific to two different types
    # of headers for the financial documents.

    #if the headers only have one level (one row that holds all the headers)
    if len(statements_data[statements_num]['headers']) == 1:

        #headers get all the values in 'headers' except the first one which is used as the header for the index
        header = statements_data[statements_num]['headers'][0][1:]
        document = statements_data[statements_num]['headers'][0][0]

    #if the headers have two levels (there are two rows that hold all the headers)
    elif len(statements_data[statements_num]['headers']) == 2:

        #headers get the bottom row
        header = statements_data[statements_num]['headers'][-1]

        #document name gets first element of the top row
        document = statements_data[statements_num]['headers'][0][0]

    #there are probably more edge cases, so we'll just keep everything the same to keep things moving
    else:
        header = df.columns
        document = 'Category'


    try:
        df.columns = header
        df.index.name = document
    except:
        print('title error')
        df = pd.DataFrame()


    return df


## Purpose: Some indices repeat in a financial statement (e.g. others). To make sure each index is unique without
##          losing information in the dataframe, we can add a tag to the end. The number of tags at the end represent
##          the number of times that index value has been seen before (no tag means first time, one tag means second, two
##          tags means third)
def add_tags_to_repeating_indices(df, tag):
    name = df.index.name
    idx = df.index.to_list()
    dup = {x for x in idx if idx.count(x) > 1}

    for ele in dup:
        end = ''
        for i in range(len(idx)):
            if ele == idx[i]:
                idx[i] = idx[i] + end
                end = end + tag

    df.index = idx
    df.index.name = name
    return df


def add_tags_for_sections(sections, df):
    if len(sections) < 2:
        idx = df.index.to_list()
        name = df.index.name
        idx_tags = []
        for ele in idx:
            idx_tags.append(ele + '-' + str(1))
        df.index = idx_tags
        df.index.name = name
        return df

    idx = df.index.to_list()
    name = df.index.name

    idx_tags = []

    count = 0

    for ele in idx:
        if ele in sections:
            count = count + 1
        idx_tags.append(ele + '-' + str(count))


    df.index = idx_tags
    df.index.name = name

    return df


### Function: Filings within a set year range
### Purpose: Takes the master list of all filings, and culls it a set number of years starting at the latest desired year
### Returns: A list of dictionaries containing information on filings based on year

def filings_within_year_range(master_list, filing, latest_year, num_years):

    culled_master_list = []

    #run loop until we run out of asked-for years
    while num_years > 0:

        #for each dictionary in the master list, check if the filing matches the asked-for year and is the exact filing
        #and then appends that dictionary to the new master list
        for file in master_list:
            if file['file_year'] == latest_year:
                if file['file_type'] == filing:
                    culled_master_list.append(file)

        latest_year = latest_year - 1

        num_years = num_years - 1

    return culled_master_list


def get_statements_data_from_filing_to_dataframes(filing, CIK_num, user_agent):
    json_url = get_filing_json(filing, CIK_num, user_agent)
    xml_summary = get_xml_Filing_Summary(json_url, user_agent)

    master_reports = parse_xml_summary_of_file(xml_summary, user_agent)

    statements_data = grab_financial_statements(master_reports, user_agent)

    dataframes = []
    for i in range(len(statements_data)):
        df = convert_statements_data_to_pandas(statements_data, i)
        df = add_tags_for_sections(statements_data[i]['sections'], df)
        df = add_tags_to_repeating_indices(df, '@')
        dataframes.append(df)

    return dataframes


### Function: Scrape Company Financial Statements
### Input: Company's CIK number, the type of filing you are searching for, the year you want to start from and
###        the number of years you want to go back from that starting year, and the user agent to access the SEC website
### Purpose: Performs a query search on the SEC website for a company's filings, accesses that filing, and then pulls out
###          the relevant financial statements (balance sheet, cash flow, income, etc.) into a pandas dataframe
### Returns: A 2-dimensional array of dataframes with the rows being the years and the columns being which financial statement

def scrape_company_financial_statements(CIK_num, filing_type, start_year, num_years, user_agent):

    #query for a master list of all filings given a CIK_number and a filing type
    master_list = get_all_filings(CIK_num, filing_type, user_agent)

    #focus the master list on the years you want
    culled_master_list = filings_within_year_range(master_list, filing_type, start_year, num_years)


    #array to store dataframes
    dfs = []

    #for each filing in the master list
    for filing in culled_master_list:

        #get the statements data from the filing and store it in pandas dataframes
        dataframes = get_statements_data_from_filing_to_dataframes(filing, CIK_num, user_agent)
        dfs.append(dataframes)

    #financial statements tend to have multiple years, but we just want the current year so we drop the other columns
    for i in range(len(dfs)):
        for j in range(len(dfs[i])):

            #columns = years, drop all the columns that isn't the first one
            dfs[i][j].drop(columns=dfs[i][j].columns[1:], axis=1, inplace=True)

    return dfs


def combine_yearly_financial_statements(dfs):
    num_docs = len(dfs[0])

    multi_year_statements = []
    for i in range(num_docs):
        year_statements = []
        for ele in dfs:
            if len(ele) == num_docs:
                year_statements.append(ele[i])
            else:
                print(len(ele))
        multi_year_statements.append(year_statements)

    combined_financial_statements = []

    for i in range(len(multi_year_statements)):
        combined_fs = pd.concat(multi_year_statements[i], axis=1)
       # combined_fs.index.name = multi_year_statements[i][0].index.name
        combined_financial_statements.append(combined_fs)

    return combined_financial_statements


def reindex_combined_financial_statements(combined_financial_statements):

    for i in range(len(combined_financial_statements)):
        current_index = list(combined_financial_statements[i].index)

        current_tag = 1
        num_elements_with_tag = 0

        new_index = []
        while True:
            for name in current_index:
                if name[-1] == str(current_tag):
                    new_index.append(name)
                    num_elements_with_tag = num_elements_with_tag + 1
                elif name[-1] == '@':
                    if name[-2] == str(current_tag):
                        new_index.append(name)
                        num_elements_with_tag = num_elements_with_tag + 1

            if num_elements_with_tag < 1:
                break
            current_tag = current_tag + 1
            num_elements_with_tag = 0


        combined_financial_statements[i] = combined_financial_statements[i].reindex(new_index)

    return combined_financial_statements


def scrape_company_financial_statements_combined(CIK_num, filing_type, start_year, num_years, user_agent):
    statements_dataframes = scrape_company_financial_statements(CIK_num, filing_type, start_year, num_years, user_agent)
    combined_financial_statements = combine_yearly_financial_statements(statements_dataframes)
    combined_financial_statements = reindex_combined_financial_statements(combined_financial_statements)

    return combined_financial_statements



def get_summaries(CIK_num, filing_type, start_year, num_years, user_agent):
    #query for a master list of all filings given a CIK_number and a filing type
    master_list = get_all_filings(CIK_num, filing_type, user_agent)

    #focus the master list on the years you want
    culled_master_list = filings_within_year_range(master_list, filing_type, start_year, num_years)


    #for each filing in the master list
    for filing in culled_master_list:
        json_url = get_filing_json(filing, CIK_num, user_agent)
        xml_summary = get_xml_Filing_Summary(json_url, user_agent)

        print_xml_summaries(xml_summary, user_agent)
        #get the statements data from the filing and store it in pandas dataframes



def print_xml_summaries(xml_summary, user_agent):
        #define a new base url that represents the filing folder. This will come in handy when we need to download the reports
    base_url = xml_summary.replace('FilingSummary.xml', '')

    #request and parse the content (use .content because this is an xml file not json)
    content = requests.get(xml_summary, headers=user_agent).content

    #create a soup object to parse the content using BeautifulSoup
    soup = BeautifulSoup(content, 'lxml')

    #find the 'myreports' tag because this contains all the individual reports submitted
    reports = soup.find('myreports')

    #want a list ot store all theindividual components of the report, so create the master list
    master_reports = []

    # loop through each report in the 'myreports' tag but avoid the last one as this will cause an error
    # (last one has differnent formatting).
    for index, report in enumerate(reports.find_all('report')[:-1]):

        #create a dictionary to store all the differnet parts we need
        report_dict = {}
        report_dict['name_short'] = report.shortname.text
        report_dict['name_long'] = report.longname.text
        report_dict['position'] = index+1
        #report_dict['category'] = report.menucategory.text
        report_dict['url'] = base_url + report.htmlfilename.text

        #append the dictionary to the master list.
        master_reports.append(report_dict)


        #print the info to the user.
        print('-'*100)
        print(base_url + report.htmlfilename.text)
        print(report.longname.text)
        print(report.shortname.text)
        #print(report.menucategory."text)
        print(index+1)
