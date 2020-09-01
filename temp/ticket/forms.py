from django import forms

class TicketForm(forms.Form):
    account = forms.CharField(
        widget=forms.TextInput(attrs={'class': 'form-control'}),
        label='Account',
        max_length=32,
    )
    password = forms.CharField(
        widget=forms.TextInput(attrs={'class': 'form-control'}),
        label='Password',
        max_length=32,
    )
    character = forms.ChoiceField(
        widget=forms.Select(attrs={'class': 'form-control'}),
        label='Character',
        choices=(
            ('cloud', '雲端'),
            ('self', '個人'),
        ),
    )
    ticket_type = forms.ChoiceField(
        widget=forms.Select(attrs={'class': 'form-control'}),
        label='Ticket Type',
        choices=(
            ('all', '全部'),
            ('預先通知派工單', '預先通知派工單'),
            ('已轉派派工單', '已轉派派工單'),
            ('處理中派工單', '處理中派工單'),
            ('完成待結派工單', '完成待結派工單'),
            ('特殊申請派工單', '特殊申請派工單'),
        ),
    )
    join_detail = forms.ChoiceField(
        widget=forms.Select(attrs={'class': 'form-control'}),
        label='Join Detail',
        choices=(
            ('true', '是'),
            ('false', '否'),
        ),
        initial='true',
    )
    add_pdf_url = forms.ChoiceField(
        widget=forms.Select(attrs={'class': 'form-control'}),
        label='Add PDF URL',
        choices=(
            ('true', '是'),
            ('false', '否'),
        ),
        initial='false',
    )