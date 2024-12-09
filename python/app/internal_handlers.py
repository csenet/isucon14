from http import HTTPStatus

from fastapi import APIRouter
from sqlalchemy import text

from .models import Chair, Ride
from .sql import engine

router = APIRouter(prefix="/api/internal")


# このAPIをインスタンス内から一定間隔で叩かせることで、椅子とライドをマッチングさせる
@router.get("/matching", status_code=HTTPStatus.NO_CONTENT)
def internal_get_matching() -> None:
    # MEMO: 最もマンハッタン距離？が近い椅子を選んでいる
    with engine.begin() as conn:
        row = conn.execute(
            text(
                "SELECT * FROM rides WHERE chair_id IS NULL ORDER BY created_at LIMIT 1"
            )
        ).fetchone()
        if row is None:
            return
        ride = Ride.model_validate(row)
        pickup_lat = ride.pickup_latitude
        pickup_lon = ride.pickup_longitude

        matched: Chair | None = None
        empty = False

        query = text("""
                  SELECT c.*
                  FROM chairs c
                  INNER JOIN chair_locations cl ON c.id = cl.chair_id
                  WHERE c.is_active = TRUE
                  ORDER BY (ABS(cl.latitude - :lat) + ABS(cl.longitude - :lon)) ASC
                  LIMIT 1
              """)

        chair_row = conn.execute(query, {"lat": pickup_lat, "lon": pickup_lon}).fetchone()

        if chair_row is None:
            return
        matched = Chair.model_validate(chair_row)
        
        empty = bool(
          conn.execute(
              text(
                  "SELECT COUNT(*) = 0 FROM ("
                  "SELECT COUNT(chair_sent_at) = 6 AS completed "
                  "FROM ride_statuses "
                  "WHERE ride_id IN (SELECT id FROM rides WHERE chair_id = :chair_id) "
                  "GROUP BY ride_id"
                  ") is_completed WHERE completed = FALSE"
              ),
              {"chair_id": matched.id},
          ).scalar()
        )


        #for _ in range(10):
        #    row = conn.execute(
        #        text(
        #            "SELECT * FROM chairs INNER JOIN (SELECT id FROM chairs WHERE is_active = TRUE ORDER BY RAND() LIMIT 1) AS tmp ON chairs.id = tmp.id LIMIT 1"
        #        )
        #    ).fetchone()
        #    if row is None:
        #        return
        #    matched = Chair.model_validate(row)

        #    empty = bool(
        #        conn.execute(
        #            text(
        #                "SELECT COUNT(*) = 0 FROM (SELECT COUNT(chair_sent_at) = 6 AS completed FROM ride_statuses WHERE ride_id IN (SELECT id FROM rides WHERE chair_id = :chair_id) GROUP BY ride_id) is_completed WHERE completed = FALSE"
        #            ),
        #            {"chair_id": matched.id},
        #        ).scalar()
        #    )
        #    if empty:
        #        break

        if not empty:
            return

        assert matched is not None
        conn.execute(
            text("UPDATE rides SET chair_id = :chair_id WHERE id = :id"),
            {"chair_id": matched.id, "id": ride.id},
        )
