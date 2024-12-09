from http import HTTPStatus

from fastapi import APIRouter
from sqlalchemy import text

from .models import Chair, Ride
from .sql import engine

router = APIRouter(prefix="/api/internal")


@router.get("/matching", status_code=HTTPStatus.NO_CONTENT)
def internal_get_matching() -> None:
    with engine.begin() as conn:
        # 一度にマッチングするライド数(例：5件)
        rides_rows = conn.execute(
            text("SELECT * FROM rides WHERE chair_id IS NULL ORDER BY created_at LIMIT 5")
        ).fetchall()
        
        if not rides_rows:
            return

        rides = [Ride.model_validate(r) for r in rides_rows]

        for ride in rides:
            pickup_lat = ride.pickup_latitude
            pickup_lon = ride.pickup_longitude

            # 候補の椅子を複数件取得（距離順に10件）
            chair_rows = conn.execute(
                text("""
                    SELECT c.*
                    FROM chairs c
                    INNER JOIN chair_locations cl ON c.id = cl.chair_id
                    WHERE c.is_active = TRUE
                    ORDER BY (ABS(cl.latitude - :lat) + ABS(cl.longitude - :lon)) ASC
                    LIMIT 10
                """),
                {"lat": pickup_lat, "lon": pickup_lon}
            ).fetchall()

            if not chair_rows:
                # 利用可能な椅子がなければスキップ
                continue

            matched = None

            # empty判定のロジック:
            # ride_statusesテーブルから、そのchair_idに紐づくライドで、
            # chair_sent_atが6回未満のものがあるかチェックする。
            #
            # まずは、chair_idに紐づくrideごとにchair_sent_atのCOUNTを集計し、
            # 6回未満のライドが1つでもあればempty=False、なければempty=True。

            for chair_row in chair_rows:
                candidate = Chair.model_validate(chair_row)

                not_completed_count = conn.execute(
                    text("""
                        SELECT COUNT(*) FROM (
                            SELECT r.id, COUNT(rs.chair_sent_at) as sent_count
                            FROM rides r
                            JOIN ride_statuses rs ON r.id = rs.ride_id
                            WHERE r.chair_id = :chair_id
                            GROUP BY r.id
                            HAVING COUNT(rs.chair_sent_at) < 6
                        ) t
                    """),
                    {"chair_id": candidate.id}
                ).scalar()

                empty = (not_completed_count == 0)

                if empty:
                    matched = candidate
                    break

            # emptyな椅子がなかった場合はフォールバックとして一番近い椅子を割り当てる
            if matched is None:
                matched = Chair.model_validate(chair_rows[0])

            # 椅子をライドに割り当てる
            conn.execute(
                text("UPDATE rides SET chair_id = :chair_id WHERE id = :id"),
                {"chair_id": matched.id, "id": ride.id},
            )

    return
