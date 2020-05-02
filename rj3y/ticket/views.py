from django.shortcuts import render
import requests
import pandas
from bs4 import BeautifulSoup
# Create your views here.


def index(request):

    context = {
        'message': '',
    }
    if not request.POST:
        return render(request, 'ticket/index.html', context)
    else:
        try:
            context['message'] = 'start..'
            account = request.POST.get('account')
            password = request.POST.get('password')
            session = requests.session()
            chracter_choose = request.POST.get('character')
            ticket_type = request.POST.get('ticket_type')
            has_file_url = (request.POST.get('has_file_url') == 'true')
            search_column = 'disp_seq'
            query_string = ''
            max_count = None
            chracters = {
                'cloud': '20',
                'self': account,
            }
            response_login = login_with_given_session(account=account, password=password, session=session)
            context['message'] = 'login..'
            search_http_response = search_on_dashboard_terminal(
                session=session,
                character=chracters[chracter_choose],
                search_column=search_column,
                query_string=query_string,
                max_count=max_count
            )
            ticket_tables = get_dataframe_list_by_reading_html(search_http_response.text)
            # take the part we want as a dictionary
            ticket_tables = {
                'preordered': ticket_tables[2],
                'assigned': ticket_tables[3],
                'handling': ticket_tables[4],
                'finished': ticket_tables[5],
                'special': ticket_tables[6],
            }
            context['message'] = 'get ticket table..'
            for key, value in ticket_tables.items():
                value = let_the_first_row_be_column_title(value)
                value = clean_the_column_of_ticket_number(value)
                ticket_tables[key] = value
            context['results'] = {}
            if ticket_type != 'all':
                if has_file_url:
                    ticket_number_list = list(ticket_tables[ticket_type]['單號'])
                    urls = [ get_ticket_file_url_with_given_ticket_number(ticket_number=ticket, session=session) for ticket in ticket_number_list ]
                    ticket_tables[ticket_type] = ticket_tables[ticket_type].assign(建置單檔案=urls)
                df_joined = join_ticket_detail_with_ticket_list(
                    ticket_numbers=list(ticket_tables[ticket_type]['單號']),
                    session=session,
                    character=chracters[chracter_choose],
                    ticket_tables=ticket_tables,
                    ticket_type=ticket_type
                )
                context['results'][ticket_type] = df_joined.to_html(justify='left')
            else:
                for ticket_type, value in ticket_tables.items():
                    try:
                        if has_file_url:
                            ticket_number_list = list(ticket_tables[ticket_type]['單號'])
                            urls = [ get_ticket_file_url_with_given_ticket_number(ticket_number=ticket, session=session) for ticket in ticket_number_list ]
                            ticket_tables[ticket_type] = ticket_tables[ticket_type].assign(建置單檔案=urls)
                    except:
                        pass
                    try:
                        df_joined = join_ticket_detail_with_ticket_list(
                            ticket_numbers=list(ticket_tables[ticket_type]['單號']),
                            session=session,
                            character=chracters[chracter_choose],
                            ticket_tables=ticket_tables,
                            ticket_type=ticket_type
                        )
                        context['results'][ticket_type] = df_joined.to_html(justify='left')
                    except:
                        pass
            context['message'] = 'Finished.'
        except:
            pass
        return render(request, 'ticket/index.html', context)

def login_with_given_session(account, password, session):
    post_url = 'http://202.3.168.17:8080/login_check.jsp'
    post_data = {
        'sess_id': account,
        'sess_password': password,
        'dfForm': 'login.jsp',
    }
    http_response = session.post(url=post_url, data=post_data)
    return http_response

def search_on_dashboard_terminal(session, character, search_column, query_string, max_count):
    post_url = 'http://202.3.168.17:8080/Disp/DashBoard_Terminal.jsp?action=search'
    post_data = {
        'recordCount': max_count,
        'searchColumn': search_column,
        'searchCondition': query_string,
        'doSearch': 'Search',
        'character': character,
    }
    http_response = session.post(url=post_url, data=post_data)
    return http_response

def get_dataframe_list_by_reading_html(html):
    return pandas.read_html(html)

def let_the_first_row_be_column_title(dataframe):
    new_dataframe = dataframe[1:]
    new_dataframe.columns = dataframe.iloc[0]
    return new_dataframe

def clean_the_column_of_ticket_number(dataframe):
    for index, row in dataframe.iterrows():
        row['單號'] = row['單號'].replace(' (Delay)', '')
    return dataframe

def get_ticket_detail_with_given_ticket_number(session, chracter, ticket_number):
    post_url = 'http://202.3.168.17:8080/Disp/retriveDetail.jsp'
    post_data = {
        'method': 'get_Disp_DetailCons',
        'Disp_Cons_Seq': chracter,
        'Disp_Grp_Seq': chracter,
        'Disp_Seq': ticket_number,
    }
    http_response = session.post(url=post_url, data=post_data)
    return http_response

def join_ticket_detail_with_ticket_list(ticket_numbers, session, character, ticket_tables, ticket_type):
    df_list = []
    for ticket_number in ticket_numbers:
        ticket_detail_response = get_ticket_detail_with_given_ticket_number(
            session=session,
            chracter=character,
            ticket_number=ticket_number
        )
        df_ticket_detail = get_dataframe_list_by_reading_html(ticket_detail_response.text)[0]
        df_ticket_detail = let_the_first_row_be_column_title(df_ticket_detail)
        df_ticket_detail = df_ticket_detail.assign(單號=ticket_number)
        df_list += [df_ticket_detail]
    df_left = ticket_tables[ticket_type]
    df_right = pandas.concat(df_list)
    df_joined = pandas.merge(df_left, df_right, on='單號', how='outer', suffixes=('', '-細項'))
    return df_joined

def get_ticket_file_url_with_given_ticket_number(ticket_number, session):
    post_url = 'http://202.3.168.17:8080/Disp/DashBoard_Terminal_Detail.jsp'
    post_data = {
        'seq_no': ticket_number,
    }
    response = session.post(url=post_url, data=post_data)
    soup = BeautifulSoup(response.text, 'lxml')
    tag_set = soup.select('body > table > tr:nth-child(2) > td > fieldset > table > tr:nth-child(1) > td > ol > li > input[type=button]:nth-child(1)')
    if len(tag_set) == 1:
        tag = tag_set[0]
    else:
        tag = None
    if tag:
        url = tag['onclick'].split(',')[0].split('"')[1]
    else:
        url = ''
    return url
