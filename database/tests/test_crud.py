import pathlib,sys
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]))
import crud

def test_crud(tmp_path,monkeypatch):
    monkeypatch.setenv('DATABASE_PATH',str(tmp_path/'tasks.db'))
    crud.init()
    task=crud.insert({'title':'Example','description':'','priority':'low','status':'todo'})
    assert task['id']>0 and crud.find(task['id'])['title']=='Example'
    assert crud.listing(status='todo')[0]['id']==task['id']
    new=crud.update(task['id'],{'title':'Updated','description':'','priority':'high','status':'done'})
    assert new['status']=='done'
    assert crud.delete(task['id'])
    assert crud.find(task['id']) is None
