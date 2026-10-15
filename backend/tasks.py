PRIORITIES = {'low','medium','high'}
STATUSES = {'todo','in_progress','done'}

def validate(data, existing=None):
    if not isinstance(data,dict): raise ValueError('Expected a JSON object')
    d = dict(existing or {})
    for key in ('title','description','priority','status'):
        if key in data: d[key]=data[key]
    title=d.get('title','')
    desc=d.get('description','')
    if not isinstance(title,str) or not 1 <= len(title.strip()) <= 120: raise ValueError('Title must be 1–120 characters')
    if not isinstance(desc,str) or len(desc)>2000: raise ValueError('Description must be at most 2000 characters')
    if d.get('priority','medium') not in PRIORITIES: raise ValueError('Invalid priority')
    if d.get('status','todo') not in STATUSES: raise ValueError('Invalid status')
    return dict(title=title.strip(),description=desc.strip(),priority=d.get('priority','medium'),status=d.get('status','todo'))
