from django.shortcuts import render
import requests
import pandas
from bs4 import BeautifulSoup
# Create your views here.


def index(request):

    context = {
        'message': '',
        'query_param_cookie': {},
        'result': {},
    }
    if not request.POST:
        return render(request, 'ticket/index.html', context)
    else:
        try:
            account = request.POST.get('account')
            context['query_param_cookie']['account'] = account
            password = request.POST.get('password')
            context['query_param_cookie']['password'] = password
            character = request.POST.get('character')
            ticket_type = request.POST.get('ticket_type')
            add_file_url = (request.POST.get('add_file_url') == 'true')
            join_ticket_detail = (request.POST.get('join_ticket_detail') == 'true')
            message_if_no_data_in_table = '<p>Oops, no data to show here.</p>'
            if character == 'self':
                character_id = account
            elif character == 'cloud':
                character_id = '20'
            session = login(account=account, password=password)
        except:
            context['message'] = 'Login failed.'
        try:
            response_dashboard = request_dashboard(session=session, character_id=character_id)
            ticket_table_titles = get_ticket_table_titles(html=response_dashboard.text)
            ticket_tables = get_ticket_tables(html=response_dashboard.text)
            ticket_tables = dict(zip(ticket_table_titles, ticket_tables))                
        except:
            context['message'] = 'Parsing http://202.3.168.17:8080/Disp/DashBoard_Terminal failed.'
        try:
            if add_file_url and ticket_type != 'all':
                ticket_tables[ticket_type] = add_column_file_url(ticket_tables[ticket_type], session=session)
            elif add_file_url and ticket_type == 'all':
                ticket_tables = {key:add_column_file_url(value, session=session) for key, value in ticket_tables.items()}
        except:
            context['message'] = 'Adding PDF url failed.'
        try:
            ticket_detail_tables = {}
            if join_ticket_detail and ticket_type != 'all':
                ticket_detail_tables[ticket_type] = produce_ticket_detail_table(session=session, character_id=character_id, dataframe=ticket_tables[ticket_type], ticket_type=ticket_type)
            elif join_ticket_detail and ticket_type == 'all':
                ticket_detail_tables = {key:produce_ticket_detail_table(session=session, character_id=character_id, dataframe=value, ticket_type=key) for key, value in ticket_tables.items()}
        except:
            context['message'] = 'Request http://202.3.168.17:8080/Disp/retriveDetail.jsp failed.'
        try:
            if ticket_type == 'all':
                ticket_type_que = ticket_table_titles
            else:
                ticket_type_que = [ticket_type]
            if join_ticket_detail:
                for ticket_type in ticket_type_que:
                    left = ticket_tables[ticket_type]
                    right = ticket_detail_tables[ticket_type]
                    if len(left) > 0 and len(right) > 0:
                        joined = pandas.merge(left=ticket_tables[ticket_type], right=ticket_detail_tables[ticket_type], on='單號', how='outer', suffixes=('', '-細項'))
                        joined.index = pandas.RangeIndex(start=1, stop=len(joined)+1, step=1)
                        context['result'][ticket_type] = joined.to_html(justify='left', render_links=True)
                    else:
                        context['result'][ticket_type] = message_if_no_data_in_table
            else:
                for ticket_type in ticket_type_que:
                    joined = ticket_tables[ticket_type]
                    if len(joined):
                        joined.index = pandas.RangeIndex(start=1, stop=len(joined)+1, step=1)
                        context['result'][ticket_type] = joined.to_html(justify='left', render_links=True)
                    else:
                        context['result'][ticket_type] = message_if_no_data_in_table

            
            context['message'] = 'Finished.'
        except:
            context['message'] = 'Failed.'
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

def use_first_row_as_title(dataframe):
    title = dataframe.iloc[0]
    dataframe = dataframe[1:]
    dataframe.columns = title
    return dataframe

def clean_data(dataframe):
    for index, row in dataframe.iterrows():
        if ' (Delay)' in row['單號']:
            row['單號'] = row['單號'][:row['單號'].index(' (Delay)')]
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

def get_ticket_table_titles(html):
    soup = BeautifulSoup(html, 'lxml')
    h2_tags = soup.select('body div.content table tr td h2')
    h2_texts = []
    for h2_tag in h2_tags:
        h2_text = h2_tag.text
        if '\xa0' in h2_text:
            h2_text = h2_text[:h2_text.index('\xa0')]
        h2_texts.append(h2_text)
    return h2_texts

def get_ticket_tables(html):
    soup = soup = BeautifulSoup(html, 'lxml')
    table_tags = soup.select('body div.content table tr td div.CSSTableGenerator table')    
    ticket_dataframes = []
    for table_tag in table_tags:
        ticket_dataframe = pandas.read_html(str(table_tag))[0]
        ticket_dataframe = use_first_row_as_title(ticket_dataframe)
        ticket_dataframe = clean_data(ticket_dataframe)
        ticket_dataframe.index = pandas.RangeIndex(start=1, stop=len(ticket_dataframe)+1, step=1)
        ticket_dataframes.append(ticket_dataframe)
    return ticket_dataframes

def produce_ticket_detail_table(session, character_id, dataframe, ticket_type):
    ticket_detail_dataframes = []
    for index, row in dataframe.iterrows():
        try:
            ticket_number = row['單號']
            url = 'http://202.3.168.17:8080/Disp/retriveDetail.jsp'
            if ticket_type == '完成待結派工單':
                method = 'get_Disp_DetailCons_Finish'
            elif ticket_type == '已轉派派工單':
                method = 'get_Disp_DetailConsAccept'
            else:
                method = 'get_Disp_DetailCons'
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
        ticket_detail_table = pandas.DataFrame()
    return ticket_detail_table