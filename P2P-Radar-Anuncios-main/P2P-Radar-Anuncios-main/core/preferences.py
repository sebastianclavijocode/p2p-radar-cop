"""Only non-secret user configuration may enter browser persistence."""
import json
import re
EXACT={'radar-view','capital_cfg','taker_cfg','maker_fees','mappings','custom_methods','saved-route-exclusions','saved-route-strategies','excluded-route-venues','route-strategies','auto_refresh_sel','scan_fiats','scan_min','scan_rows'}
PREFIXES=('cfg-p2p-','cfg-rulo-','rulo-fee-','quote-volume-','fee_input_','csim_','taker_')
def clean_preferences(data):
    if not isinstance(data,dict):return {}
    result={}
    for key,value in data.items():
        if not isinstance(key,str) or not (key in EXACT or key.startswith(PREFIXES)):continue
        try:
            encoded=json.dumps(value,allow_nan=False)
            if len(encoded)>50000:continue
            result[key]=json.loads(encoded)
        except (ValueError,TypeError):continue
    return result

def filter_catalog(catalog,fiats=None,excluded=()):
    return [m for m in catalog if (fiats is None or m['fiat'] in fiats) and m['id'] not in excluded]

def normalize_method(value):
    return re.sub(r'[^a-z0-9]','',str(value).casefold())

def hidden_method(name,aliases):
    name=normalize_method(name)
    return any(name==normalize_method(a) or (not normalize_method(a).isdigit() and name.startswith(normalize_method(a))) for a in aliases if normalize_method(a))
