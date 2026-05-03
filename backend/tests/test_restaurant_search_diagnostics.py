from app.models.search import RestaurantSearchRequest
from app.services.search import SearchService

class _DB:
    def table(self, _):
        class _Q:
            def select(self,*a,**k): return self
            def eq(self,*a,**k): return self
            def gt(self,*a,**k): return self
            def limit(self,*a,**k): return self
            def execute(self):
                class R: data=[]
                return R()
            def insert(self,*a,**k): return self
        return _Q()

def test_search_restaurants_exposes_status_and_verified_identity_fields():
    svc = SearchService(_DB())
    out = svc.search_restaurants(RestaurantSearchRequest(location='Chicago'))
    assert out
    assert all(r.verification_status == 'verified' for r in out)
    assert all(r.source_status == 'ok' for r in out)
    assert all(r.cache_status in {'miss','hit'} for r in out)
    assert all(r.google_maps_uri or r.provider_place_id or r.place_id for r in out)
