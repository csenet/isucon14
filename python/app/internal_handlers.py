from http import HTTPStatus
from fastapi import APIRouter
from sqlalchemy import text

from .models import Chair, Ride
from .sql import engine

router = APIRouter(prefix="/api/internal")

@router.get("/matching", status_code=HTTPStatus.NO_CONTENT)
def internal_get_matching() -> None:
    with engine.begin() as conn:
        # 一度に5件のライドをマッチング対象として取得
        rides_rows = conn.execute(
            text("SELECT * FROM rides WHERE chair_id IS NULL ORDER BY created_at LIMIT 5")
        ).fetchall()
        
        if not rides_rows:
            return

        rides = [Ride.model_validate(r) for r in rides_rows]

        # 同一バッチ内で再割り当てを防ぐためのセット
        used_chairs = set()

        for ride in rides:
            pickup_lat = ride.pickup_latitude
            pickup_lon = ride.pickup_longitude

            # すでに使用した椅子を除外する
            excluded_ids = tuple(used_chairs) if used_chairs else ('',)  # 空対策でダミー値を入れておく

            # 候補となる椅子を取得（距離順）
            chair_rows = conn.execute(
                text("""
                    SELECT c.*
                    FROM chairs c
                    INNER JOIN chair_locations cl ON c.id = cl.chair_id
                    WHERE c.is_active = TRUE
                    AND c.id NOT IN :excluded_ids
                    ORDER BY (ABS(cl.latitude - :lat) + ABS(cl.longitude - :lon)) ASC
                    LIMIT 10
                """),
                {"lat": pickup_lat, "lon": pickup_lon, "excluded_ids": excluded_ids}
            ).fetchall()

            if not chair_rows:
                # 利用可能な椅子がなければこのライドは今回は割り当て不能
                continue

            matched = None

            # empty判定: この椅子に紐づくrideのうちchair_sent_atが6回未満のものがあればempty=False
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

            # emptyな椅子が無い場合、最も近い椅子をフォールバックで割り当てる
            if matched is None:
                matched = Chair.model_validate(chair_rows[0])

            # 割り当て実行
            conn.execute(
                text("UPDATE rides SET chair_id = :chair_id WHERE id = :id"),
                {"chair_id": matched.id, "id": ride.id},
            )

            # 同一バッチ内で再利用しないように記録
            used_chairs.add(matched.id)

    return
