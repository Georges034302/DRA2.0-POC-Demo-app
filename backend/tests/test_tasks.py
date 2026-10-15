import pathlib,sys,pytest
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]))
from tasks import validate

def test_valid_task():
    assert validate({'title':' Build tests ','priority':'high'})['title']=='Build tests'

@pytest.mark.parametrize('bad',[{'title':''},{'title':'a'*121},{'title':'valid','priority':'urgent'},{'title':'valid','status':'unknown'},{'title':'valid','description':4}])
def test_reject_invalid(bad):
    with pytest.raises(ValueError):validate(bad)

def test_partial_update():
    existing={'title':'Original','description':'','priority':'low','status':'todo'}
    assert validate({'status':'done'},existing)['title']=='Original'
