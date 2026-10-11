from core.preferences import clean_preferences, filter_catalog, hidden_method


def test_only_personal_settings_persist():
    data={'cfg-p2p-fiats':['COP'],'cfg-rulo-capital':2000000,'csim_COP':3000000,
          'auto_refresh_sel':'30 seg','tg_token':'secret','BYBIT_API_KEY':'secret',
          'results':[{'price':123}],'last_update':123,'rulo-fee-test':float('nan')}
    assert clean_preferences(data)=={k:data[k] for k in ('cfg-p2p-fiats','cfg-rulo-capital','csim_COP','auto_refresh_sel')}
    assert clean_preferences(None)=={}


def test_methods_and_currency_exclusions():
    catalog=[{'id':'prex','fiat':'UYU'},{'id':'mp','fiat':'ARS'},
             {'id':'prexusd','fiat':'USD'},{'id':'nequi','fiat':'COP'}]
    assert filter_catalog(catalog,['COP','USD'],['prexusd'])==[catalog[-1]]
    assert filter_catalog(catalog,[],[])==[]
    assert hidden_method('Prex Uruguay',['Prex'])
    assert hidden_method('Mercado Pago Argentina',['Mercado Pago'])
    assert hidden_method('209',['209'])
    assert not hidden_method('2099',['209'])
    assert not hidden_method('Nequi',['Prex','Mercado Pago',''])


def test_mount_restores_before_widgets_and_retains_inactive_settings(monkeypatch):
    from ui import preferences as ui
    state={}
    monkeypatch.setattr(ui.st,'session_state',state)
    calls=[]
    def component(**kwargs):
        calls.append(kwargs)
        return {'preferences':{'cfg-p2p-fiats':['COP'],'cfg-rulo-capital':5000000,'tg_token':'never'}}
    monkeypatch.setattr(ui,'_component',component)
    ui.mount()
    assert state['cfg-p2p-fiats']==['COP']
    assert 'tg_token' not in state
    state['cfg-p2p-fiats']=['COP','USD']
    ui.mount()
    del state['cfg-p2p-fiats']
    ui.mount()
    assert state['cfg-p2p-fiats']==['COP','USD']
    assert calls[-1]['hydrated'] is True
    assert calls[-1]['preferences']['cfg-rulo-capital']==5000000
