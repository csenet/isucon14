from http import HTTPStatus

from fastapi import APIRouter
from sqlalchemy import text

from .models import Chair, Ride
from .sql import engine

router = APIRouter(prefix="/api/internal")

@router.get("/matching", status_code=HTTPStatus.NO_CONTENT)
def internal_get_matching() -> None:
    with engine.begin() as conn:
        # 未マッチのライドを1件取得
        ride_row = conn.execute(
            text("SELECT * FROM rides WHERE chair_id IS NULL ORDER BY created_at LIMIT 1")
        ).fetchone()

        if ride_row is None:
            # マッチ対象ライドがない場合は終了
            return

        ride = Ride.model_validate(ride_row)
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
            # 利用可能な椅子がなければ何もしない
            return

        matched = None

        # empty判定:
        # すべてのライドがchair_sent_at 6回で完了しているかを確認
        # 1つでも6回未満のライドがあればその椅子はemptyではない
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

        # emptyな椅子がなかった場合はフォールバックとして最も近い椅子を割り当てる
        if matched is None:
            matched = Chair.model_validate(chair_rows[0])

        # ライドに椅子を割り当て
        conn.execute(
            text("UPDATE rides SET chair_id = :chair_id WHERE id = :id"),
            {"chair_id": matched.id, "id": ride.id},
        )

    return
