from django.shortcuts import render
import requests
import pandas
from bs4 import BeautifulSoup
# Create your views here.


def index(request):

    context = {
        'message': '',
        'result': None,
    }
    if not request.POST:
        return render(request, 'ticket/index.html', context)
    else:
        try:
            account = request.POST.get('account')
            context['account'] = account
            password = request.POST.get('password')
            context['password'] = password
            character = request.POST.get('character')
            context['character'] = request.POST.get('character')
            ticket_type = request.POST.get('ticket_type')
            add_file_url = (request.POST.get('add_file_url') == 'true')
            join_ticket_detail = (request.POST.get('join_ticket_detail') == 'true')
            if character == 'self':
                character_id = account
            elif character == 'cloud':
                character_id = '20'
            session = login(account=account, password=password)
        except:
            context['message'] = 'Login failed'
        try:
            response_dashboard = request_dashboard(session=session, character_id=character_id)
            ticket_tables = produce_ticket_tables(html=response_dashboard.text)
            ticket_tables = {key:clean_data(use_first_row_as_title(value)) for key, value in ticket_tables.items()}
        except:
            context['message'] = 'Request about http://202.3.168.17:8080/index.jsp failed.'
        try:
            if add_file_url and ticket_type != 'all':
                ticket_tables[ticket_type] = add_column_file_url(ticket_tables[ticket_type], session=session)
            elif add_file_url and ticket_type == 'all':
                ticket_tables = {key:add_column_file_url(value, session=session) for key, value in ticket_tables.items()}
        except:
            context['message'] = 'Adding file url failed.'
        try:
            ticket_detail_tables = {}
            if join_ticket_detail and ticket_type != 'all':
                ticket_detail_tables[ticket_type] = produce_ticket_detail_table(session=session, character_id=character_id, dataframe=ticket_tables[ticket_type], ticket_type=ticket_type)
            elif join_ticket_detail and ticket_type == 'all':
                ticket_detail_tables = {key:produce_ticket_detail_table(session=session, character_id=character_id, dataframe=value, ticket_type=key) for key, value in ticket_tables.items()}
        except:
            context['message'] = 'Request about http://202.3.168.17:8080/Disp/retriveDetail.jsp failed.'
        try:
            result = {}
            if join_ticket_detail and ticket_type != 'all':
                left = ticket_tables[ticket_type]
                right = ticket_detail_tables[ticket_type]
                joined = pandas.merge(left, right, on='單號', how='outer', suffixes=('', '-細項'))
                result[ticket_type] = joined.to_html(justify='left')
            elif join_ticket_detail and ticket_type == 'all':
                for key, value in ticket_tables.items():
                    try:
                        left = value
                        right = ticket_detail_tables[key]
                        joined = pandas.merge(left, right, on='單號', how='outer', suffixes=('', '-細項'))
                        result[key] = joined.to_html(justify='left')
                    except:
                        pass
            elif not join_ticket_detail and ticket_type != 'all':
                left = ticket_tables[ticket_type]
                if len(left):
                    result[ticket_type] = left.to_html(justify='left')
            elif not join_ticket_detail and ticket_type == 'all':
                for key, value in ticket_tables.items():
                    try:
                        left = value
                        result[key] = left.to_html(justify='left')
                    except:
                        pass
            context['result'] = result
            context['message'] = 'Finished.'
        except:
            context['message'] = 'Joining ticket list with detail failed.'
        return render(request, 'ticket/index.html', context)

def login(account, password):
    url = 'http://202.3.168.17:8080/login_check.jsp'
    data = {
        'sess_id': account,
        'sess_password': password,
        'dfForm': 'login.jsp',
    }
    session = requests.session()
    response = session.post(url=url, data=data)
    return session

def request_dashboard(session, character_id):
    url = 'http://202.3.168.17:8080/Disp/DashBoard_Terminal.jsp?action=search'
    data = {
        'character': character_id,
    }
    response = session.post(url=url, data=data)
    return response

def produce_ticket_tables(html):
    dataframes = pandas.read_html(html)
    # take the part we want to build a dictionary
    ticket_tables = {
        'advanced': dataframes[2],
        'assigned': dataframes[3],
        'processing': dataframes[4],
        'finished': dataframes[5],
        'special': dataframes[6],
    }
    return ticket_tables

def use_first_row_as_title(dataframe):
    title = dataframe.iloc[0]
    dataframe = dataframe[1:]
    dataframe.columns = title
    return dataframe

def clean_data(dataframe):
    for index, row in dataframe.iterrows():
        row['單號'] = row['單號'].replace(' (Delay)', '')
    return dataframe

def add_column_file_url(dataframe, session):
    file_urls = []
    for index, row in dataframe.iterrows():
        file_url = ''
        try:
            ticket_number = row['單號']
            url = 'http://202.3.168.17:8080/Disp/DashBoard_Terminal_Detail.jsp'
            data = {
                'seq_no': ticket_number,
            }
            response = session.post(url=url, data=data)
            soup = BeautifulSoup(response.text, 'lxml')
            tags = soup.select('body > table > tr:nth-child(2) > td > fieldset > table > tr:nth-child(1) > td > ol > li > input[type=button]:nth-child(1)')
            file_url = tags[0]['onclick'].split(',')[0].split('"')[1]
        except:
            pass
        file_urls.append(file_url)
    dataframe = dataframe.assign(建置單檔案=file_urls)
    return dataframe

def produce_ticket_detail_table(session, character_id, dataframe, ticket_type):
    ticket_detail_dataframes = []
    for index, row in dataframe.iterrows():
        try:
            ticket_number = row['單號']
            url = 'http://202.3.168.17:8080/Disp/retriveDetail.jsp'
            method = 'get_Disp_DetailCons'
            if ticket_type == 'finished':
                method = 'get_Disp_DetailCons_Finish'
            data = {
                'method': method,
                'Disp_Cons_Seq': character_id,
                'Disp_Grp_Seq': character_id,
                'Disp_Seq': ticket_number,
            }
            detail_response = session.post(url=url, data=data)
            ticket_detail_dataframe = pandas.read_html(detail_response.text)[0]
            ticket_detail_dataframe = use_first_row_as_title(ticket_detail_dataframe)
            ticket_detail_dataframe = ticket_detail_dataframe.assign(單號=ticket_number)
            ticket_detail_dataframes.append(ticket_detail_dataframe)
        except:
            pass
    if ticket_detail_dataframes:
        ticket_detail_table = pandas.concat(ticket_detail_dataframes)
    else:
        ticket_detail_table = None
    return ticket_detail_table