from http import HTTPStatus

from fastapi import APIRouter
from sqlalchemy import text

from .models import Chair, Ride
from .sql import engine

router = APIRouter(prefix="/api/internal")


@router.get("/matching", status_code=HTTPStatus.NO_CONTENT)
def internal_get_matching() -> None:
    with engine.begin() as conn:
        # 一度にマッチングするライド数を5件とする
        rides_rows = conn.execute(
            text("SELECT * FROM rides WHERE chair_id IS NULL ORDER BY created_at LIMIT 5")
        ).fetchall()
        
        if not rides_rows:
            return

        rides = [Ride.model_validate(r) for r in rides_rows]

        # 複数のライド分をまとめて処理する
        for ride in rides:
            pickup_lat = ride.pickup_latitude
            pickup_lon = ride.pickup_longitude

            # 候補の椅子を複数件取得（距離順）
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
                # 利用可能な椅子が全くなければこのライドはスキップ(マッチング不可)
                continue

            matched = None

            # empty判定を簡略化（以下は例。実際の空判定は環境依存）
            # ここではstatus = 'completed'以外のライドが椅子に紐づいていなければemptyとみなす
            for chair_row in chair_rows:
                candidate = Chair.model_validate(chair_row)

                not_completed_count = conn.execute(
                    text("SELECT COUNT(*) FROM rides WHERE chair_id = :chair_id AND status <> 'completed'"),
                    {"chair_id": candidate.id}
                ).scalar()

                empty = (not_completed_count == 0)

                if empty:
                    matched = candidate
                    break

            # emptyな椅子が見つからない場合はフォールバックで最も近い椅子を採用
            if matched is None:
                matched = Chair.model_validate(chair_rows[0])

            # 椅子をライドに割り当てる
            conn.execute(
                text("UPDATE rides SET chair_id = :chair_id WHERE id = :id"),
                {"chair_id": matched.id, "id": ride.id},
            )

    # 一度に複数ライドのマッチが終了したら204を返す
    return
