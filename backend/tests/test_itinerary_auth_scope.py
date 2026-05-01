from __future__ import annotations

from datetime import date
from pathlib import Path
from uuid import uuid4

import pytest

from app.models.itinerary import ItineraryDayCreate, ItineraryItemCreate
from app.services.itinerary import ItineraryService

# minimal DB omitted (same as before)
class _Result:
    def __init__(self, data): self.data = data
class _Query:
    def __init__(self, rows): self.rows=rows; self.filters=[]; self.mode='select'; self.payload=None; self.limit_n=None; self.order_field=None
    def select(self,_='*'): return self
    def eq(self,f,v): self.filters.append((f,str(v))); return self
    def limit(self,n): self.limit_n=n; return self
    def order(self,f,desc=False): self.order_field=f; return self
    def insert(self,p): self.mode='insert'; self.payload=p; return self
    def update(self,p): self.mode='update'; self.payload=p; return self
    def delete(self): self.mode='delete'; return self
    def _match(self,r): return all(str(r.get(f))==v for f,v in self.filters)
    def execute(self):
        if self.mode=='select':
            rows=[dict(r) for r in self.rows if self._match(r)]
            if self.order_field: rows.sort(key=lambda r:r.get(self.order_field))
            if self.limit_n is not None: rows=rows[:self.limit_n]
            return _Result(rows)
        if self.mode=='insert':
            row=dict(self.payload); row.setdefault('id',str(uuid4())); row.setdefault('created_at','2026-01-01T00:00:00+00:00'); row.setdefault('updated_at','2026-01-01T00:00:00+00:00'); self.rows.append(row); return _Result([dict(row)])
        if self.mode=='update':
            out=[]
            for r in self.rows:
                if self._match(r): r.update(dict(self.payload)); out.append(dict(r))
            return _Result(out)
        if self.mode=='delete':
            self.rows[:] = [r for r in self.rows if not self._match(r)]; return _Result([])
        return _Result([])
class _DB:
    def __init__(self): self.tables={'trips':[], 'itinerary_days':[], 'itinerary_items':[]}
    def table(self,name): return _Query(self.tables[name])

def _seed_trip(db, user_id, trip_id): db.tables['trips'].append({'id': str(trip_id), 'user_id': str(user_id)})

def test_itinerary_route_source_includes_user_id_on_handlers():
    source = Path('backend/app/routes/itinerary.py').read_text()
    for fn in ['list_days','create_day','get_day','update_day','delete_day','list_items','create_item','create_trip_item','get_item','update_item','delete_item']:
        assert f'def {fn}(' in source and 'user_id: CurrentUserID' in source.split(f'def {fn}(',1)[1].split('):',1)[0]

def test_cross_user_blocked_and_owner_allowed():
    db=_DB(); svc=ItineraryService(db)
    owner=uuid4(); intruder=uuid4(); trip=uuid4(); _seed_trip(db, owner, trip)
    day=svc.create_day(ItineraryDayCreate(trip_id=trip, day_number=1, title='D1', date=date(2026,6,1)), owner)
    item=svc.create_item(ItineraryItemCreate(trip_id=trip, day_id=day.id, item_type='activity', title='Museum', position=0), owner)
    assert svc.get_day(day.id, owner).id == day.id
    assert svc.get_item(item.id, owner).id == item.id
    with pytest.raises(Exception): svc.get_day(day.id, intruder)
    with pytest.raises(Exception): svc.list_items(day.id, intruder)
    with pytest.raises(Exception): svc.get_item(item.id, intruder)
