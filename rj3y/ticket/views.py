from django.shortcuts import render
import requests
import pandas
# Create your views here.


def index(request):

    context = {
        'error_message': 'Sorry, something may go wrong.',
        'full_html': None,
    }
    if not request.POST:
        return render(request, 'index.html', context)
    else:
        try:
            account = request.POST.get('account')
            password = request.POST.get('password')
            session = requests.session()
            session = get_session_login(account=account, password=password, session=session)
            df_handling_ticket = get_df_handling_ticket(session)
            df_handling_ticket_with_title = let_the_first_row_be_column_title(df_handling_ticket)
            handling_ticket_number_list = list(df_handling_ticket_with_title['單號'])
            df_list = []
            for ticket_number in handling_ticket_number_list:
                df_ticket_detail = get_df_ticket_detail(session=session, account=account, ticket_number=ticket_number)
                df_ticket_detail_with_title = let_the_first_row_be_column_title(df_ticket_detail)
                df_ticket_detail_with_title_with_ticket_number = df_ticket_detail_with_title.assign(單號=ticket_number)
                df_list += [df_ticket_detail_with_title_with_ticket_number]
            df_ticket_detail_total = pandas.concat(df_list)
            df_left = df_ticket_detail_total
            df_right = df_handling_ticket_with_title.drop(columns=['流程'])
            result = pandas.merge(df_left, df_right, on='單號', how='left')
            context['full_html'] = result.to_html()
        except:
            pass
        return render(request, 'summary.html', context)

def get_session_login(account, password, session):
    login_url = 'http://202.3.168.17:8080/login_check.jsp'
    login_data = {
        'sess_id': account,
        'sess_password': password,
        'dfURL': '',
        'dfFrame_no': 2,
        'dfAction': '',
        'dfId': '',
        'dfForm': 'login.jsp'
    }
    session.post(url=login_url, data=login_data)
    return session

def get_df_handling_ticket(session):
    dashboard_terminal_url = 'http://202.3.168.17:8080/Disp/DashBoard_Terminal.jsp'
    response_dashboard_terminal = session.get(url=dashboard_terminal_url)
    df_read_html_response_dashboard_terminal_text = pandas.read_html(response_dashboard_terminal.text)
    df_handling_ticket = df_read_html_response_dashboard_terminal_text[4]
    return df_handling_ticket

def let_the_first_row_be_column_title(dataframe):
    new_dataframe = dataframe[1:]
    new_dataframe.columns = dataframe.iloc[0]
    return new_dataframe

def get_df_ticket_detail(session, account, ticket_number):
    ticket_detail_url = 'http://202.3.168.17:8080/Disp/retriveDetail.jsp'
    ticket_detail_data = {
        'method': 'get_Disp_DetailCons',
        'Disp_Cons_Seq': account,
        'Disp_Seq': ticket_number,
    }
    response_ticket_detail = session.post(url=ticket_detail_url, data=ticket_detail_data)
    df_read_html_response_ticket_detail_text = pandas.read_html(response_ticket_detail.text)
    df_ticket_detail = df_read_html_response_ticket_detail_text[0]
    return df_ticket_detail
