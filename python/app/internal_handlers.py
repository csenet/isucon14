from http import HTTPStatus

from fastapi import APIRouter
from sqlalchemy import text

from .models import Chair, Ride
from .sql import engine

router = APIRouter(prefix="/api/internal")

@router.get("/matching", status_code=HTTPStatus.NO_CONTENT)
def internal_get_matching() -> None:
    with engine.begin() as conn:
        # 最も古い未マッチのライドを1件取得
        ride_row = conn.execute(
            text("SELECT * FROM rides WHERE chair_id IS NULL ORDER BY created_at LIMIT 1")
        ).fetchone()

        if ride_row is None:
            # 対象のライドがなければ何もしない
            return

        ride = Ride.model_validate(ride_row)
        pickup_lat = ride.pickup_latitude
        pickup_lon = ride.pickup_longitude

        # 距離順に椅子を最大10件取得（マンハッタン距離近似）
        chair_rows = conn.execute(
            text(
                """
                SELECT c.*
                FROM chairs c
                INNER JOIN chair_locations cl ON c.id = cl.chair_id
                WHERE c.is_active = TRUE
                ORDER BY (ABS(cl.latitude - :lat) + ABS(cl.longitude - :lon)) ASC
                LIMIT 10
                """
            ),
            {"lat": pickup_lat, "lon": pickup_lon}
        ).fetchall()

        if not chair_rows:
            # 椅子が全くなければ終了
            return

        matched = None

        # empty判定:
        # 椅子に紐づくライドで chair_sent_at が6回未満のものがあれば未完了ライドが残っているとみなし、empty = False
        # 全てのライドが6回chair_sent_atを持つ（完了）か、もしくは紐づくライドがそもそも無ければ empty = True
        for chair_row in chair_rows:
            candidate = Chair.model_validate(chair_row)
            not_completed_count = conn.execute(
                text(
                    """
                    SELECT COUNT(*) FROM (
                        SELECT r.id, COUNT(rs.chair_sent_at) as sent_count
                        FROM rides r
                        JOIN ride_statuses rs ON r.id = rs.ride_id
                        WHERE r.chair_id = :chair_id
                        GROUP BY r.id
                        HAVING COUNT(rs.chair_sent_at) < 6
                    ) t
                    """
                ),
                {"chair_id": candidate.id}
            ).scalar()

            empty = (not_completed_count == 0)

            if empty:
                matched = candidate
                break

        # emptyな椅子が見つからなければ割り当てせず終了
        if matched is None:
            return

        # emptyな椅子が見つかったのでライドに割り当て
        conn.execute(
            text("UPDATE rides SET chair_id = :chair_id WHERE id = :id"),
            {"chair_id": matched.id, "id": ride.id},
        )
    return
